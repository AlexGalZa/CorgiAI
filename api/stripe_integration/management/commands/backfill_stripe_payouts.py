"""
Management command to backfill ``PolicyTransaction.stripe_payout_id`` for
historical policies by walking Stripe payouts in reverse chronological
order.

For every Stripe payout we enumerate the balance transactions it covered
(``stripe.BalanceTransaction.list(payout=<id>, type='charge')``), resolve
each charge to its originating payment intent, then match that payment
intent to ``Policy.stripe_payment_intent_id`` and stamp the payout ID on
every related ``PolicyTransaction``.

A single charge can fan out to multiple policy transactions when the
customer bundled coverages on one payment — every matching row is updated.

Refs Trello card 2.1 "Store Stripe Payout IDs on Django Policy Records".

Usage::

    python manage.py backfill_stripe_payouts
    python manage.py backfill_stripe_payouts --since 2025-01-01
    python manage.py backfill_stripe_payouts --dry-run
    python manage.py backfill_stripe_payouts --overwrite
"""

import logging
from datetime import datetime, timezone as dt_timezone

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Backfill PolicyTransaction.stripe_payout_id from Stripe payouts so "
        "finance can trace money from policy to bank deposit. Walks payouts "
        "-> balance transactions -> charges -> policies -> transactions."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--since",
            type=str,
            default=None,
            help="Only walk payouts created on or after this date (YYYY-MM-DD).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Log what would change but do not write to the database.",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Overwrite existing stripe_payout_id values. Default: only "
            "fill rows where the field is currently NULL.",
        )

    def handle(self, *args, **options):
        since_str = options.get("since")
        dry_run: bool = options.get("dry_run", False)
        overwrite: bool = options.get("overwrite", False)

        since_ts = self._parse_since(since_str)

        # Import lazily so tooling like `python -m py_compile` works without
        # Django settings being loaded.
        from stripe_integration.service import StripeService
        from policies.models import Policy, PolicyTransaction

        stripe_client = StripeService.get_client()

        list_kwargs = {"limit": 100}
        if since_ts is not None:
            list_kwargs["created"] = {"gte": since_ts}

        payouts_walked = 0
        charges_seen = 0
        transactions_updated = 0
        policies_touched: set[int] = set()
        unmatched_charges = 0

        try:
            payouts = stripe_client.Payout.list(**list_kwargs).auto_paging_iter()

            for payout in payouts:
                payouts_walked += 1
                payout_id = getattr(payout, "id", None)
                if not payout_id:
                    continue

                # Walk every balance transaction covered by this payout and
                # pick out the ones backed by a charge.
                bt_iter = stripe_client.BalanceTransaction.list(
                    payout=payout_id,
                    type="charge",
                    limit=100,
                ).auto_paging_iter()

                for bt in bt_iter:
                    charge_id = getattr(bt, "source", None)
                    if not charge_id or not str(charge_id).startswith("ch_"):
                        continue
                    charges_seen += 1

                    try:
                        charge = stripe_client.Charge.retrieve(charge_id)
                    except Exception as exc:  # pragma: no cover — API guard
                        logger.warning(
                            "Could not retrieve charge %s for payout %s: %s",
                            charge_id,
                            payout_id,
                            exc,
                        )
                        continue

                    payment_intent_id = charge.get("payment_intent")
                    if not payment_intent_id:
                        unmatched_charges += 1
                        continue

                    policy_ids = list(
                        Policy.objects.filter(
                            stripe_payment_intent_id=payment_intent_id,
                        ).values_list("id", flat=True)
                    )
                    if not policy_ids:
                        unmatched_charges += 1
                        continue

                    policies_touched.update(policy_ids)

                    txn_qs = PolicyTransaction.objects.filter(
                        policy_id__in=policy_ids,
                    )
                    if not overwrite:
                        txn_qs = txn_qs.filter(
                            Q(stripe_payout_id__isnull=True) | Q(stripe_payout_id=""),
                        )

                    if dry_run:
                        count = txn_qs.count()
                        transactions_updated += count
                        self.stdout.write(
                            f"[dry-run] would stamp payout {payout_id} on "
                            f"{count} transaction(s) for payment_intent "
                            f"{payment_intent_id}"
                        )
                    else:
                        count = txn_qs.update(stripe_payout_id=payout_id)
                        transactions_updated += count
                        if count:
                            logger.info(
                                "Stamped payout %s on %d transaction(s) for payment_intent %s",
                                payout_id,
                                count,
                                payment_intent_id,
                            )
        except Exception as exc:
            raise CommandError(f"Backfill failed: {exc}") from exc

        summary = (
            f"Walked {payouts_walked} payout(s); inspected {charges_seen} "
            f"charge(s); {unmatched_charges} unmatched; updated "
            f"{transactions_updated} PolicyTransaction row(s) across "
            f"{len(policies_touched)} polic{'y' if len(policies_touched) == 1 else 'ies'}"
            f"{' (dry-run)' if dry_run else ''}."
        )
        self.stdout.write(self.style.SUCCESS(summary))

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
