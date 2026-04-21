"""
Commission payout service for Corgi producers.

Calculates commissions from policy premiums and manages the payout lifecycle.
"""

from decimal import Decimal
from django.utils import timezone

from policies.models import Policy
from producers.models import PolicyProducer, CommissionPayout


DEFAULT_COMMISSION_RATE = Decimal("0.10")  # 10% default if no explicit rate set


def calculate_commissions_for_policy(policy: Policy) -> list[CommissionPayout]:
    """
    Calculate commission payouts for all producers assigned to a policy.
    Creates CommissionPayout records with status='calculated'.

    Returns list of created CommissionPayout objects.
    """
    assignments = PolicyProducer.objects.filter(policy=policy).select_related(
        "producer"
    )
    payouts = []

    for assignment in assignments:
        # Skip if a payout already exists for this producer+policy
        if CommissionPayout.objects.filter(
            producer=assignment.producer, policy=policy
        ).exists():
            continue

        if assignment.commission_type == "flat" and assignment.commission_amount:
            amount = assignment.commission_amount
            method = "flat_fee"
        else:
            rate = assignment.commission_rate or DEFAULT_COMMISSION_RATE
            amount = (policy.premium or Decimal("0")) * rate
            method = "percentage_of_premium"

        payout = CommissionPayout.objects.create(
            producer=assignment.producer,
            policy=policy,
            amount=amount,
            calculation_method=method,
            status="calculated",
        )
        payouts.append(payout)

    return payouts


def calculate_commissions_for_active_policies() -> dict:
    """
    Batch-calculate commissions for all active policies that don't yet have payouts.
    Returns summary dict with counts.
    """
    from policies.models import Policy

    policies = Policy.objects.filter(status="active").prefetch_related("producers")
    created = 0
    skipped = 0

    for policy in policies:
        payouts = calculate_commissions_for_policy(policy)
        if payouts:
            created += len(payouts)
        else:
            skipped += 1

    return {"created": created, "skipped": skipped}


def approve_payout(payout: CommissionPayout) -> CommissionPayout:
    """Mark a commission payout as approved."""
    if payout.status != "calculated":
        raise ValueError(
            f"Payout {payout.id} is not in 'calculated' state (current: {payout.status})"
        )
    payout.status = "approved"
    payout.save(update_fields=["status", "updated_at"])
    return payout


def mark_payout_paid(
    payout: CommissionPayout, stripe_transfer_id: str = ""
) -> CommissionPayout:
    """Mark a commission payout as paid."""
    if payout.status != "approved":
        raise ValueError(
            f"Payout {payout.id} must be approved before marking paid (current: {payout.status})"
        )
    payout.status = "paid"
    payout.paid_at = timezone.now()
    payout.stripe_transfer_id = stripe_transfer_id or ""
    payout.save(update_fields=["status", "paid_at", "stripe_transfer_id", "updated_at"])
    return payout
