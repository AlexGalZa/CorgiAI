"""
Management command: calculate_earned_premium

Processes active policies and calculates earned vs unearned premium
prorated over the policy period for GAAP revenue recognition.

Usage:
    python manage.py calculate_earned_premium
    python manage.py calculate_earned_premium --month 2026-03
    python manage.py calculate_earned_premium --dry-run
"""

import datetime
from decimal import Decimal

from django.core.management.base import BaseCommand

from policies.models import Policy, EarnedPremiumRecord


def get_period_bounds(month_str: str | None) -> tuple[datetime.date, datetime.date]:
    """Return (period_start, period_end) for the given month string or current month."""
    if month_str:
        year, month = map(int, month_str.split("-"))
    else:
        today = datetime.date.today()
        year, month = today.year, today.month

    period_start = datetime.date(year, month, 1)
    if month == 12:
        period_end = datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
    else:
        period_end = datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)

    return period_start, period_end


def calculate_earned_for_policy(
    policy: Policy,
    period_start: datetime.date,
    period_end: datetime.date,
) -> tuple[Decimal, Decimal]:
    """
    Calculate earned and unearned premium for a policy during the given period.

    Earned premium = total_premium × (days_in_period_covered / total_policy_days)
    Unearned premium = total_premium - cumulative_earned_up_to_period_end
    """
    total_premium = policy.premium or Decimal("0")
    eff = policy.effective_date
    exp = policy.expiration_date

    total_days = (exp - eff).days
    if total_days <= 0:
        return Decimal("0"), total_premium

    # Overlap of policy with reporting period
    overlap_start = max(eff, period_start)
    overlap_end = min(exp, period_end)

    if overlap_start >= overlap_end:
        # Policy doesn't overlap with this period
        return Decimal("0"), total_premium

    days_in_period = (overlap_end - overlap_start).days
    earned_fraction = Decimal(days_in_period) / Decimal(total_days)
    earned_amount = (total_premium * earned_fraction).quantize(Decimal("0.01"))

    # Unearned = what's left after period_end
    days_remaining = max(0, (exp - period_end).days)
    unearned_fraction = Decimal(days_remaining) / Decimal(total_days)
    unearned_amount = (total_premium * unearned_fraction).quantize(Decimal("0.01"))

    return earned_amount, unearned_amount


class Command(BaseCommand):
    help = "Calculate earned and unearned premium for active policies (GAAP revenue recognition)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--month",
            type=str,
            default=None,
            help="Month to calculate for in YYYY-MM format (defaults to current month)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print results without saving to database",
        )

    def handle(self, *args, **options):
        month = options["month"]
        dry_run = options["dry_run"]

        period_start, period_end = get_period_bounds(month)
        self.stdout.write(
            self.style.NOTICE(
                f"Calculating earned premium for period {period_start} – {period_end}"
                + (" [DRY RUN]" if dry_run else "")
            )
        )

        # Active policies that overlap with this period
        policies = Policy.objects.filter(
            status="active",
            effective_date__lt=period_end,
            expiration_date__gt=period_start,
        )

        created = 0
        updated = 0
        total_earned = Decimal("0")
        total_unearned = Decimal("0")

        for policy in policies:
            earned, unearned = calculate_earned_for_policy(
                policy, period_start, period_end
            )
            total_earned += earned
            total_unearned += unearned

            if dry_run:
                self.stdout.write(
                    f"  {policy.policy_number}: earned=${earned}, unearned=${unearned}"
                )
                continue

            record, was_created = EarnedPremiumRecord.objects.update_or_create(
                policy=policy,
                period_start=period_start,
                period_end=period_end,
                defaults={
                    "earned_amount": earned,
                    "unearned_amount": unearned,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Done. Created: {created}, Updated: {updated}. "
                    f"Total earned: ${total_earned:,.2f}, Total unearned: ${total_unearned:,.2f}"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"[DRY RUN] {policies.count()} policies. "
                    f"Total earned would be: ${total_earned:,.2f}, unearned: ${total_unearned:,.2f}"
                )
            )
