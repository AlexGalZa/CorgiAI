"""
Webhook Subscriptions API (V3 #38)

Partner-facing endpoints for Zapier/Make/n8n webhook subscriptions.
Requires API key auth (same as external_api).

Endpoints:
    POST   /api/v1/webhooks/subscribe         — Register a new endpoint
    GET    /api/v1/webhooks/subscriptions     — List your subscriptions
    DELETE /api/v1/webhooks/subscriptions/:id — Delete (unsubscribe)
"""

import secrets
import logging
from typing import Optional

from ninja import Router, Schema
from pydantic import Field, field_validator

from external_api.auth import ApiKeyAuth
from webhooks.delivery import WebhookEndpoint, SUPPORTED_EVENTS

logger = logging.getLogger("corgi.webhooks.api")

router = Router(auth=ApiKeyAuth(), tags=["Webhooks"])


# ─── Schemas ─────────────────────────────────────────────────────────────────


class WebhookSubscribeInput(Schema):
    url: str = Field(
        description="HTTPS URL that will receive POST requests for subscribed events",
        example="https://hooks.zapier.com/hooks/catch/12345/abcde/",
    )
    events: list[str] = Field(
        description=(
            "List of events to subscribe to. "
            "Supported: quote.created, policy.bound, claim.filed, "
            "payment.failed, policy.cancelled"
        ),
        example=["quote.created", "policy.bound"],
    )
    description: Optional[str] = Field(
        default="",
        description="Optional human-readable description for this subscription",
    )

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith("https://") and not v.startswith("http://"):
            raise ValueError("URL must start with https:// or http://")
        return v

    @field_validator("events")
    @classmethod
    def validate_events(cls, v: list[str]) -> list[str]:
        # Allow all supported events; ignore unknowns with a warning
        valid = [e for e in v if e in SUPPORTED_EVENTS]
        if not valid:
            raise ValueError(
                f"No valid events provided. Supported events: {', '.join(SUPPORTED_EVENTS)}"
            )
        return valid


class WebhookSubscriptionSchema(Schema):
    id: int
    url: str
    events: list[str]
    description: str
    is_active: bool
    created_at: str


class WebhookSubscribeData(Schema):
    id: int
    url: str
    events: list[str]
    description: str
    secret: str  # shown only on creation
    is_active: bool
    created_at: str


class WebhookSubscribeResponse(Schema):
    success: bool
    message: str
    data: Optional[WebhookSubscribeData] = None


class WebhookSubscriptionListResponse(Schema):
    success: bool
    message: str
    data: list[WebhookSubscriptionSchema] = []


class WebhookDeleteResponse(Schema):
    success: bool
    message: str


# ─── Endpoints ───────────────────────────────────────────────────────────────


@router.post(
    "/subscribe",
    response=WebhookSubscribeResponse,
    summary="Register a webhook endpoint",
)
def subscribe(request, payload: WebhookSubscribeInput):
    """
    Register a new webhook endpoint to receive Corgi events.

    A signing secret is generated automatically and returned **once** — store it securely.
    Incoming requests from Corgi will include an `X-Corgi-Signature-256` header
    containing `sha256=<HMAC-SHA256 signature>` computed with your secret.

    **Supported events:**
    - `quote.created` — A new quote was created
    - `policy.bound` — A policy was bound / purchased
    - `claim.filed` — A new claim was filed
    - `payment.failed` — A payment failed
    - `policy.cancelled` — A policy was cancelled
    """
    api_key = request.auth
    org = getattr(api_key, "organization", None)

    secret = secrets.token_hex(32)  # 64-char hex secret

    endpoint = WebhookEndpoint.objects.create(
        url=payload.url,
        secret=secret,
        subscribed_events=payload.events,
        description=payload.description or "",
        is_active=True,
        org=org,
    )

    logger.info(
        "Webhook endpoint %s registered by org %s for events: %s",
        endpoint.id,
        org,
        payload.events,
    )

    return WebhookSubscribeResponse(
        success=True,
        message="Webhook endpoint registered. Store your secret — it will not be shown again.",
        data=WebhookSubscribeData(
            id=endpoint.id,
            url=endpoint.url,
            events=endpoint.subscribed_events,
            description=endpoint.description,
            secret=secret,
            is_active=endpoint.is_active,
            created_at=endpoint.created_at.isoformat(),
        ),
    )


@router.get(
    "/subscriptions",
    response=WebhookSubscriptionListResponse,
    summary="List webhook subscriptions",
)
def list_subscriptions(request):
    """
    List all active webhook subscriptions for your organization.
    """
    api_key = request.auth
    org = getattr(api_key, "organization", None)

    qs = WebhookEndpoint.objects.filter(is_active=True)
    if org is not None:
        qs = qs.filter(org=org)

    data = [
        WebhookSubscriptionSchema(
            id=ep.id,
            url=ep.url,
            events=ep.subscribed_events or [],
            description=ep.description,
            is_active=ep.is_active,
            created_at=ep.created_at.isoformat(),
        )
        for ep in qs.order_by("-created_at")
    ]

    return WebhookSubscriptionListResponse(
        success=True,
        message=f"{len(data)} subscription(s) found.",
        data=data,
    )


@router.delete(
    "/subscriptions/{endpoint_id}",
    response=WebhookDeleteResponse,
    summary="Unsubscribe a webhook endpoint",
)
def unsubscribe(request, endpoint_id: int):
    """
    Unsubscribe (deactivate) a webhook endpoint.

    The endpoint record is retained for audit purposes but will no longer receive events.
    """
    api_key = request.auth
    org = getattr(api_key, "organization", None)

    qs = WebhookEndpoint.objects.filter(id=endpoint_id, is_active=True)
    if org is not None:
        qs = qs.filter(org=org)

    endpoint = qs.first()
    if endpoint is None:
        return WebhookDeleteResponse(
            success=False,
            message="Subscription not found or already deactivated.",
        )

    endpoint.is_active = False
    endpoint.save(update_fields=["is_active"])

    logger.info("Webhook endpoint %s deactivated by org %s", endpoint_id, org)

    return WebhookDeleteResponse(
        success=True,
        message="Webhook subscription deactivated.",
    )
