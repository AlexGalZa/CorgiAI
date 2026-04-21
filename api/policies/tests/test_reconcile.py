"""Tests for the Stripe reconciler's scheduling cursor.

The reconciler must pick policies in ``last_reconciled_at`` nulls-first
order so a newly-subscribed policy (``last_reconciled_at=None``) is
scanned before one that was already reconciled an hour ago. This guards
against a silent dropped-webhook backlog — if ordering regresses to
e.g. ``updated_at``, brand-new rows can starve behind recently-edited
ones.
"""

from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from common.tasks import reconcile_stripe_state
from tests.factories import create_test_policy


class ReconcileSchedulingOrderTest(TestCase):
    """Verify reconciler ordering by ``last_reconciled_at`` nulls-first."""

    def test_null_last_reconciled_at_scanned_before_older_row(self):
        now = timezone.now()

        never_reconciled = create_test_policy()
        never_reconciled.stripe_subscription_id = "sub_never"
        never_reconciled.last_reconciled_at = None
        never_reconciled.save(
            update_fields=["stripe_subscription_id", "last_reconciled_at"],
            skip_validation=True,
        )

        recently_reconciled = create_test_policy()
        recently_reconciled.stripe_subscription_id = "sub_recent"
        recently_reconciled.last_reconciled_at = now - timedelta(hours=1)
        recently_reconciled.save(
            update_fields=["stripe_subscription_id", "last_reconciled_at"],
            skip_validation=True,
        )

        scan_order: list[str] = []

        class _StubStripe:
            class Subscription:
                @staticmethod
                def retrieve(sub_id):
                    scan_order.append(sub_id)
                    return {"status": "active", "current_period_end": None}

        with patch(
            "stripe_integration.service.StripeService.get_client",
            return_value=_StubStripe(),
        ):
            with patch("common.tasks.time.sleep"):
                reconcile_stripe_state()

        self.assertEqual(scan_order[0], "sub_never")
        self.assertIn("sub_recent", scan_order)
        self.assertLess(scan_order.index("sub_never"), scan_order.index("sub_recent"))

    def test_stamps_last_reconciled_at_on_every_row(self):
        before = timezone.now()

        policy = create_test_policy()
        policy.stripe_subscription_id = "sub_stamp"
        policy.last_reconciled_at = None
        policy.save(
            update_fields=["stripe_subscription_id", "last_reconciled_at"],
            skip_validation=True,
        )

        class _StubStripe:
            class Subscription:
                @staticmethod
                def retrieve(sub_id):
                    return {"status": "active", "current_period_end": None}

        with patch(
            "stripe_integration.service.StripeService.get_client",
            return_value=_StubStripe(),
        ):
            with patch("common.tasks.time.sleep"):
                reconcile_stripe_state()

        policy.refresh_from_db()
        self.assertIsNotNone(policy.last_reconciled_at)
        self.assertGreaterEqual(policy.last_reconciled_at, before)
