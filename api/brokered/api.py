"""
Brokered coverage webhook endpoints.

Receives callbacks from the Skyvern automation platform for
Workers' Compensation quotes. These endpoints are unauthenticated
(called by external services) and must validate payloads internally.

Flow:
    1. Customer selects Workers' Comp → Django triggers Skyvern workflow.
    2. Skyvern automates the Pie Insurance portal.
    3. Skyvern POSTs results back to these callback endpoints.
    4. Django creates CustomProduct + UnderwriterOverride if quoted.
"""

from typing import Any

from django.conf import settings
from django.http import HttpRequest
from ninja import Router
from ninja.security import APIKeyHeader

from brokered.schemas import WorkersCompWebhookSchema, SkyvernRunWebhookSchema
from brokered.service import BrokeredService
from common.schemas import ApiResponseSchema

router = Router(tags=["Brokered"])


class WebhookSecret(APIKeyHeader):
    """Ninja auth backend that validates X-Webhook-Secret before Ninja
    runs request-schema validation. Without this, tests POSTing invalid
    bodies get 422 (schema error) instead of 401 (auth failure), and
    genuinely unauthorized callers leak schema shape info."""

    param_name = "X-Webhook-Secret"

    def authenticate(self, request: HttpRequest, key: str | None):
        expected = settings.SKYVERN_WEBHOOK_SECRET
        if not expected:
            # No secret configured (dev mode) — allow everything through.
            return "dev"
        if key and key == expected:
            return "webhook"
        return None


_webhook_auth = WebhookSecret()


@router.post(
    "/{quote_number}/workers-compensation/callback",
    response={200: ApiResponseSchema, 404: ApiResponseSchema},
    auth=_webhook_auth,
)
def workers_compensation_callback(
    request: HttpRequest, quote_number: str, data: WorkersCompWebhookSchema
) -> tuple[int, dict[str, Any]]:
    """Receive Skyvern callback with Workers' Comp quote result.

    Called by the Skyvern workflow after completing (or failing) the
    Pie Insurance portal automation. If the status is ``quoted``, creates
    a ``CustomProduct`` with the premium amount.

    Args:
        request: HTTP request. Auth handled by WebhookSecret (401 on miss).
        quote_number: Quote number this callback pertains to.
        data: Callback payload with status, premium, and optional decline reason.

    Returns:
        200 on success, 404 if quote or brokered request not found.
    """
    return BrokeredService.workers_compensation_callback(
        quote_number=quote_number, data=data
    )


@router.post(
    "/workers-compensation/run-status",
    response={200: ApiResponseSchema, 404: ApiResponseSchema},
    auth=_webhook_auth,
)
def workers_compensation_run_status(
    request: HttpRequest, data: SkyvernRunWebhookSchema
) -> tuple[int, dict[str, Any]]:
    """Receive Skyvern run status updates for Workers' Comp automation.

    Handles workflow lifecycle events (failed, cancelled, timed_out,
    terminated, completed). If the run ends without a callback having
    already set a terminal status, marks the request as failed.

    Args:
        request: HTTP request. Auth handled by WebhookSecret (401 on miss).
        data: Run status payload with workflow_run_id and status.

    Returns:
        200 on success, 404 if brokered request not found.
    """
    return BrokeredService.workers_compensation_run_status(data=data)
