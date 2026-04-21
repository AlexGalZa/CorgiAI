"""
Backfill Cession records for existing non-brokered PolicyTransactions.

Usage:
    python manage.py backfill_cessions
    python manage.py backfill_cessions --dry-run
"""

from decimal import Decimal

from django.core.management.base import BaseCommand

from common.constants import (
    DEFAULT_ATTACHMENT_POINT,
    DEFAULT_CEDED_PREMIUM_RATE,
    DEFAULT_REINSURANCE_TYPE,
    DEFAULT_REINSURER_NAME,
    DEFAULT_TREATY_ID,
)
from policies.models import Cession, PolicyTransaction


class Command(BaseCommand):
    help = "Backfill Cession records for existing non-brokered PolicyTransactions"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be created without actually creating",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write("DRY RUN - no changes will be made\n")

        transactions = (
            PolicyTransaction.objects.filter(
                policy__is_brokered=False,
            )
            .exclude(
                cessions__isnull=False,
            )
            .select_related("policy")
        )

        count = transactions.count()
        self.stdout.write(f"Found {count} non-brokered transactions without cessions\n")

        created = 0
        for txn in transactions.iterator():
            ceded_premium_amount = (
                txn.gross_written_premium * Decimal(DEFAULT_CEDED_PREMIUM_RATE)
            ).quantize(Decimal("0.01"))

            if dry_run:
                self.stdout.write(
                    f"  Would create: {txn.policy.policy_number} "
                    f"txn={txn.id} gwp={txn.gross_written_premium} "
                    f"ceded={ceded_premium_amount}\n"
                )
            else:
                Cession.objects.create(
                    transaction=txn,
                    treaty_id=DEFAULT_TREATY_ID,
                    reinsurance_type=DEFAULT_REINSURANCE_TYPE,
                    attachment_point=Decimal(DEFAULT_ATTACHMENT_POINT),
                    ceded_premium_rate=Decimal(DEFAULT_CEDED_PREMIUM_RATE),
                    ceded_premium_amount=ceded_premium_amount,
                    reinsurer_name=DEFAULT_REINSURER_NAME,
                )
            created += 1

        action = "Would create" if dry_run else "Created"
        self.stdout.write(self.style.SUCCESS(f"{action} {created} cession records\n"))
