"""
Tests for the producers signal handlers.

Covers Trello 3.6 (Commission Calculation: Account for Cancellations):
when a Policy transitions to ``cancelled``, every ``calculated`` or
``approved`` CommissionPayout attached to that policy is flipped to
``reversed`` with a populated ``reversal_reason`` and ``reversed_at``.
"""

from decimal import Decimal

from django.test import TestCase

from producers.models import CommissionPayout, PolicyProducer, Producer
from tests.factories import create_test_policy


def _producer(name="Test Producer", ptype="broker"):
    return Producer.objects.create(
        name=name,
        producer_type=ptype,
        email=f"{name.lower().replace(' ', '-')}@example.com",
    )


def _payout(policy, producer, *, amount=Decimal("100.00"), status="calculated"):
    return CommissionPayout.objects.create(
        producer=producer,
        policy=policy,
        amount=amount,
        calculation_method="percentage_of_premium",
        status=status,
    )


class CommissionReversalOnCancellationTest(TestCase):
    """Verify commission reversal flows when a Policy flips to cancelled."""

    def setUp(self):
        self.policy = create_test_policy(status="active")
        self.producer = _producer()
        PolicyProducer.objects.create(
            policy=self.policy,
            producer=self.producer,
            commission_type="percentage",
            commission_rate=Decimal("0.1500"),
        )

    def _cancel(self, policy=None):
        target = policy or self.policy
        target.status = "cancelled"
        target.save(update_fields=["status"])
        target.refresh_from_db()
        return target

    def test_calculated_payouts_are_reversed_on_cancellation(self):
        payout = _payout(self.policy, self.producer, status="calculated")

        self._cancel()

        payout.refresh_from_db()
        self.assertEqual(payout.status, "reversed")
        self.assertIn("policy_cancelled", payout.reversal_reason)
        self.assertIn(self.policy.policy_number, payout.reversal_reason)
        self.assertIsNotNone(payout.reversed_at)

    def test_approved_payouts_are_reversed_on_cancellation(self):
        payout = _payout(self.policy, self.producer, status="approved")

        self._cancel()

        payout.refresh_from_db()
        self.assertEqual(payout.status, "reversed")

    def test_paid_payouts_are_left_untouched(self):
        # Money already left the bank — you can't claw it back via a flag flip.
        payout = _payout(self.policy, self.producer, status="paid")

        self._cancel()

        payout.refresh_from_db()
        self.assertEqual(payout.status, "paid")
        self.assertEqual(payout.reversal_reason, "")
        self.assertIsNone(payout.reversed_at)

    def test_already_reversed_payouts_are_left_untouched(self):
        payout = _payout(self.policy, self.producer, status="reversed")
        original_reason = "manual_correction"
        payout.reversal_reason = original_reason
        payout.save(update_fields=["reversal_reason"])

        self._cancel()

        payout.refresh_from_db()
        self.assertEqual(payout.status, "reversed")
        self.assertEqual(payout.reversal_reason, original_reason)

    def test_other_policy_payouts_are_not_touched(self):
        """Only payouts attached to the cancelled policy are reversed."""
        other_policy = create_test_policy(status="active")
        other_payout = _payout(other_policy, self.producer, status="calculated")

        self._cancel()

        other_payout.refresh_from_db()
        self.assertEqual(other_payout.status, "calculated")

    def test_transition_from_pending_cancellation_also_reverses(self):
        """pending_cancellation → cancelled must still trigger reversal."""
        self.policy.status = "pending_cancellation"
        self.policy.save(update_fields=["status"])
        payout = _payout(self.policy, self.producer, status="calculated")

        self._cancel()

        payout.refresh_from_db()
        self.assertEqual(payout.status, "reversed")

    def test_saving_a_cancelled_policy_without_transition_is_noop(self):
        """No status transition = no reversal (prevents accidental double-reverse)."""
        # Put the policy into cancelled state + pre-reverse the payout.
        self._cancel()
        payout = _payout(self.policy, self.producer, status="calculated")
        # We're now explicitly setting up a payout AFTER cancellation.
        # Saving the already-cancelled policy again should leave the new
        # 'calculated' payout alone — no transition, no signal effect.
        self.policy.save(update_fields=["status"])

        payout.refresh_from_db()
        self.assertEqual(payout.status, "calculated")

    def test_non_cancellation_status_change_does_not_reverse(self):
        """Only transitions *to* cancelled trigger reversal."""
        payout = _payout(self.policy, self.producer, status="calculated")

        # active → pending_cancellation is not a cancellation transition.
        self.policy.status = "pending_cancellation"
        self.policy.save(update_fields=["status"])

        payout.refresh_from_db()
        self.assertEqual(payout.status, "calculated")

    def test_multiple_payouts_reversed_in_one_transition(self):
        p1 = _payout(
            self.policy, self.producer, status="calculated", amount=Decimal("10.00")
        )
        p2 = _payout(
            self.policy, self.producer, status="approved", amount=Decimal("20.00")
        )
        p3 = _payout(self.policy, self.producer, status="paid", amount=Decimal("30.00"))

        self._cancel()

        for payout, expected in ((p1, "reversed"), (p2, "reversed"), (p3, "paid")):
            payout.refresh_from_db()
            self.assertEqual(
                payout.status,
                expected,
                f"Payout with amount {payout.amount} got {payout.status}, expected {expected}",
            )
