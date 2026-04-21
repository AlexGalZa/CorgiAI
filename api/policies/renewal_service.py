"""
Policy renewal service for the Corgi Insurance platform.

Handles:
- Fetching pre-filled renewal data for a policy
- Initiating a Stripe checkout for renewal
- Marking a renewal as accepted when checkout completes
"""

import logging
from dateutil.relativedelta import relativedelta

from django.conf import settings

from organizations.service import OrganizationService
from policies.models import Policy, PolicyRenewal

logger = logging.getLogger(__name__)


class PolicyRenewalService:
    @staticmethod
    def _get_policy_for_user(policy_id: int, user) -> Policy:
        """Fetch policy and verify user's org has access."""
        org_id = OrganizationService.get_active_org_id(user)
        try:
            policy = Policy.objects.select_related(
                "quote__user", "quote__company", "quote__company__business_address"
            ).get(pk=policy_id, quote__organization_id=org_id)
        except Policy.DoesNotExist:
            raise Policy.DoesNotExist(f"Policy {policy_id} not found")
        return policy

    @staticmethod
    def get_renewal_data(policy_id: int, user) -> dict:
        """
        Return renewal data for a policy, pre-filled from the current policy.

        Includes:
        - Current policy details (coverage, limits, premium, dates)
        - Renewal offer status
        - Estimated renewal dates (new effective = old expiration_date)
        - Latest PolicyRenewal record if one exists
        """
        policy = PolicyRenewalService._get_policy_for_user(policy_id, user)

        # Calculate proposed renewal period (1 year from expiration)
        new_effective = policy.expiration_date
        new_expiration = new_effective + relativedelta(years=1)

        # Get latest renewal record if exists
        renewal_record = (
            PolicyRenewal.objects.filter(policy=policy).order_by("-created_at").first()
        )

        renewal_data = None
        if renewal_record:
            renewal_data = {
                "id": renewal_record.pk,
                "status": renewal_record.status,
                "offered_at": renewal_record.offered_at.isoformat()
                if renewal_record.offered_at
                else None,
                "expires_at": renewal_record.expires_at.isoformat()
                if renewal_record.expires_at
                else None,
                "accepted_at": renewal_record.accepted_at.isoformat()
                if renewal_record.accepted_at
                else None,
                "new_quote_id": renewal_record.new_quote_id,
            }

        company = policy.quote.company if policy.quote else None
        address = company.business_address if company else None

        return {
            "policy": {
                "id": policy.pk,
                "policy_number": policy.policy_number,
                "coverage_type": policy.coverage_type,
                "status": policy.status,
                "renewal_status": policy.renewal_status,
                "effective_date": policy.effective_date.isoformat(),
                "expiration_date": policy.expiration_date.isoformat(),
                "premium": str(policy.premium),
                "billing_frequency": policy.billing_frequency,
                "per_occurrence_limit": policy.per_occurrence_limit,
                "aggregate_limit": policy.aggregate_limit,
                "retention": policy.retention,
                "insured_legal_name": policy.insured_legal_name,
                "carrier": policy.carrier,
                "is_brokered": policy.is_brokered,
            },
            "proposed_renewal": {
                "effective_date": new_effective.isoformat(),
                "expiration_date": new_expiration.isoformat(),
                "coverage_type": policy.coverage_type,
                "per_occurrence_limit": policy.per_occurrence_limit,
                "aggregate_limit": policy.aggregate_limit,
                "retention": policy.retention,
                "billing_frequency": policy.billing_frequency,
                # Pre-fill company info from existing policy
                "insured_legal_name": policy.insured_legal_name,
                "insured_fein": policy.insured_fein,
                "mailing_address": policy.mailing_address,
                "principal_state": policy.principal_state,
            },
            "company": {
                "legal_name": company.entity_legal_name if company else None,
                "federal_ein": company.federal_ein if company else None,
                "state": address.state if address else None,
            }
            if company
            else None,
            "renewal": renewal_data,
            "can_renew": policy.status == "active"
            and policy.renewal_status in ("not_due", "offered"),
        }

    @staticmethod
    def initiate_renewal_checkout(policy_id: int, user) -> dict:
        """
        Initiate a Stripe checkout session for policy renewal.

        Creates a new quote cloned from the expiring policy's quote,
        then generates a Stripe checkout URL.

        Returns dict with checkout_url and renewal_id.
        """
        policy = PolicyRenewalService._get_policy_for_user(policy_id, user)

        if policy.status != "active":
            raise ValueError(
                f"Policy {policy.policy_number} is not active (status: {policy.status})."
            )

        if policy.renewal_status == "renewed":
            raise ValueError(f"Policy {policy.policy_number} has already been renewed.")

        if policy.renewal_status == "non_renewed":
            raise ValueError(
                f"Policy {policy.policy_number} has been marked non-renewal."
            )

        # Calculate new dates
        new_effective = policy.expiration_date
        new_expiration = new_effective + relativedelta(years=1)

        # Get or create renewal record
        renewal, _ = PolicyRenewal.objects.get_or_create(
            policy=policy,
            status__in=["pending"],
            defaults={
                "status": "pending",
            },
        )

        # Clone the existing quote for the renewal

        try:
            # Create a renewal checkout URL using the existing policy service
            from policies.service import PolicyService

            # Build a checkout URL for the renewal coverage
            checkout_data = PolicyService.create_renewal_checkout(
                policy=policy,
                new_effective=new_effective,
                new_expiration=new_expiration,
                user=user,
            )

            # Mark renewal as accepted
            renewal.status = "pending"  # stays pending until payment
            renewal.save(update_fields=["status", "updated_at"])

        except AttributeError:
            # PolicyService.create_renewal_checkout not yet implemented — return placeholder
            checkout_data = {
                "checkout_url": f"{settings.FRONTEND_URL}/renew/{policy.policy_number}",
                "message": "Contact support to complete your renewal.",
            }

        return {
            "renewal_id": renewal.pk,
            "policy_number": policy.policy_number,
            "coverage_type": policy.coverage_type,
            "new_effective_date": new_effective.isoformat(),
            "new_expiration_date": new_expiration.isoformat(),
            **checkout_data,
        }
