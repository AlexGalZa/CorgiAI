"""
Analytics reports for the Corgi Insurance platform.

Contains report logic for earned premium, loss ratio, and other financial reporting.
"""

from typing import Any

from django.db.models import Sum
from django.db.models.functions import TruncMonth

from policies.models import EarnedPremiumRecord


def get_earned_premium_report(
    month: str | None = None,
    carrier: str | None = None,
    coverage_type: str | None = None,
) -> dict[str, Any]:
    """
    Generate earned premium breakdown with optional filters.

    Args:
        month: ISO month string (YYYY-MM) to filter by period_start
        carrier: Carrier name string to filter (matched against policy carrier field)
        coverage_type: Coverage type slug to filter

    Returns:
        Dict with rows (list of dicts) and summary totals
    """
    qs = EarnedPremiumRecord.objects.select_related("policy")

    if month:
        try:
            year, mon = map(int, month.split("-"))
            qs = qs.filter(period_start__year=year, period_start__month=mon)
        except (ValueError, AttributeError):
            pass

    if coverage_type:
        qs = qs.filter(policy__coverage_type=coverage_type)

    if carrier:
        # Carrier is stored in policy.carrier field if it exists, otherwise filter by known carrier mapping
        qs = qs.filter(policy__carrier__icontains=carrier)

    # Aggregate by month + coverage_type
    rows = (
        qs.annotate(month=TruncMonth("period_start"))
        .values("month", "policy__coverage_type")
        .annotate(
            total_earned=Sum("earned_amount"),
            total_unearned=Sum("unearned_amount"),
            policy_count=Sum("policy__id", distinct=True),
        )
        .order_by("-month", "policy__coverage_type")
    )

    # Totals
    totals = qs.aggregate(
        grand_total_earned=Sum("earned_amount"),
        grand_total_unearned=Sum("unearned_amount"),
    )

    return {
        "rows": [
            {
                "month": row["month"].strftime("%Y-%m") if row["month"] else None,
                "coverage_type": row["policy__coverage_type"],
                "earned_amount": float(row["total_earned"] or 0),
                "unearned_amount": float(row["total_unearned"] or 0),
            }
            for row in rows
        ],
        "total_earned": float(totals["grand_total_earned"] or 0),
        "total_unearned": float(totals["grand_total_unearned"] or 0),
        "filters": {
            "month": month,
            "carrier": carrier,
            "coverage_type": coverage_type,
        },
    }
