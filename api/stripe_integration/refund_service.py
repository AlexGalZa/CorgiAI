"""
Refund workflow service for the Corgi Insurance platform.

Handles:
- Creating refund requests
- Approving refund requests (triggers Stripe refund)
- Denying refund requests
- Admin-level refund processing
"""

import logging
from decimal import Decimal

from django.utils import timezone

logger = logging.getLogger(__name__)


class RefundService:
    @staticmethod
    def create_refund_request(
        policy,
        amount: Decimal,
        reason: str,
        reason_detail: str,
        requested_by,
        stripe_payment_intent_id: str | None = None,
    ) -> "RefundRequest":  # noqa: F821
        """
        Create a new refund request for a policy.

        Args:
            policy: Policy instance
            amount: Amount to refund in USD
            reason: One of RefundRequest.REASON_CHOICES keys
            reason_detail: Free-text explanation
            requested_by: User submitting the request
            stripe_payment_intent_id: Override payment intent (auto-detected otherwise)

        Returns:
            RefundRequest instance
        """
        from stripe_integration.models import RefundRequest

        if amount <= 0:
            raise ValueError("Refund amount must be greater than zero.")
        if amount > policy.premium:
            raise ValueError(
                f"Refund amount ${amount} exceeds policy premium ${policy.premium}."
            )

        # Auto-detect payment intent from policy if not provided
        if not stripe_payment_intent_id:
            stripe_payment_intent_id = policy.stripe_payment_intent_id

        refund_request = RefundRequest.objects.create(
            policy=policy,
            amount=amount,
            reason=reason,
            reason_detail=reason_detail,
            status="pending",
            requested_by=requested_by,
            stripe_payment_intent_id=stripe_payment_intent_id,
        )

        logger.info(
            "Refund request #%s created for policy %s (amount: $%s, reason: %s)",
            refund_request.pk,
            policy.policy_number,
            amount,
            reason,
        )

        return refund_request

    @staticmethod
    def approve_refund(refund_request_id: int, approved_by) -> "RefundRequest":  # noqa: F821
        """
        Approve a refund request and process it via Stripe.

        Calls Stripe refund API with the payment intent ID.
        On success, sets status=processed and records stripe_refund_id.
        On failure, sets status=failed.

        Args:
            refund_request_id: ID of the RefundRequest to approve
            approved_by: Staff User approving the request

        Returns:
            Updated RefundRequest instance
        """
        from stripe_integration.models import RefundRequest

        rr = RefundRequest.objects.select_related("policy").get(pk=refund_request_id)

        if rr.status != "pending":
            raise ValueError(
                f"Refund request #{rr.pk} is not in pending status (current: {rr.status})."
            )

        rr.approved_by = approved_by
        rr.approved_at = timezone.now()
        rr.status = "approved"
        rr.save(update_fields=["approved_by", "approved_at", "status", "updated_at"])

        # Process the Stripe refund
        try:
            stripe_refund = RefundService._process_stripe_refund(rr)
            rr.stripe_refund_id = stripe_refund.id
            rr.status = "processed"
            rr.processed_at = timezone.now()
            rr.save(
                update_fields=[
                    "stripe_refund_id",
                    "status",
                    "processed_at",
                    "updated_at",
                ]
            )

            logger.info(
                "Refund #%s processed via Stripe (refund_id=%s, amount=$%s)",
                rr.pk,
                stripe_refund.id,
                rr.amount,
            )

        except Exception as e:
            rr.status = "failed"
            rr.denial_reason = f"Stripe error: {e}"
            rr.save(update_fields=["status", "denial_reason", "updated_at"])

            logger.exception(
                "Stripe refund failed for refund request #%s: %s",
                rr.pk,
                e,
            )
            raise ValueError(f"Stripe refund failed: {e}") from e

        return rr

    @staticmethod
    def deny_refund(
        refund_request_id: int,
        denied_by,
        denial_reason: str = "",
    ) -> "RefundRequest":  # noqa: F821
        """
        Deny a refund request.

        Args:
            refund_request_id: ID of the RefundRequest to deny
            denied_by: Staff User denying the request
            denial_reason: Explanation shown to the customer

        Returns:
            Updated RefundRequest instance
        """
        from stripe_integration.models import RefundRequest

        rr = RefundRequest.objects.get(pk=refund_request_id)

        if rr.status != "pending":
            raise ValueError(
                f"Refund request #{rr.pk} is not in pending status (current: {rr.status})."
            )

        rr.status = "denied"
        rr.approved_by = denied_by
        rr.approved_at = timezone.now()
        rr.denial_reason = denial_reason
        rr.save(
            update_fields=[
                "status",
                "approved_by",
                "approved_at",
                "denial_reason",
                "updated_at",
            ]
        )

        logger.info(
            "Refund request #%s denied by %s",
            rr.pk,
            denied_by,
        )

        return rr

    @staticmethod
    def _process_stripe_refund(rr) -> object:
        """
        Call Stripe to process the refund.

        Prefers payment_intent refund. Falls back to charge refund if no PI.
        """
        import stripe
        from django.conf import settings

        stripe.api_key = settings.STRIPE_SECRET_KEY

        amount_cents = int(rr.amount * 100)

        if rr.stripe_payment_intent_id:
            return stripe.Refund.create(
                payment_intent=rr.stripe_payment_intent_id,
                amount=amount_cents,
                reason="requested_by_customer",
                metadata={
                    "refund_request_id": str(rr.pk),
                    "policy_number": rr.policy.policy_number,
                    "requested_by": str(rr.requested_by_id),
                },
            )

        # No payment intent — try to find from policy charges
        charges = stripe.Charge.list(
            limit=5,
            metadata={"policy_number": rr.policy.policy_number},
        )
        if charges.data:
            return stripe.Refund.create(
                charge=charges.data[0].id,
                amount=amount_cents,
                reason="requested_by_customer",
                metadata={
                    "refund_request_id": str(rr.pk),
                    "policy_number": rr.policy.policy_number,
                },
            )

        raise ValueError(
            f"No Stripe payment intent or charge found for policy {rr.policy.policy_number}."
        )
