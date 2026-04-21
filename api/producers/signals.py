"""
Signal handlers for the ``producers`` app.

Trello 3.6 — Commission Calculation: Account for Cancellations.

When a ``Policy`` transitions from any non-cancelled status to ``cancelled``,
reverse every unpaid/pending ``CommissionPayout`` row that belongs to the
policy's ``PolicyProducer`` assignments. Reversal marks the payout with
``status='reversed'`` and stamps a ``reversal_reason`` for the audit trail.

A payout is considered "unpaid/pending" when its ``status`` is one of
``calculated`` or ``approved``. Payouts already ``paid`` or ``reversed`` are
left untouched (you cannot claw back money that already left the bank via
Stripe — that requires a manual refund flow).
"""

import logging

from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone

from policies.models import Policy
from producers.models import CommissionPayout


logger = logging.getLogger(__name__)


REVERSIBLE_STATUSES = ("calculated", "approved")
CANCELLED_STATUS = "cancelled"


@receiver(pre_save, sender=Policy)
def _capture_previous_policy_status(sender, instance: Policy, **kwargs):
    """Cache the prior ``status`` on the instance so ``post_save`` can detect transitions."""
    if not instance.pk:
        instance._previous_status = None
        return
    try:
        previous = Policy.objects.only("status").get(pk=instance.pk)
        instance._previous_status = previous.status
    except Policy.DoesNotExist:
        instance._previous_status = None


@receiver(post_save, sender=Policy)
def reverse_commissions_on_cancellation(
    sender, instance: Policy, created: bool, **kwargs
):
    """
    When a policy becomes cancelled, reverse every pending/unpaid CommissionPayout
    associated with that policy.
    """
    if created:
        # A brand-new policy can't have pre-existing payouts; skip.
        return

    previous_status = getattr(instance, "_previous_status", None)
    if instance.status != CANCELLED_STATUS:
        return
    if previous_status == CANCELLED_STATUS:
        # No transition — already cancelled on a prior save.
        return

    now = timezone.now()
    reason = f"policy_cancelled:{instance.policy_number}"

    qs = CommissionPayout.objects.filter(
        policy=instance,
        status__in=REVERSIBLE_STATUSES,
    )
    updated = qs.update(
        status="reversed",
        reversal_reason=reason,
        reversed_at=now,
        updated_at=now,
    )

    if updated:
        logger.info(
            "Reversed %s commission payout(s) for cancelled policy %s",
            updated,
            instance.policy_number,
        )
