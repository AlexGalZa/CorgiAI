"""
Webhook delivery system for Corgi platform.

Handles outbound webhooks to partner/customer endpoints:
- WebhookEndpoint: registered endpoints with secrets and event subscriptions
- WebhookDelivery: delivery tracking with retry logic
- Service: HMAC signing, retries with exponential backoff
"""

import hashlib
import hmac
import json
import logging
import time
from datetime import timedelta

import requests
from django.db import models
from django.utils import timezone

from common.models import TimestampedModel

logger = logging.getLogger("corgi.webhooks.delivery")

# ─── Event type constants ────────────────────────────────────────────────────

WEBHOOK_EVENT_QUOTE_CREATED = "quote.created"
WEBHOOK_EVENT_POLICY_BOUND = "policy.bound"
WEBHOOK_EVENT_CLAIM_FILED = "claim.filed"
WEBHOOK_EVENT_PAYMENT_FAILED = "payment.failed"
WEBHOOK_EVENT_POLICY_CANCELLED = "policy.cancelled"
WEBHOOK_EVENT_POLICY_RENEWED = "policy.renewed"

SUPPORTED_EVENTS = [
    WEBHOOK_EVENT_QUOTE_CREATED,
    WEBHOOK_EVENT_POLICY_BOUND,
    WEBHOOK_EVENT_CLAIM_FILED,
    WEBHOOK_EVENT_PAYMENT_FAILED,
    WEBHOOK_EVENT_POLICY_CANCELLED,
    WEBHOOK_EVENT_POLICY_RENEWED,
]

EVENT_CHOICES = [(e, e) for e in SUPPORTED_EVENTS]


# ─── Models ──────────────────────────────────────────────────────────────────


class WebhookEndpoint(TimestampedModel):
    """
    A registered webhook endpoint.

    Partners register a URL + secret to receive events.
    The secret is used for HMAC-SHA256 request signing.
    """

    url = models.URLField(
        max_length=500,
        verbose_name="Endpoint URL",
        help_text="HTTPS URL that will receive POST requests",
    )
    secret = models.CharField(
        max_length=255,
        verbose_name="Signing Secret",
        help_text="Secret used to sign HMAC-SHA256 payload signatures",
    )
    subscribed_events = models.JSONField(
        default=list,
        verbose_name="Subscribed Events",
        help_text="List of event types this endpoint subscribes to",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Active",
        help_text="Inactive endpoints receive no deliveries",
    )
    description = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Description",
    )
    # Optional org scoping
    org = models.ForeignKey(
        "organizations.Organization",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="webhook_endpoints",
        verbose_name="Organization",
    )

    class Meta:
        verbose_name = "Webhook Endpoint"
        verbose_name_plural = "Webhook Endpoints"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.url} ({'active' if self.is_active else 'inactive'})"

    def subscribes_to(self, event_type: str) -> bool:
        """Return True if this endpoint is subscribed to the given event."""
        return event_type in (self.subscribed_events or [])


class WebhookDelivery(TimestampedModel):
    """
    A single webhook delivery attempt record.

    Tracks state, attempts, and response metadata for each outbound event.
    """

    STATUS_PENDING = "pending"
    STATUS_DELIVERED = "delivered"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_DELIVERED, "Delivered"),
        (STATUS_FAILED, "Failed"),
    ]

    endpoint = models.ForeignKey(
        WebhookEndpoint,
        on_delete=models.CASCADE,
        related_name="deliveries",
        verbose_name="Endpoint",
    )
    event_type = models.CharField(
        max_length=100,
        verbose_name="Event Type",
        choices=EVENT_CHOICES,
    )
    payload = models.JSONField(
        verbose_name="Payload",
        help_text="JSON payload sent to the endpoint",
    )
    status = models.CharField(
        max_length=20,
        default=STATUS_PENDING,
        choices=STATUS_CHOICES,
        verbose_name="Status",
        db_index=True,
    )
    attempts = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="Attempts",
    )
    last_attempt_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Last Attempt At",
    )
    response_status = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="HTTP Response Status",
        help_text="HTTP status code from last delivery attempt",
    )
    response_body = models.TextField(
        blank=True,
        default="",
        verbose_name="Response Body",
        help_text="Truncated response body from last attempt",
    )
    error_message = models.TextField(
        blank=True,
        default="",
        verbose_name="Error Message",
        help_text="Error detail from last failed attempt",
    )

    class Meta:
        verbose_name = "Webhook Delivery"
        verbose_name_plural = "Webhook Deliveries"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["endpoint", "event_type"]),
        ]

    def __str__(self):
        return f"{self.event_type} → {self.endpoint.url} [{self.status}]"


# ─── Service ─────────────────────────────────────────────────────────────────


class WebhookDeliveryService:
    """
    Core webhook delivery service.

    Handles:
    - Queuing deliveries for active endpoints subscribed to an event
    - Signing payloads with HMAC-SHA256
    - Delivering with 3 retry attempts and exponential backoff
    """

    MAX_ATTEMPTS = 3
    REQUEST_TIMEOUT = 15  # seconds
    BACKOFF_BASE = 2  # seconds; attempt n waits BASE^n seconds

    @classmethod
    def queue_event(cls, event_type: str, payload: dict, org=None) -> list:
        """
        Queue a webhook delivery for all active endpoints subscribed to event_type.

        Args:
            event_type: One of SUPPORTED_EVENTS
            payload: Dict to send as JSON body
            org: Optional org to restrict endpoint lookup

        Returns:
            List of created WebhookDelivery objects
        """
        if event_type not in SUPPORTED_EVENTS:
            logger.warning("Unknown webhook event type: %s", event_type)
            return []

        endpoints_qs = WebhookEndpoint.objects.filter(is_active=True)
        if org is not None:
            endpoints_qs = endpoints_qs.filter(org=org)

        deliveries = []
        for endpoint in endpoints_qs:
            if not endpoint.subscribes_to(event_type):
                continue

            delivery = WebhookDelivery.objects.create(
                endpoint=endpoint,
                event_type=event_type,
                payload=payload,
                status=WebhookDelivery.STATUS_PENDING,
            )
            deliveries.append(delivery)
            logger.info(
                "Queued webhook delivery %s: %s → %s",
                delivery.id,
                event_type,
                endpoint.url,
            )

        return deliveries

    @classmethod
    def deliver(cls, delivery: WebhookDelivery) -> bool:
        """
        Attempt to deliver a single webhook with retry logic.

        Tries up to MAX_ATTEMPTS times with exponential backoff.
        Updates delivery status on the model.

        Returns:
            True if delivered successfully, False otherwise
        """
        for attempt in range(1, cls.MAX_ATTEMPTS + 1):
            delivery.attempts = attempt
            delivery.last_attempt_at = timezone.now()

            try:
                success = cls._send_request(delivery)
                if success:
                    delivery.status = WebhookDelivery.STATUS_DELIVERED
                    delivery.save(
                        update_fields=[
                            "status",
                            "attempts",
                            "last_attempt_at",
                            "response_status",
                            "response_body",
                            "error_message",
                        ]
                    )
                    logger.info(
                        "Webhook delivery %s succeeded on attempt %d",
                        delivery.id,
                        attempt,
                    )
                    return True
                else:
                    logger.warning(
                        "Webhook delivery %s attempt %d failed (HTTP %s)",
                        delivery.id,
                        attempt,
                        delivery.response_status,
                    )
            except Exception as exc:
                delivery.error_message = str(exc)[:1000]
                logger.warning(
                    "Webhook delivery %s attempt %d raised exception: %s",
                    delivery.id,
                    attempt,
                    exc,
                )

            # Save progress after each failed attempt
            delivery.save(
                update_fields=[
                    "attempts",
                    "last_attempt_at",
                    "response_status",
                    "response_body",
                    "error_message",
                ]
            )

            if attempt < cls.MAX_ATTEMPTS:
                backoff = cls.BACKOFF_BASE**attempt
                logger.debug(
                    "Webhook delivery %s backing off %ss before attempt %d",
                    delivery.id,
                    backoff,
                    attempt + 1,
                )
                time.sleep(backoff)

        # All attempts exhausted
        delivery.status = WebhookDelivery.STATUS_FAILED
        delivery.save(update_fields=["status"])
        logger.error(
            "Webhook delivery %s failed after %d attempts",
            delivery.id,
            cls.MAX_ATTEMPTS,
        )
        return False

    @classmethod
    def deliver_event(cls, event_type: str, payload: dict, org=None) -> list:
        """
        Queue and immediately deliver an event synchronously.

        Returns list of (delivery, success) tuples.
        """
        deliveries = cls.queue_event(event_type, payload, org=org)
        results = []
        for delivery in deliveries:
            success = cls.deliver(delivery)
            results.append((delivery, success))
        return results

    @classmethod
    def retry_failed(cls, older_than_minutes: int = 0) -> int:
        """
        Retry all failed deliveries. Returns count of retried deliveries.

        Args:
            older_than_minutes: Only retry deliveries failed more than N minutes ago
        """
        qs = WebhookDelivery.objects.filter(status=WebhookDelivery.STATUS_FAILED)
        if older_than_minutes > 0:
            cutoff = timezone.now() - timedelta(minutes=older_than_minutes)
            qs = qs.filter(last_attempt_at__lte=cutoff)

        count = 0
        for delivery in qs:
            # Reset to pending before retrying
            delivery.status = WebhookDelivery.STATUS_PENDING
            delivery.attempts = 0
            delivery.save(update_fields=["status", "attempts"])
            cls.deliver(delivery)
            count += 1

        return count

    @classmethod
    def _send_request(cls, delivery: WebhookDelivery) -> bool:
        """
        Execute the HTTP POST to the endpoint.

        Signs the payload with HMAC-SHA256 and sends it.
        Updates delivery.response_status and delivery.response_body.

        Returns:
            True if the endpoint responded with 2xx status
        """
        payload_bytes = json.dumps(delivery.payload, separators=(",", ":")).encode(
            "utf-8"
        )
        signature = cls._sign_payload(delivery.endpoint.secret, payload_bytes)

        headers = {
            "Content-Type": "application/json",
            "X-Corgi-Event": delivery.event_type,
            "X-Corgi-Delivery": str(delivery.id),
            "X-Corgi-Signature-256": f"sha256={signature}",
            "User-Agent": "Corgi-Webhooks/1.0",
        }

        response = requests.post(
            delivery.endpoint.url,
            data=payload_bytes,
            headers=headers,
            timeout=cls.REQUEST_TIMEOUT,
        )

        delivery.response_status = response.status_code
        delivery.response_body = response.text[:2000]
        delivery.error_message = ""

        return 200 <= response.status_code < 300

    @staticmethod
    def _sign_payload(secret: str, payload_bytes: bytes) -> str:
        """Generate HMAC-SHA256 signature for the payload."""
        return hmac.new(
            secret.encode("utf-8"),
            payload_bytes,
            hashlib.sha256,
        ).hexdigest()  # type: ignore[attr-defined]
