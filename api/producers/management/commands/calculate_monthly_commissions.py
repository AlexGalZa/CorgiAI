"""
Management command: ``calculate_monthly_commissions``

Trello 3.6 — Commission Calculation: Monthly Pay cadence.

Iterates every active ``PolicyProducer`` assignment whose parent ``Policy``
overlaps the target month and computes the producer's commission for that
month, prorated by the number of days the policy was active within the month.

For each (producer, policy, month) triple, we create or update a
``CommissionPayout`` row with ``status='calculated'`` and
``period_start``/``period_end`` pinned to the month window. A summary is
printed at the end grouping totals by producer.

Usage:
    python manage.py calculate_monthly_commissions
    python manage.py calculate_monthly_commissions --month 2026-04
    python manage.py calculate_monthly_commissions --dry-run
    python manage.py calculate_monthly_commissions --month 2026-03 --dry-run

Prorated formula (per (policy, producer)):

    days_active  = max(0, min(policy.expiration_date, month_end)
                          - max(policy.effective_date, month_start) + 1 day)
    days_in_month = calendar.monthrange(year, month)[1]

    If commission_type == 'flat':
        monthly_base = commission_amount / 12
        amount       = monthly_base * (days_active / days_in_month)
    Else (percentage):
        rate         = commission_rate or DEFAULT_COMMISSION_RATE
        monthly_prem = policy.monthly_premium or (policy.premium / 12)
        amount       = monthly_prem * rate * (days_active / days_in_month)
"""

import calendar
import logging
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from policies.models import Policy
from producers.models import CommissionPayout, PolicyProducer


logger = logging.getLogger(__name__)

DEFAULT_COMMISSION_RATE = Decimal("0.10")
TWO_PLACES = Decimal("0.01")

# Statuses where the policy is considered "live" for commission accrual
ACCRUING_POLICY_STATUSES = ("active", "past_due", "cancelled", "expired", "non_renewed")


def _parse_month(raw: str) -> tuple[date, date, int]:
    """Return ``(month_start, month_end, days_in_month)`` for ``YYYY-MM``."""
    try:
        parsed = datetime.strptime(raw, "%Y-%m").date()
    except ValueError as exc:
        raise CommandError(f"--month must be in YYYY-MM format (got {raw!r})") from exc
    days_in_month = calendar.monthrange(parsed.year, parsed.month)[1]
    start = parsed.replace(day=1)
    end = parsed.replace(day=days_in_month)
    return start, end, days_in_month


def _default_month_window() -> tuple[date, date, int]:
    """Default to the previous completed calendar month."""
    today = timezone.localdate()
    first_of_this_month = today.replace(day=1)
    last_of_prev = first_of_this_month - timedelta(days=1)
    days_in_month = calendar.monthrange(last_of_prev.year, last_of_prev.month)[1]
    start = last_of_prev.replace(day=1)
    return start, last_of_prev, days_in_month


def _days_active(policy: Policy, month_start: date, month_end: date) -> int:
    """Inclusive count of days the policy was in force during [month_start, month_end]."""
    if not policy.effective_date or not policy.expiration_date:
        return 0
    window_start = max(policy.effective_date, month_start)
    window_end = min(policy.expiration_date, month_end)
    if window_end < window_start:
        return 0
    return (window_end - window_start).days + 1


def _compute_amount(
    assignment: PolicyProducer,
    policy: Policy,
    days_active: int,
    days_in_month: int,
) -> tuple[Decimal, str]:
    """Return ``(amount, calculation_method)`` for this assignment+month."""
    if days_active <= 0 or days_in_month <= 0:
        return Decimal("0.00"), "percentage_of_premium"

    proration = Decimal(days_active) / Decimal(days_in_month)

    if assignment.commission_type == "flat" and assignment.commission_amount:
        monthly_base = assignment.commission_amount / Decimal(12)
        amount = monthly_base * proration
        method = "flat_fee"
    else:
        rate = assignment.commission_rate or DEFAULT_COMMISSION_RATE
        if policy.monthly_premium:
            monthly_prem = policy.monthly_premium
        elif policy.premium:
            monthly_prem = policy.premium / Decimal(12)
        else:
            monthly_prem = Decimal("0")
        amount = monthly_prem * rate * proration
        method = "percentage_of_premium"

    return amount.quantize(TWO_PLACES, rounding=ROUND_HALF_UP), method


class Command(BaseCommand):
    help = (
        "Calculate (or recalculate) monthly commission payouts for every active "
        "PolicyProducer, prorated by days the policy was live in the target month."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--month",
            type=str,
            default=None,
            help="Target month in YYYY-MM form. Defaults to the previous completed month.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Compute and print totals but do not write any CommissionPayout rows.",
        )

    def handle(self, *args, **options):
        raw_month = options.get("month")
        dry_run = bool(options.get("dry_run"))

        if raw_month:
            month_start, month_end, days_in_month = _parse_month(raw_month)
        else:
            month_start, month_end, days_in_month = _default_month_window()

        self.stdout.write(
            self.style.NOTICE(
                f"Calculating monthly commissions for "
                f"{month_start.isoformat()} .. {month_end.isoformat()} "
                f"({days_in_month} days)"
                f"{' [DRY RUN]' if dry_run else ''}"
            )
        )

        # Every PolicyProducer whose policy overlaps this month and has an
        # accruing status. We use a generous status filter so commissions still
        # accrue for the portion of the month prior to cancellation/expiration.
        assignments = PolicyProducer.objects.select_related(
            "producer", "policy"
        ).filter(
            policy__effective_date__lte=month_end,
            policy__expiration_date__gte=month_start,
            policy__status__in=ACCRUING_POLICY_STATUSES,
            producer__is_active=True,
        )

        created_count = 0
        updated_count = 0
        skipped_count = 0
        by_producer: dict[int, dict] = defaultdict(
            lambda: {"name": "", "total": Decimal("0.00"), "rows": 0}
        )

        for assignment in assignments.iterator():
            policy = assignment.policy
            days_active = _days_active(policy, month_start, month_end)
            if days_active <= 0:
                skipped_count += 1
                continue

            amount, method = _compute_amount(
                assignment, policy, days_active, days_in_month
            )

            bucket = by_producer[assignment.producer_id]
            bucket["name"] = assignment.producer.name
            bucket["total"] += amount
            bucket["rows"] += 1

            if dry_run:
                continue

            with transaction.atomic():
                existing = (
                    CommissionPayout.objects.select_for_update()
                    .filter(
                        producer=assignment.producer,
                        policy=policy,
                        period_start=month_start,
                        period_end=month_end,
                    )
                    .first()
                )
                if existing is None:
                    CommissionPayout.objects.create(
                        producer=assignment.producer,
                        policy=policy,
                        amount=amount,
                        calculation_method=method,
                        status="calculated",
                        period_start=month_start,
                        period_end=month_end,
                        notes=(
                            f"Monthly accrual {month_start.isoformat()}..{month_end.isoformat()} "
                            f"({days_active}/{days_in_month} days)"
                        ),
                    )
                    created_count += 1
                elif existing.status in ("calculated",):
                    existing.amount = amount
                    existing.calculation_method = method
                    existing.notes = (
                        f"Monthly accrual {month_start.isoformat()}..{month_end.isoformat()} "
                        f"({days_active}/{days_in_month} days)"
                    )
                    existing.save(
                        update_fields=[
                            "amount",
                            "calculation_method",
                            "notes",
                            "updated_at",
                        ]
                    )
                    updated_count += 1
                else:
                    skipped_count += 1

        # Summary
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=== Per-producer totals ==="))
        grand_total = Decimal("0.00")
        for pid, info in sorted(by_producer.items(), key=lambda kv: kv[1]["name"]):
            grand_total += info["total"]
            self.stdout.write(
                f"  {info['name']:<40s}  rows={info['rows']:<4d}  total=${info['total']:,.2f}"
            )
        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Grand total: ${grand_total:,.2f}  "
                f"(created={created_count}, updated={updated_count}, skipped={skipped_count})"
            )
        )
        if dry_run:
            self.stdout.write(
                self.style.WARNING("Dry run — no CommissionPayout rows were written.")
            )
