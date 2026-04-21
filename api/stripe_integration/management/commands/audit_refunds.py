"""
Management command to audit Stripe refunds against expected (Django-computed)
refund amounts.

Pulls refunds from Stripe, locates the corresponding Corgi ``Policy`` (via
``stripe_payment_intent_id`` or the ``policy_number`` metadata on the
underlying charge), computes the expected pro-rated unused-premium refund,
subtracts any non-refundable fees from the most recent ``PolicyTransaction``,
and emits a CSV diff.

This command is strictly read-only — it never mutates Stripe or Django data.

Refs Trello card "Verify Refund Calculations" (4.5).

Usage:
    python manage.py audit_refunds
    python manage.py audit_refunds --since 2026-01-01
    python manage.py audit_refunds --output /tmp/refund_audit.csv
    python manage.py audit_refunds --tolerance 0.50
"""

import csv
import logging
import sys
from datetime import datetime, timezone as dt_timezone
from decimal import Decimal, ROUND_HALF_UP

from django.core.management.base import BaseCommand, CommandError

logger = logging.getLogger(__name__)

CENTS = Decimal("0.01")


class Command(BaseCommand):
    help = (
        "Audit Stripe refunds against expected pro-rated refund amounts "
        "computed from Django policy data. Read-only. Emits CSV."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--since",
            type=str,
            default=None,
            help="Only audit refunds created on or after this date (YYYY-MM-DD).",
        )
        parser.add_argument(
            "--output",
            type=str,
            default=None,
            help="Path to write the CSV report. Defaults to stdout.",
        )
        parser.add_argument(
            "--tolerance",
            type=float,
            default=1.0,
            help="Absolute dollar tolerance for the expected vs actual diff "
            "(default: 1.0 — i.e. within_tolerance = abs(diff) <= $1.00).",
        )

    def handle(self, *args, **options):
        since_str = options.get("since")
        output_path = options.get("output")
        tolerance = Decimal(str(options.get("tolerance", 1.0)))

        since_ts = self._parse_since(since_str)

        # Import lazily so `python -m py_compile` works without Django settings.
        from stripe_integration.service import StripeService

        stripe_client = StripeService.get_client()

        # Open the output sink (stdout or file).
        if output_path:
            fh = open(output_path, "w", newline="", encoding="utf-8")
            close_fh = True
        else:
            fh = sys.stdout
            close_fh = False

        writer = csv.writer(fh)
        writer.writerow(
            [
                "refund_id",
                "policy_number",
                "stripe_amount",
                "expected_amount",
                "diff",
                "within_tolerance",
            ]
        )

        total_refunds = 0
        discrepancies = 0
        total_diff = Decimal("0.00")

        try:
            list_kwargs = {"limit": 100}
            if since_ts is not None:
                list_kwargs["created"] = {"gte": since_ts}

            # auto_paging_iter handles pagination across the full result set.
            refunds = stripe_client.Refund.list(**list_kwargs).auto_paging_iter()

            for refund in refunds:
                total_refunds += 1

                stripe_amount = self._cents_to_dollars(
                    getattr(refund, "amount", 0) or 0
                )

                policy = self._locate_policy(stripe_client, refund)
                if policy is None:
                    # No policy match — still emit a row so the operator can triage.
                    writer.writerow(
                        [
                            refund.id,
                            "",
                            f"{stripe_amount:.2f}",
                            "",
                            "",
                            "",
                        ]
                    )
                    continue

                expected_amount = self._expected_refund_amount(policy, refund)
                diff = (stripe_amount - expected_amount).quantize(
                    CENTS, rounding=ROUND_HALF_UP
                )
                within_tolerance = abs(diff) <= tolerance

                if not within_tolerance:
                    discrepancies += 1
                total_diff += diff

                writer.writerow(
                    [
                        refund.id,
                        policy.policy_number,
                        f"{stripe_amount:.2f}",
                        f"{expected_amount:.2f}",
                        f"{diff:.2f}",
                        str(bool(within_tolerance)).lower(),
                    ]
                )
        finally:
            if close_fh:
                fh.close()

        # Summary footer — always to stderr so it doesn't pollute the CSV stream.
        summary = (
            f"Audited {total_refunds} refund(s); "
            f"{discrepancies} outside tolerance (±${tolerance}); "
            f"total $diff = ${total_diff:.2f}"
        )
        self.stderr.write(summary)

    # ── Helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_since(since_str):
        if not since_str:
            return None
        try:
            dt = datetime.strptime(since_str, "%Y-%m-%d").replace(
                tzinfo=dt_timezone.utc
            )
        except ValueError as e:
            raise CommandError(
                f"--since must be in YYYY-MM-DD format (got {since_str!r})."
            ) from e
        return int(dt.timestamp())

    @staticmethod
    def _cents_to_dollars(cents) -> Decimal:
        return (Decimal(int(cents)) / Decimal(100)).quantize(
            CENTS, rounding=ROUND_HALF_UP
        )

    @staticmethod
    def _locate_policy(stripe_client, refund):
        """
        Find the Corgi Policy that corresponds to a Stripe refund.

        Priority:
        1. Match refund.payment_intent → Policy.stripe_payment_intent_id
        2. Fall back to the charge metadata "policy_number"
        """
        from policies.models import Policy

        payment_intent_id = getattr(refund, "payment_intent", None)
        if payment_intent_id:
            policy = Policy.objects.filter(
                stripe_payment_intent_id=payment_intent_id
            ).first()
            if policy:
                return policy

        charge_id = getattr(refund, "charge", None)
        if charge_id:
            try:
                charge = stripe_client.Charge.retrieve(charge_id)
            except Exception as exc:  # pragma: no cover — network/API guard
                logger.warning(
                    "Could not retrieve charge %s for refund %s: %s",
                    charge_id,
                    refund.id,
                    exc,
                )
                return None

            metadata = getattr(charge, "metadata", {}) or {}
            policy_number = metadata.get("policy_number")
            if policy_number:
                return Policy.objects.filter(policy_number=policy_number).first()

        return None

    @staticmethod
    def _expected_refund_amount(policy, refund) -> Decimal:
        """
        Expected refund = prorated unused portion of the premium, minus any
        non-refundable fees captured on the most recent PolicyTransaction.

        Formula:
            unused_ratio = days(refund.created → policy.expiration_date)
                         / days(policy.effective_date → policy.expiration_date)
            expected     = premium * unused_ratio - admin_fee - processor_fee
        """
        from policies.models import PolicyTransaction

        refund_created_ts = getattr(refund, "created", None)
        if refund_created_ts is None:
            return Decimal("0.00")

        refund_date = datetime.fromtimestamp(
            int(refund_created_ts), tz=dt_timezone.utc
        ).date()

        effective = policy.effective_date
        expiration = policy.expiration_date

        total_days = (expiration - effective).days
        if total_days <= 0:
            return Decimal("0.00")

        # Cap remaining days to the policy window [0, total_days].
        remaining_days = (expiration - refund_date).days
        if remaining_days < 0:
            remaining_days = 0
        if remaining_days > total_days:
            remaining_days = total_days

        premium = Decimal(policy.premium or 0)
        unused_ratio = Decimal(remaining_days) / Decimal(total_days)
        prorated = premium * unused_ratio

        # Subtract any non-refundable fees on the latest transaction.
        non_refundable = Decimal("0.00")
        latest_txn = (
            PolicyTransaction.objects.filter(policy=policy)
            .order_by("-accounting_date", "-created_at")
            .first()
        )
        if latest_txn is not None:
            admin_fee = getattr(latest_txn, "admin_fee_amount", None)
            if admin_fee:
                non_refundable += Decimal(admin_fee)

            # Stripe processor fee — may live as a custom attr on the transaction
            # depending on environment; guarded with getattr for forward-compat.
            processor_fee = getattr(latest_txn, "stripe_processor_fee", None)
            if processor_fee:
                non_refundable += Decimal(processor_fee)

        expected = prorated - non_refundable
        if expected < 0:
            expected = Decimal("0.00")

        return expected.quantize(CENTS, rounding=ROUND_HALF_UP)
