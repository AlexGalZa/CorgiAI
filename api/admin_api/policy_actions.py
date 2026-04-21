"""
Policy action endpoints for the Admin API.

Provides endorse, cancel, and reactivate operations on policies.
"""

from decimal import Decimal
from typing import Any

from django.http import HttpRequest

from admin_api.helpers import OPERATIONS_ROLES, _require_role
from admin_api.schemas import (
    CancelRequest,
    CancelResponse,
    EndorseRequest,
    EndorseResponse,
    ReactivateRequest,
    ReactivateResponse,
)
from common.schemas import ApiResponseSchema
from users.auth import JWTAuth

import logging

logger = logging.getLogger(__name__)


def register_policy_action_routes(router):
    """Register all policy action endpoints on the given router."""

    @router.post(
        "/policies/{policy_id}/endorse",
        auth=JWTAuth(),
        response={
            200: ApiResponseSchema,
            400: ApiResponseSchema,
            404: ApiResponseSchema,
        },
        summary="Perform an endorsement action on a policy",
    )
    def endorse_policy(
        request: HttpRequest, policy_id: int, data: EndorseRequest
    ) -> tuple[int, dict[str, Any]]:
        """Perform a midterm endorsement on an active policy.

        Supported actions: modify_limits, add_coverage, remove_coverage, backdate.
        """
        _require_role(request, OPERATIONS_ROLES, "endorse_policy")

        from policies.models import Policy
        from policies.service import PolicyService

        try:
            policy = Policy.objects.select_related(
                "quote", "quote__company", "quote__company__business_address"
            ).get(pk=policy_id)
        except Policy.DoesNotExist:
            return 404, {"success": False, "message": "Policy not found", "data": None}

        try:
            if data.action == "modify_limits":
                if not data.new_limits or data.new_premium is None:
                    return 400, {
                        "success": False,
                        "message": "new_limits and new_premium required for modify_limits",
                        "data": None,
                    }
                endorsement = PolicyService.endorse_modify_limits(
                    policy, data.new_limits, data.new_premium, data.reason
                )
                result = EndorseResponse(
                    policy_number=policy.policy_number,
                    action=data.action,
                    old_premium=endorsement["old_premium"],
                    new_premium=endorsement["new_premium"],
                    prorated_delta=endorsement["prorated_delta"],
                    message=f"Limits modified. Premium: ${endorsement['old_premium']} → ${endorsement['new_premium']}",
                )

            elif data.action == "add_coverage":
                if not data.new_coverage_type or data.new_premium is None:
                    return 400, {
                        "success": False,
                        "message": "new_coverage_type and new_premium required for add_coverage",
                        "data": None,
                    }
                endorsement = PolicyService.endorse_add_coverage(
                    policy,
                    data.new_coverage_type,
                    data.new_limits or {},
                    data.new_premium,
                    data.reason,
                    is_brokered=data.is_brokered,
                    carrier=data.carrier,
                )
                result = EndorseResponse(
                    policy_number=policy.policy_number,
                    action=data.action,
                    new_premium=endorsement["full_term_premium"],
                    prorated_delta=endorsement["prorated_premium"],
                    message=f"Coverage {data.new_coverage_type} added. Prorated charge: ${endorsement['prorated_premium']}",
                )

            elif data.action == "remove_coverage":
                endorsement = PolicyService.endorse_remove_coverage(policy, data.reason)
                result = EndorseResponse(
                    policy_number=policy.policy_number,
                    action=data.action,
                    old_premium=policy.premium,
                    prorated_delta=-endorsement["refund_amount"],
                    message=f"Coverage removed. Refund: ${endorsement['refund_amount']}",
                )

            elif data.action == "backdate":
                if not data.new_effective_date:
                    return 400, {
                        "success": False,
                        "message": "new_effective_date required for backdate",
                        "data": None,
                    }
                endorsement = PolicyService.endorse_backdate_policy(
                    policy, data.new_effective_date, data.reason
                )
                result = EndorseResponse(
                    policy_number=policy.policy_number,
                    action=data.action,
                    old_premium=endorsement["old_premium"],
                    new_premium=endorsement["new_premium"],
                    prorated_delta=endorsement["premium_delta"],
                    message=f"Effective date backdated from {endorsement['old_effective_date']} to {endorsement['new_effective_date']}",
                )
            else:
                return 400, {
                    "success": False,
                    "message": f"Unknown action: {data.action}",
                    "data": None,
                }

        except ValueError as e:
            return 400, {"success": False, "message": str(e), "data": None}

        return 200, {
            "success": True,
            "message": "Endorsement processed",
            "data": result.dict(),
        }

    @router.post(
        "/policies/{policy_id}/cancel",
        auth=JWTAuth(),
        response={
            200: ApiResponseSchema,
            400: ApiResponseSchema,
            404: ApiResponseSchema,
        },
        summary="Cancel a policy with Stripe refund",
    )
    def cancel_policy(
        request: HttpRequest, policy_id: int, data: CancelRequest
    ) -> tuple[int, dict[str, Any]]:
        """Cancel an active policy with prorated Stripe refund."""
        _require_role(request, OPERATIONS_ROLES, "cancel_policy")

        from policies.models import Policy
        from policies.service import PolicyService

        try:
            policy = Policy.objects.select_related(
                "quote", "quote__company", "quote__company__business_address"
            ).get(pk=policy_id)
        except Policy.DoesNotExist:
            return 404, {"success": False, "message": "Policy not found", "data": None}

        try:
            cancellation = PolicyService.cancel_policy(policy, data.reason)
        except ValueError as e:
            return 400, {"success": False, "message": str(e), "data": None}

        result = CancelResponse(
            policy_number=policy.policy_number,
            refund_amount=cancellation["refund_amount"],
            message=f"Policy cancelled. Refund: ${cancellation['refund_amount']}",
        )
        return 200, {
            "success": True,
            "message": "Policy cancelled",
            "data": result.dict(),
        }

    @router.post(
        "/policies/{policy_id}/reactivate",
        auth=JWTAuth(),
        response={
            200: ApiResponseSchema,
            400: ApiResponseSchema,
            404: ApiResponseSchema,
        },
        summary="Reactivate a cancelled policy",
    )
    def reactivate_policy(
        request: HttpRequest, policy_id: int, data: ReactivateRequest
    ) -> tuple[int, dict[str, Any]]:
        """Reactivate a cancelled monthly policy."""
        _require_role(request, OPERATIONS_ROLES, "reactivate_policy")

        from policies.models import Policy
        from policies.service import PolicyService

        try:
            policy = Policy.objects.select_related(
                "quote", "quote__company", "quote__company__business_address"
            ).get(pk=policy_id)
        except Policy.DoesNotExist:
            return 404, {"success": False, "message": "Policy not found", "data": None}

        # Gather all cancelled policies in the same COI group for batch reactivation
        policies_to_reactivate = list(
            Policy.objects.filter(
                coi_number=policy.coi_number,
                status="cancelled",
                billing_frequency="monthly",
            ).select_related(
                "quote", "quote__company", "quote__company__business_address"
            )
        )

        if not policies_to_reactivate:
            policies_to_reactivate = [policy]

        admin_user = request.auth
        admin_username = getattr(admin_user, "email", "admin")

        try:
            reactivation = PolicyService.reactivate_policy(
                policies_to_reactivate,
                data.reactivation_date,
                admin_username,
            )
        except ValueError as e:
            return 400, {"success": False, "message": str(e), "data": None}

        result = ReactivateResponse(
            policy_numbers=[
                p.policy_number for p in reactivation["reactivated_policies"]
            ],
            subscription_id=reactivation.get("subscription_id"),
            gap_premium=reactivation.get("gap_premium", Decimal("0")),
            message=f"Reactivated {len(reactivation['reactivated_policies'])} policies",
        )
        return 200, {
            "success": True,
            "message": "Policy reactivated",
            "data": result.dict(),
        }
