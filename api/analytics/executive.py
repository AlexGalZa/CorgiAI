"""
Executive Dashboard Analytics (V3 #48)

Single-page summary of key business metrics for executive consumption.

Metrics:
    - Gross Written Premium (GWP) — total and YTD
    - Annual Recurring Revenue (ARR) — annualised from active monthly subs
    - Loss Ratio — incurred losses / earned premium
    - Growth Rate — GWP growth vs prior 30 days
    - Retention Rate — active policies renewed in last 12 months
    - Cash Position — paid premiums minus paid losses (proxy)

Usage:
    from analytics.executive import get_executive_dashboard
    data = get_executive_dashboard()
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.db.models import Sum
from django.utils import timezone


def get_executive_dashboard() -> dict[str, Any]:
    """
    Build the executive dashboard metrics dict.

    Returns a standardised metrics bundle suitable for the dashboard template.
    All monetary values are in USD floats.
    """
    from policies.models import Policy
    from claims.models import Claim
    from policies.models import EarnedPremiumRecord

    now = timezone.now()

    # ── Time windows ────────────────────────────────────────────────────
    ytd_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    last_30 = now - timezone.timedelta(days=30)
    prior_30_start = now - timezone.timedelta(days=60)
    prior_30_end = now - timezone.timedelta(days=30)
    last_12m = now - timezone.timedelta(days=365)

    # ── Gross Written Premium (GWP) ──────────────────────────────────────
    gwp_all_time = _policy_sum(
        "premium",
        Policy.objects.filter(
            is_deleted=False,
            status__in=["active", "expired", "cancelled"],
        ),
    )
    gwp_ytd = _policy_sum(
        "premium",
        Policy.objects.filter(
            is_deleted=False,
            status__in=["active", "expired", "cancelled"],
            purchased_at__gte=ytd_start,
        ),
    )
    gwp_last_30 = _policy_sum(
        "premium",
        Policy.objects.filter(
            is_deleted=False,
            purchased_at__gte=last_30,
        ),
    )
    gwp_prior_30 = _policy_sum(
        "premium",
        Policy.objects.filter(
            is_deleted=False,
            purchased_at__gte=prior_30_start,
            purchased_at__lt=prior_30_end,
        ),
    )

    # ── ARR (Annual Recurring Revenue) ──────────────────────────────────
    # Active monthly subscribers: monthly_premium * 12
    # Annual subscribers: premium (already annual)
    monthly_subs = Policy.objects.filter(
        is_deleted=False,
        status="active",
        billing_frequency="monthly",
    ).aggregate(total=Sum("monthly_premium"))["total"] or Decimal("0")

    annual_subs = Policy.objects.filter(
        is_deleted=False,
        status="active",
        billing_frequency="annual",
    ).aggregate(total=Sum("premium"))["total"] or Decimal("0")

    arr = float(monthly_subs * 12 + annual_subs)

    # ── Policy Count ────────────────────────────────────────────────────
    active_policy_count = Policy.objects.filter(
        is_deleted=False,
        status="active",
    ).count()
    total_policy_count = Policy.objects.filter(
        is_deleted=False,
        status__in=["active", "expired", "cancelled"],
    ).count()

    # ── Loss Ratio ──────────────────────────────────────────────────────
    earned_qs = EarnedPremiumRecord.objects.aggregate(
        total_earned=Sum("earned_amount"),
    )
    total_earned = float(earned_qs["total_earned"] or 0)

    claim_agg = Claim.objects.filter(is_deleted=False).aggregate(
        total_paid=Sum("paid_loss"),
        total_reserve=Sum("case_reserve_loss"),
    )
    total_paid_losses = float(claim_agg["total_paid"] or 0)
    total_incurred = total_paid_losses + float(claim_agg["total_reserve"] or 0)
    loss_ratio = (
        round(total_incurred / total_earned * 100, 1) if total_earned > 0 else None
    )

    # ── Growth Rate ─────────────────────────────────────────────────────
    if gwp_prior_30 > 0:
        growth_rate = round((gwp_last_30 - gwp_prior_30) / gwp_prior_30 * 100, 1)
    else:
        growth_rate = None  # not enough data

    # ── Retention Rate ──────────────────────────────────────────────────
    # Renewal rate: policies up for renewal in last 12m that were actually renewed
    policies_up_for_renewal = Policy.objects.filter(
        is_deleted=False,
        expiration_date__gte=last_12m,
        expiration_date__lt=now,
    ).count()

    policies_renewed = Policy.objects.filter(
        is_deleted=False,
        renewal_status="renewed",
        expiration_date__gte=last_12m,
        expiration_date__lt=now,
    ).count()

    retention_rate = (
        round(policies_renewed / policies_up_for_renewal * 100, 1)
        if policies_up_for_renewal > 0
        else None
    )

    # ── Cash Position (proxy) ───────────────────────────────────────────
    # Total premiums collected - total paid losses (simplified cash proxy)
    # In a real deployment this would pull from accounting/Stripe balance
    cash_position = gwp_all_time - total_paid_losses

    # ── Open Claims ────────────────────────────────────────────────────
    open_claims = Claim.objects.filter(
        is_deleted=False,
        status__in=["submitted", "under_review", "approved"],
    ).count()

    return {
        "gwp": {
            "all_time": gwp_all_time,
            "ytd": gwp_ytd,
            "last_30_days": gwp_last_30,
            "prior_30_days": gwp_prior_30,
        },
        "arr": arr,
        "loss_ratio_pct": loss_ratio,
        "growth_rate_pct": growth_rate,
        "retention_rate_pct": retention_rate,
        "cash_position": cash_position,
        "policy_count": {
            "active": active_policy_count,
            "total": total_policy_count,
        },
        "claims": {
            "open": open_claims,
            "total_paid": total_paid_losses,
            "total_incurred": total_incurred,
        },
        "generated_at": now.isoformat(),
    }


def _policy_sum(field: str, qs) -> float:
    result = qs.aggregate(total=Sum(field))["total"]
    return float(result or 0)
