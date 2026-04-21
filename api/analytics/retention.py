"""
Customer Retention / Churn Analytics (V3 #44)

Calculates:
- Renewal rate by month
- Churn reasons (from cancellation data)
- Revenue retention rate
- Cohort analysis by signup month
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from django.utils import timezone


# Cancellation reason keyword mapping → category
CHURN_REASON_CATEGORIES = {
    "price": ["price", "cost", "expensive", "afford", "premium", "budget"],
    "competition": [
        "competitor",
        "compet",
        "other insurer",
        "another carrier",
        "switched",
        "switch",
    ],
    "no_longer_needed": [
        "no longer",
        "closed",
        "dissolved",
        "out of business",
        "ceased",
        "shut",
    ],
    "claims_dispute": ["claim", "dispute", "denial", "denied"],
    "service": ["service", "support", "response", "slow"],
    "other": [],  # fallback
}


def _categorise_reason(reason_text: str) -> str:
    """Categorise a free-text cancellation reason into a bucket."""
    if not reason_text:
        return "not_provided"
    lower = reason_text.lower()
    for category, keywords in CHURN_REASON_CATEGORIES.items():
        if category == "other":
            continue
        if any(kw in lower for kw in keywords):
            return category
    return "other"


def get_retention_report() -> dict[str, Any]:
    """Build the full customer retention/churn report.

    Returns a dict with:
        ``renewal_rates``: list of monthly renewal rate dicts.
        ``churn_reasons``: list of churn reason breakdown dicts.
        ``revenue_retention_rate``: float — % of revenue retained on renewal.
        ``cohort_analysis``: list of cohort dicts.
        ``overall_renewal_rate``: float.
        ``total_eligible``: int.
        ``total_renewed``: int.
    """
    from policies.models import Policy, PolicyTransaction

    today = date.today()
    twelve_months_ago = today - timedelta(days=365)

    # ── Renewal Rates by Month ────────────────────────────────────────
    # Policies that expired in the past 12 months = eligible for renewal
    expired_policies = Policy.objects.filter(
        expiration_date__gte=twelve_months_ago,
        expiration_date__lte=today,
        status__in=["expired", "active", "non_renewed", "cancelled"],
    ).exclude(is_deleted=True)

    # Group by expiration month
    by_month: dict[str, dict] = {}
    for policy in expired_policies.values(
        "id", "expiration_date", "premium", "quote__organization_id"
    ):
        month_str = policy["expiration_date"].strftime("%Y-%m")
        if month_str not in by_month:
            by_month[month_str] = {"eligible": 0, "eligible_premium": Decimal("0")}
        by_month[month_str]["eligible"] += 1
        by_month[month_str]["eligible_premium"] += Decimal(str(policy["premium"] or 0))

    # Renewal transactions in the past 12 months
    renewal_txns = PolicyTransaction.objects.filter(
        transaction_type="renewal",
        accounting_date__gte=twelve_months_ago,
    ).values("accounting_date", "gross_written_premium", "policy__expiration_date")

    renewed_by_month: dict[str, dict] = {}
    for txn in renewal_txns:
        # The renewal month is the month the *old* policy expired
        exp_date = txn.get("policy__expiration_date")
        if exp_date:
            month_str = exp_date.strftime("%Y-%m")
        else:
            month_str = txn["accounting_date"].strftime("%Y-%m")
        if month_str not in renewed_by_month:
            renewed_by_month[month_str] = {
                "renewed": 0,
                "renewed_premium": Decimal("0"),
            }
        renewed_by_month[month_str]["renewed"] += 1
        renewed_by_month[month_str]["renewed_premium"] += Decimal(
            str(txn["gross_written_premium"] or 0)
        )

    renewal_rates = []
    for month_str in sorted(by_month.keys()):
        eligible = by_month[month_str]["eligible"]
        renewed = renewed_by_month.get(month_str, {}).get("renewed", 0)
        rate = round(renewed / eligible * 100, 1) if eligible else None
        renewal_rates.append(
            {
                "month": month_str,
                "eligible_renewals": eligible,
                "renewed": renewed,
                "renewal_rate": rate,
            }
        )

    total_eligible = sum(m["eligible"] for m in by_month.values())
    total_renewed = sum(v.get("renewed", 0) for v in renewed_by_month.values())
    overall_rate = (
        round(total_renewed / total_eligible * 100, 1) if total_eligible else None
    )

    # ── Churn Reasons ─────────────────────────────────────────────────
    cancelled_policies = Policy.objects.filter(
        status="cancelled",
        updated_at__gte=timezone.now() - timedelta(days=365),
    ).exclude(is_deleted=True)

    reason_buckets: dict[str, int] = {}
    for policy in cancelled_policies.values("id"):
        # Try to get cancellation reason from PolicyTransaction
        txn = (
            PolicyTransaction.objects.filter(
                policy_id=policy["id"],
                transaction_type="cancellation",
            )
            .values("description")
            .first()
        )
        reason_text = txn["description"] if txn and txn.get("description") else ""
        category = _categorise_reason(reason_text)
        reason_buckets[category] = reason_buckets.get(category, 0) + 1

    total_churned = sum(reason_buckets.values())
    churn_reasons = [
        {
            "reason": reason,
            "count": count,
            "percentage": round(count / total_churned * 100, 1)
            if total_churned
            else None,
        }
        for reason, count in sorted(reason_buckets.items(), key=lambda x: -x[1])
    ]

    # ── Revenue Retention Rate ────────────────────────────────────────
    eligible_premium = sum(m["eligible_premium"] for m in by_month.values())
    renewed_premium = sum(
        v.get("renewed_premium", Decimal("0")) for v in renewed_by_month.values()
    )
    revenue_retention = (
        round(float(renewed_premium / eligible_premium * 100), 1)
        if eligible_premium
        else None
    )

    # ── Cohort Analysis by Signup Month ──────────────────────────────
    # Cohort = first policy purchased by an org in that month
    # Retention = org still has an active policy 12 months later
    from quotes.models import Quote

    cohort_data: dict[str, dict] = {}
    # Get all quotes that became purchased, grouped by org and month
    purchased_quotes = (
        Quote.objects.filter(status="purchased")
        .exclude(is_deleted=True)
        .values("organization_id", "created_at")
        .order_by("organization_id", "created_at")
    )

    # Find first purchase month per org
    first_purchase: dict[int, date] = {}
    for q in purchased_quotes:
        org_id = q["organization_id"]
        created = q["created_at"].date() if q["created_at"] else None
        if created and (
            org_id not in first_purchase or created < first_purchase[org_id]
        ):
            first_purchase[org_id] = created

    for org_id, first_date in first_purchase.items():
        # Only cohorts from 12+ months ago (enough time to have churned/renewed)
        if first_date > today - timedelta(days=365):
            continue
        cohort_month = first_date.strftime("%Y-%m")
        if cohort_month not in cohort_data:
            cohort_data[cohort_month] = {"total": 0, "retained": 0}
        cohort_data[cohort_month]["total"] += 1

        # Retained = org has active policy today
        is_retained = (
            Policy.objects.filter(
                quote__organization_id=org_id,
                status="active",
            )
            .exclude(is_deleted=True)
            .exists()
        )
        if is_retained:
            cohort_data[cohort_month]["retained"] += 1

    cohort_analysis = []
    for month_str in sorted(cohort_data.keys()):
        d = cohort_data[month_str]
        total = d["total"]
        retained = d["retained"]
        churned = total - retained
        cohort_analysis.append(
            {
                "cohort_month": month_str,
                "total": total,
                "retained": retained,
                "churned": churned,
                "retention_rate": round(retained / total * 100, 1) if total else None,
            }
        )

    return {
        "renewal_rates": renewal_rates,
        "churn_reasons": churn_reasons,
        "revenue_retention_rate": revenue_retention,
        "cohort_analysis": cohort_analysis,
        "overall_renewal_rate": overall_rate,
        "total_eligible": total_eligible,
        "total_renewed": total_renewed,
    }
