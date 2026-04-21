"""
Internal AE / BDR performance metrics sourced from Django (policies, producers, quotes).

Two service functions power the Sales Performance dashboard (H21):

- ``ae_metrics``  — per-AE scorecard (policies bound, GWP, close rate, time-to-bind,
  open pipeline).
- ``bdr_metrics`` — same shape scoped to BDRs (pipeline sourced + handoffs).

Metrics are calculated against ``Policy.purchased_at`` for bound counts and against
``Quote.created_at`` for pipeline / close-rate denominators. "Close rate" is defined
as ``policies_bound / quotes_touched`` where a quote is considered touched when the
producer was attached to the quote's resulting policy (or any policy sharing the
same quote lineage).
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any, Optional

from django.db.models import Count, DecimalField, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone


def _to_aware_range(start_date: date, end_date: date) -> tuple[datetime, datetime]:
    """Return (start_dt, end_dt_exclusive) timezone-aware datetimes."""
    tz = timezone.get_current_timezone()
    start_dt = timezone.make_aware(datetime.combine(start_date, time.min), tz)
    end_dt = timezone.make_aware(
        datetime.combine(end_date + timedelta(days=1), time.min), tz
    )
    return start_dt, end_dt


def _producer_queryset(role: str, producer_id: Optional[int]):
    """Return the Producer queryset filtered to a role + optional single id."""
    from producers.models import Producer

    qs = Producer.objects.filter(producer_type=role, is_active=True)
    if producer_id is not None:
        qs = qs.filter(id=producer_id)
    return qs.order_by("name")


def _compute_metrics_for_role(
    role: str,
    start_date: date,
    end_date: date,
    producer_id: Optional[int],
) -> list[dict[str, Any]]:
    """Shared computation for AE / BDR scorecards.

    For each producer with ``producer_type == role`` we aggregate:
      - policies_bound: Policy rows linked via PolicyProducer where
        ``Policy.purchased_at`` falls in [start, end].
      - gross_premium: sum of Policy.premium across those bound policies.
      - close_rate: bound / quotes_touched in the window.
      - avg_time_to_bind_days: mean (purchased_at - quote.created_at) across bound
        policies.
      - active_pipeline_count: Quotes the producer is associated with (via their
        existing PolicyProducer links on sibling policies) currently in non-terminal
        statuses (submitted, needs_review, quoted).
    """
    from producers.models import PolicyProducer

    start_dt, end_dt_exclusive = _to_aware_range(start_date, end_date)

    producers = list(_producer_queryset(role, producer_id))
    if not producers:
        return []

    producer_ids = [p.id for p in producers]

    bound_qs = (
        PolicyProducer.objects.filter(
            producer_id__in=producer_ids,
            policy__purchased_at__gte=start_dt,
            policy__purchased_at__lt=end_dt_exclusive,
        )
        .values("producer_id")
        .annotate(
            policies_bound=Count("policy_id", distinct=True),
            gross_premium=Coalesce(
                Sum("policy__premium"),
                Value(Decimal("0")),
                output_field=DecimalField(max_digits=15, decimal_places=2),
            ),
        )
    )
    bound_map = {row["producer_id"]: row for row in bound_qs}

    time_to_bind_rows = PolicyProducer.objects.filter(
        producer_id__in=producer_ids,
        policy__purchased_at__gte=start_dt,
        policy__purchased_at__lt=end_dt_exclusive,
    ).values_list("producer_id", "policy__purchased_at", "policy__quote__created_at")

    ttb_totals: dict[int, list[float]] = {pid: [] for pid in producer_ids}
    for pid, purchased_at, quote_created_at in time_to_bind_rows:
        if purchased_at and quote_created_at:
            delta = purchased_at - quote_created_at
            days = delta.total_seconds() / 86400.0
            if days >= 0:
                ttb_totals[pid].append(days)

    touched_qs = (
        PolicyProducer.objects.filter(
            producer_id__in=producer_ids,
            policy__quote__created_at__gte=start_dt,
            policy__quote__created_at__lt=end_dt_exclusive,
        )
        .values("producer_id")
        .annotate(quotes_touched=Count("policy__quote_id", distinct=True))
    )
    touched_map = {row["producer_id"]: row["quotes_touched"] for row in touched_qs}

    open_pipeline_qs = (
        PolicyProducer.objects.filter(
            producer_id__in=producer_ids,
            policy__quote__status__in=["submitted", "needs_review", "quoted"],
        )
        .values("producer_id")
        .annotate(active=Count("policy__quote_id", distinct=True))
    )
    pipeline_map = {row["producer_id"]: row["active"] for row in open_pipeline_qs}

    results: list[dict[str, Any]] = []
    for p in producers:
        bound_row = bound_map.get(p.id)
        policies_bound = int(bound_row["policies_bound"]) if bound_row else 0
        gross_premium = float(bound_row["gross_premium"]) if bound_row else 0.0
        quotes_touched = int(touched_map.get(p.id, 0))
        close_rate = (
            round(policies_bound / quotes_touched, 4) if quotes_touched > 0 else None
        )
        ttb = ttb_totals.get(p.id) or []
        avg_ttb = round(sum(ttb) / len(ttb), 2) if ttb else None

        results.append(
            {
                "producer_id": p.id,
                "name": p.name,
                "role": p.producer_type,
                "policies_bound": policies_bound,
                "gross_premium": gross_premium,
                "quotes_touched": quotes_touched,
                "close_rate": close_rate,
                "avg_time_to_bind_days": avg_ttb,
                "active_pipeline_count": int(pipeline_map.get(p.id, 0)),
            }
        )

    return results


def ae_metrics(
    start_date: date,
    end_date: date,
    producer_id: Optional[int] = None,
) -> dict[str, Any]:
    rows = _compute_metrics_for_role("ae", start_date, end_date, producer_id)
    return {
        "role": "ae",
        "start": start_date.isoformat(),
        "end": end_date.isoformat(),
        "totals": _roll_up_totals(rows),
        "producers": rows,
    }


def bdr_metrics(
    start_date: date,
    end_date: date,
    producer_id: Optional[int] = None,
) -> dict[str, Any]:
    rows = _compute_metrics_for_role("bdr", start_date, end_date, producer_id)
    return {
        "role": "bdr",
        "start": start_date.isoformat(),
        "end": end_date.isoformat(),
        "totals": _roll_up_totals(rows),
        "producers": rows,
    }


def _roll_up_totals(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "producer_count": 0,
            "policies_bound": 0,
            "gross_premium": 0.0,
            "quotes_touched": 0,
            "close_rate": None,
            "active_pipeline_count": 0,
        }
    bound = sum(r["policies_bound"] for r in rows)
    touched = sum(r["quotes_touched"] for r in rows)
    return {
        "producer_count": len(rows),
        "policies_bound": bound,
        "gross_premium": round(sum(r["gross_premium"] for r in rows), 2),
        "quotes_touched": touched,
        "close_rate": round(bound / touched, 4) if touched > 0 else None,
        "active_pipeline_count": sum(r["active_pipeline_count"] for r in rows),
    }
