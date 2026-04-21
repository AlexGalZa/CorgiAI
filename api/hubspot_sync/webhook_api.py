"""
HubSpot inbound webhook endpoint.

Receives event notifications from HubSpot workflow subscriptions.
Validates the request signature (v3) when HUBSPOT_WEBHOOK_SECRET is configured.

Setup in HubSpot:
  1. Go to Settings → Integrations → Private Apps → your app → Webhooks
  2. Subscribe to events: deal.propertyChange, contact.propertyChange, contact.creation
  3. Set the webhook URL to: https://your-api.com/api/v1/hubspot/webhook
  4. Copy the "Client secret" and set it as HUBSPOT_WEBHOOK_SECRET in Django settings
"""

import hashlib
import hmac
import json
import logging

from django.conf import settings
from django.http import HttpRequest
from ninja import Router

logger = logging.getLogger(__name__)

router = Router(tags=["HubSpot Webhooks"])


def _verify_signature(request: HttpRequest) -> bool:
    """Verify HubSpot webhook v3 signature.

    See: https://developers.hubspot.com/docs/api/webhooks#validate-webhook-signatures
    """
    secret = getattr(settings, "HUBSPOT_WEBHOOK_SECRET", "")
    if not secret:
        # No secret configured — skip validation (dev mode)
        return True

    signature_header = request.headers.get("X-HubSpot-Signature-v3", "")
    timestamp = request.headers.get("X-HubSpot-Request-Timestamp", "")

    if not signature_header or not timestamp:
        return False

    # v3 signature: HMAC-SHA256(secret, method + url + body + timestamp)
    body = request.body.decode("utf-8")
    source_string = f"{request.method}{request.build_absolute_uri()}{body}{timestamp}"

    expected = hmac.new(
        secret.encode("utf-8"),
        source_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature_header)


@router.post(
    "/webhook",
    response={200: dict, 401: dict},
    auth=None,  # No JWT — HubSpot authenticates via signature
    summary="Receive HubSpot webhook events",
)
def hubspot_webhook(request: HttpRequest) -> tuple[int, dict]:
    """Process incoming HubSpot webhook events.

    HubSpot sends an array of events. Each event is processed independently.
    We always return 200 to prevent HubSpot from retrying — errors are logged.
    """
    if not _verify_signature(request):
        logger.warning("HubSpot webhook signature verification failed")
        return 401, {"error": "Invalid signature"}

    try:
        events = json.loads(request.body)
    except (json.JSONDecodeError, Exception):
        logger.error("Invalid JSON in HubSpot webhook body")
        return 200, {"processed": 0}  # Still 200 to stop retries

    if not isinstance(events, list):
        events = [events]

    from hubspot_sync.service import HubSpotSyncService

    processed = 0
    for event in events:
        try:
            HubSpotSyncService.process_webhook_event(event)
            processed += 1
        except Exception as e:
            logger.error(
                "Failed to process HubSpot event %s: %s",
                event.get("subscriptionType", "unknown"),
                e,
            )

    logger.info("Processed %d/%d HubSpot webhook events", processed, len(events))
    return 200, {"processed": processed, "total": len(events)}
