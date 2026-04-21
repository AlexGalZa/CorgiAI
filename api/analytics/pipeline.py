"""
Sales Pipeline Velocity Analytics (V3 #43)

Calculates:
- Average days a quote spends in each status stage
- Stage-to-stage conversion rates (submitted → quoted → purchased)
- Total pipeline value (sum of quote_amount for active/quoted pipeline)
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.db.models import (
    Count,
    Sum,
)
from django.db.models.functions import Coalesce
from django.utils import timezone


# Status stages in funnel order
FUNNEL_STAGES = ["submitted", "needs_review", "quoted", "purchased", "declined"]


def get_pipeline_velocity() -> dict[str, Any]:
    """Calculate sales pipeline velocity metrics.

    Returns a dict with:
        ``stage_velocity``: list of dicts — one per status stage with avg_days and count.
        ``conversion_rates``: dict — stage-to-stage conversion rates as percentages.
        ``pipeline_value``: Decimal — sum of quote_amount for quoted/active quotes.
        ``total_quotes``: int — total number of non-draft quotes.
        ``purchased_count``: int — number of purchased quotes.
    """
    from quotes.models import Quote

    base_qs = Quote.objects.exclude(status="draft")

    # ── Stage counts ──────────────────────────────────────────────────
    stage_counts: dict[str, int] = {}
    counts_qs = base_qs.values("status").annotate(count=Count("id"))
    for row in counts_qs:
        stage_counts[row["status"]] = row["count"]

    # ── Average time in each stage ─────────────────────────────────────
    # We approximate "time in stage" as:
    #   - submitted → quoted: quoted_at - created_at (for quoted/purchased quotes)
    #   - quoted → purchased: purchased_at - quoted_at (for purchased quotes)
    #   - submitted → purchased: purchased_at - created_at (for purchased quotes)
    #
    # For quotes still in a stage: now - created_at (open pipeline age)

    stage_velocity = []

    # submitted: time from created_at → quoted_at (or now if still submitted)
    submitted_qs = base_qs.filter(
        status__in=["submitted", "needs_review", "quoted", "purchased"]
    )
    # Average days from creation to first rating (quoted_at)
    rated_qs = submitted_qs.filter(quoted_at__isnull=False)
    avg_submit_to_quote = _avg_days(rated_qs, "created_at", "quoted_at")

    stage_velocity.append(
        {
            "stage": "submitted",
            "display": "Submitted → Quoted",
            "avg_days": round(avg_submit_to_quote, 1)
            if avg_submit_to_quote is not None
            else None,
            "count": stage_counts.get("submitted", 0)
            + stage_counts.get("needs_review", 0),
        }
    )

    # quoted → purchased: time from quoted_at → purchased_at
    purchased_qs = base_qs.filter(status="purchased", quoted_at__isnull=False)
    avg_quote_to_purchase = _avg_days_purchased(purchased_qs)

    stage_velocity.append(
        {
            "stage": "quoted",
            "display": "Quoted → Purchased",
            "avg_days": round(avg_quote_to_purchase, 1)
            if avg_quote_to_purchase is not None
            else None,
            "count": stage_counts.get("quoted", 0),
        }
    )

    # Full funnel: submitted → purchased
    full_funnel_qs = base_qs.filter(status="purchased", quoted_at__isnull=False)
    avg_full_funnel = _avg_days_full(full_funnel_qs)

    stage_velocity.append(
        {
            "stage": "full_funnel",
            "display": "Submitted → Purchased",
            "avg_days": round(avg_full_funnel, 1)
            if avg_full_funnel is not None
            else None,
            "count": stage_counts.get("purchased", 0),
        }
    )

    # ── Conversion Rates ──────────────────────────────────────────────
    total = base_qs.count()
    submitted_plus = base_qs.filter(
        status__in=["submitted", "needs_review", "quoted", "purchased"]
    ).count()
    quoted_plus = base_qs.filter(status__in=["quoted", "purchased"]).count()
    purchased_count = stage_counts.get("purchased", 0)
    declined_count = stage_counts.get("declined", 0)

    def pct(num: int, denom: int) -> float | None:
        return round(num / denom * 100, 1) if denom else None

    conversion_rates = {
        "submitted_to_quoted": pct(quoted_plus, submitted_plus),
        "quoted_to_purchased": pct(purchased_count, quoted_plus),
        "submitted_to_purchased": pct(purchased_count, submitted_plus),
        "decline_rate": pct(declined_count, total),
    }

    # ── Pipeline Value ─────────────────────────────────────────────────
    pipeline_value = (
        base_qs.filter(status__in=["submitted", "needs_review", "quoted"]).aggregate(
            total=Coalesce(Sum("quote_amount"), Decimal("0"))
        )
    )["total"]

    # ── Open pipeline age ──────────────────────────────────────────────
    now = timezone.now()
    open_quotes = base_qs.filter(status__in=["submitted", "needs_review", "quoted"])
    open_ages = []
    for q in open_quotes.values("created_at"):
        days = (now - q["created_at"]).days
        open_ages.append(days)
    avg_open_age = round(sum(open_ages) / len(open_ages), 1) if open_ages else None

    return {
        "stage_velocity": stage_velocity,
        "conversion_rates": conversion_rates,
        "pipeline_value": float(pipeline_value),
        "total_quotes": total,
        "purchased_count": purchased_count,
        "open_quotes": len(open_ages),
        "avg_open_age_days": avg_open_age,
        "stage_counts": {stage: stage_counts.get(stage, 0) for stage in FUNNEL_STAGES},
    }


def _avg_days(qs, start_field: str, end_field: str) -> float | None:
    """Average days between two datetime fields on a queryset."""

    results = list(qs.values(start_field, end_field))
    if not results:
        return None
    deltas = [
        (row[end_field] - row[start_field]).total_seconds() / 86400
        for row in results
        if row[start_field] and row[end_field]
    ]
    return sum(deltas) / len(deltas) if deltas else None


def _avg_days_purchased(purchased_qs) -> float | None:
    """Average days from quoted_at to purchase (first policy purchased_at for quote)."""
    from policies.models import Policy

    rows = list(purchased_qs.filter(quoted_at__isnull=False).values("id", "quoted_at"))
    if not rows:
        return None
    quote_ids = [r["id"] for r in rows]
    quoted_at_map = {r["id"]: r["quoted_at"] for r in rows}

    # Get earliest policy purchased_at per quote
    (
        Policy.objects.filter(quote_id__in=quote_ids)
        .values("quote_id")
        .annotate(first_purchased=Coalesce("purchased_at", timezone.now()))
        .values("quote_id", "first_purchased")
    )
    # Actually just pull all
    all_policy_dates: dict[int, Any] = {}
    for p in Policy.objects.filter(quote_id__in=quote_ids).values(
        "quote_id", "purchased_at"
    ):
        qid = p["quote_id"]
        if p["purchased_at"] and (
            qid not in all_policy_dates or p["purchased_at"] < all_policy_dates[qid]
        ):
            all_policy_dates[qid] = p["purchased_at"]

    deltas = []
    for qid, quoted_at in quoted_at_map.items():
        purchased_at = all_policy_dates.get(qid)
        if quoted_at and purchased_at:
            deltas.append((purchased_at - quoted_at).total_seconds() / 86400)
    return sum(deltas) / len(deltas) if deltas else None


def _avg_days_full(full_qs) -> float | None:
    """Average days from created_at to first policy purchase."""
    from policies.models import Policy

    rows = list(full_qs.values("id", "created_at"))
    if not rows:
        return None
    quote_ids = [r["id"] for r in rows]
    created_at_map = {r["id"]: r["created_at"] for r in rows}

    all_policy_dates: dict[int, Any] = {}
    for p in Policy.objects.filter(quote_id__in=quote_ids).values(
        "quote_id", "purchased_at"
    ):
        qid = p["quote_id"]
        if p["purchased_at"] and (
            qid not in all_policy_dates or p["purchased_at"] < all_policy_dates[qid]
        ):
            all_policy_dates[qid] = p["purchased_at"]

    deltas = []
    for qid, created_at in created_at_map.items():
        purchased_at = all_policy_dates.get(qid)
        if created_at and purchased_at:
            deltas.append((purchased_at - created_at).total_seconds() / 86400)
    return sum(deltas) / len(deltas) if deltas else None
