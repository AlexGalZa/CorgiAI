"""
Payment reconciliation reports for finance and admin dashboards.

Functions:
- monthly_premium_reconciliation(): Expected vs collected by month
- aging_receivables(): 30/60/90 day buckets of outstanding premiums
- collection_rate(): Overall and monthly collection rates
- reconciliation_summary(): Combined dashboard data

Used by the PaymentReconciliationAdmin view.
"""

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import TypedDict

from django.db.models import Sum

logger = logging.getLogger(__name__)


class MonthlyReconciliation(TypedDict):
    year: int
    month: int
    month_label: str
    expected_premium: Decimal
    collected_premium: Decimal
    failed_premium: Decimal
    refunded_premium: Decimal
    net_collected: Decimal
    collection_rate: float
    policy_count: int
    payment_count: int


class AgingBucket(TypedDict):
    bucket: str  # "0-30", "31-60", "61-90", "90+"
    policy_count: int
    outstanding_amount: Decimal
    oldest_due_days: int


class CollectionRate(TypedDict):
    period_label: str
    expected: Decimal
    collected: Decimal
    rate: float


def monthly_premium_reconciliation(months: int = 12) -> list[MonthlyReconciliation]:
    """
    Calculate expected vs collected premium by month for the last N months.

    Expected = sum of Policy.premium for policies that started billing in that month.
    Collected = sum of paid Payment records in that month.
    Failed = sum of failed Payment records in that month.

    Args:
        months: Number of months to look back (default 12).

    Returns:
        List of monthly reconciliation dicts, newest first.
    """
    from policies.models import Payment, Policy

    today = date.today()
    results: list[MonthlyReconciliation] = []

    MONTH_NAMES = [
        "",
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]

    for i in range(months):
        # Calculate the month we're looking at
        target_month = today.month - i
        target_year = today.year
        while target_month <= 0:
            target_month += 12
            target_year -= 1

        # First and last day of target month
        first_day = date(target_year, target_month, 1)
        if target_month == 12:
            last_day = date(target_year + 1, 1, 1)
        else:
            last_day = date(target_year, target_month + 1, 1)

        # Expected: policies that were active in this month
        # Approximation: policies effective before last_day and expiring after first_day
        active_policies = Policy.objects.filter(
            effective_date__lt=last_day,
            expiration_date__gte=first_day,
        ).exclude(status="cancelled")

        # For monthly policies: expected payment = monthly_premium each month
        # For annual policies: full premium in the effective month only
        expected = Decimal("0")
        policy_count = 0
        for p in active_policies.only(
            "billing_frequency", "premium", "monthly_premium", "effective_date"
        ):
            policy_count += 1
            if p.billing_frequency == "monthly":
                expected += p.monthly_premium or Decimal("0")
            else:
                # Annual: attribute full premium to the month the policy went effective
                if p.effective_date >= first_day and p.effective_date < last_day:
                    expected += p.premium or Decimal("0")

        # Payments collected in this month
        payments_in_month = Payment.objects.filter(
            paid_at__date__gte=first_day,
            paid_at__date__lt=last_day,
        )

        collected = payments_in_month.filter(status="paid").aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0")

        failed = payments_in_month.filter(status="failed").aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0")

        refunded = payments_in_month.filter(refund_amount__isnull=False).aggregate(
            total=Sum("refund_amount")
        )["total"] or Decimal("0")

        payment_count = payments_in_month.filter(status="paid").count()

        net_collected = collected - refunded
        collection_rate = (
            float(net_collected / expected * 100) if expected > 0 else 100.0
        )

        results.append(
            MonthlyReconciliation(
                year=target_year,
                month=target_month,
                month_label=f"{MONTH_NAMES[target_month]} {target_year}",
                expected_premium=expected,
                collected_premium=collected,
                failed_premium=failed,
                refunded_premium=refunded,
                net_collected=net_collected,
                collection_rate=round(collection_rate, 1),
                policy_count=policy_count,
                payment_count=payment_count,
            )
        )

    return results


def aging_receivables() -> list[AgingBucket]:
    """
    Calculate aging receivables in 30/60/90+ day buckets.

    A policy is considered a receivable if it is in 'past_due' status
    or has outstanding failed payments with no subsequent successful payment.

    Returns:
        List of aging buckets: 0-30, 31-60, 61-90, 90+ days.
    """
    from policies.models import Policy

    today = date.today()

    buckets: list[AgingBucket] = [
        {
            "bucket": "0-30 days",
            "policy_count": 0,
            "outstanding_amount": Decimal("0"),
            "oldest_due_days": 0,
        },
        {
            "bucket": "31-60 days",
            "policy_count": 0,
            "outstanding_amount": Decimal("0"),
            "oldest_due_days": 0,
        },
        {
            "bucket": "61-90 days",
            "policy_count": 0,
            "outstanding_amount": Decimal("0"),
            "oldest_due_days": 0,
        },
        {
            "bucket": "90+ days",
            "policy_count": 0,
            "outstanding_amount": Decimal("0"),
            "oldest_due_days": 0,
        },
    ]

    # Find past_due policies and calculate how long they've been overdue
    past_due_policies = Policy.objects.filter(
        status="past_due",
    ).prefetch_related("payments")

    for policy in past_due_policies:
        # Find the earliest failed payment date
        earliest_failure = (
            policy.payments.filter(status="failed")
            .order_by("paid_at")
            .values_list("paid_at", flat=True)
            .first()
        )
        if not earliest_failure:
            continue

        days_overdue = (today - earliest_failure.date()).days
        outstanding = policy.monthly_premium or policy.premium or Decimal("0")

        if days_overdue <= 30:
            bucket_idx = 0
        elif days_overdue <= 60:
            bucket_idx = 1
        elif days_overdue <= 90:
            bucket_idx = 2
        else:
            bucket_idx = 3

        buckets[bucket_idx]["policy_count"] += 1
        buckets[bucket_idx]["outstanding_amount"] += outstanding
        buckets[bucket_idx]["oldest_due_days"] = max(
            buckets[bucket_idx]["oldest_due_days"], days_overdue
        )

    return buckets


def collection_rate(months: int = 6) -> list[CollectionRate]:
    """
    Calculate collection rates for the last N months.

    Args:
        months: Number of months to calculate (default 6).

    Returns:
        List of monthly collection rate dicts.
    """
    monthly = monthly_premium_reconciliation(months)
    return [
        CollectionRate(
            period_label=m["month_label"],
            expected=m["expected_premium"],
            collected=m["net_collected"],
            rate=m["collection_rate"],
        )
        for m in monthly
    ]


def reconciliation_summary() -> dict:
    """
    Combined summary for the reconciliation dashboard.

    Returns:
        Dict with monthly reconciliation, aging buckets, collection rates,
        and headline metrics.
    """
    from policies.models import Payment, Policy

    today = date.today()
    thirty_days_ago = today - timedelta(days=30)

    # Headline metrics
    total_past_due = Policy.objects.filter(status="past_due").count()
    total_active = Policy.objects.filter(status="active").count()

    # Last 30 days collections
    recent_collected = Payment.objects.filter(
        status="paid",
        paid_at__date__gte=thirty_days_ago,
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")
    recent_failed = Payment.objects.filter(
        status="failed",
        paid_at__date__gte=thirty_days_ago,
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    # All time collections
    all_time_collected = Payment.objects.filter(status="paid").aggregate(
        total=Sum("amount")
    )["total"] or Decimal("0")

    monthly = monthly_premium_reconciliation(12)
    aging = aging_receivables()
    rates = collection_rate(6)

    return {
        "headline": {
            "total_active_policies": total_active,
            "total_past_due_policies": total_past_due,
            "last_30_days_collected": float(recent_collected),
            "last_30_days_failed": float(recent_failed),
            "all_time_collected": float(all_time_collected),
        },
        "monthly_reconciliation": [
            {
                **m,
                "expected_premium": float(m["expected_premium"]),
                "collected_premium": float(m["collected_premium"]),
                "failed_premium": float(m["failed_premium"]),
                "refunded_premium": float(m["refunded_premium"]),
                "net_collected": float(m["net_collected"]),
            }
            for m in monthly
        ],
        "aging_receivables": [
            {
                **bucket,
                "outstanding_amount": float(bucket["outstanding_amount"]),
            }
            for bucket in aging
        ],
        "collection_rates": [
            {
                **rate,
                "expected": float(rate["expected"]),
                "collected": float(rate["collected"]),
            }
            for rate in rates
        ],
    }
