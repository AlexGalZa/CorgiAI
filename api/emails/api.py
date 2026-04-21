"""
Emails API (H20).

Exposes the inbound-email webhook endpoint used by our email provider
(see ``emails.inbound`` for the provider-selection notes).

Endpoints:
    POST /api/v1/emails/inbound-webhook — Resend / inbound-parse receiver
"""

from __future__ import annotations

import hmac
import logging
import os
from typing import Any, Optional

from ninja import Router, Schema
from ninja.security import HttpBearer

from emails.inbound import handle_inbound_email, parse_inbound_payload

logger = logging.getLogger("corgi.emails.api")


# ─── Auth ────────────────────────────────────────────────────────────────────


class InboundWebhookAuth(HttpBearer):
    """Bearer-token auth against the ``INBOUND_EMAIL_WEBHOOK_SECRET`` env var.

    Keeping this tiny / self-contained avoids coupling the webhook to the
    external_api ApiKeyAuth (which assumes a DB-backed ``cg_live_...`` key).
    The secret is rotated via the env var; invalid tokens 401.
    """

    def authenticate(self, request, token: str) -> Optional[str]:
        expected = os.getenv("INBOUND_EMAIL_WEBHOOK_SECRET", "")
        if not expected:
            logger.warning(
                "InboundWebhookAuth: INBOUND_EMAIL_WEBHOOK_SECRET is not set; denying all inbound requests."
            )
            return None
        if not token:
            return None
        # Constant-time compare to avoid timing side channels.
        if hmac.compare_digest(token, expected):
            return token
        return None


router = Router(tags=["Emails"])


# ─── Schemas ─────────────────────────────────────────────────────────────────


class InboundWebhookResponse(Schema):
    success: bool
    message: str
    context_id: Optional[int] = None


# ─── Endpoint ────────────────────────────────────────────────────────────────


@router.post(
    "/inbound-webhook",
    auth=InboundWebhookAuth(),
    response=InboundWebhookResponse,
    summary="Inbound email webhook (Resend / provider)",
)
def inbound_webhook(request) -> InboundWebhookResponse:
    """Receive an inbound email event, upsert its EmailContext, notify sales.

    Auth: ``Authorization: Bearer <INBOUND_EMAIL_WEBHOOK_SECRET>``.

    The endpoint always returns 200 once the token validates so the
    provider doesn't retry forever on a transient handler error —
    processing errors are logged and reported in the body.
    """
    # Ninja hands us the parsed request; pull JSON manually so we accept
    # any provider payload shape (see ``parse_inbound_payload``).
    try:
        body: dict[str, Any] = request.json() if hasattr(request, "json") else {}
    except Exception:
        # Fallback for Django's HttpRequest
        import json

        try:
            body = json.loads(request.body or b"{}")
        except Exception:
            body = {}

    payload = parse_inbound_payload(body or {})
    if not payload.thread_id:
        logger.warning("inbound_webhook: rejecting payload without thread_id")
        return InboundWebhookResponse(
            success=False,
            message="Missing thread_id in payload.",
        )

    try:
        context_id = handle_inbound_email(payload)
    except Exception:
        logger.exception(
            "inbound_webhook: handler failed for thread %s", payload.thread_id
        )
        return InboundWebhookResponse(
            success=False,
            message="Handler error; event logged.",
        )

    return InboundWebhookResponse(
        success=True,
        message="Inbound email processed.",
        context_id=context_id,
    )
