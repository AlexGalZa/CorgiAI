"""
HubSpot sync persistence models.

- ``HubSpotSyncLog``: immutable audit log of every sync attempt.
- ``HubSpotSyncFailure``: dead-letter queue for webhook events whose
  Django-side processing raised. Rows are picked up by an out-of-band
  retry worker; ``retry_count`` is incremented on every replay attempt.
"""

from django.db import models

from common.models import TimestampedModel


class HubSpotSyncLog(TimestampedModel):
    """Immutable audit log of every HubSpot sync attempt (push or pull)."""

    DIRECTION_CHOICES = [
        ("push", "Django → HubSpot"),
        ("pull", "HubSpot → Django"),
    ]

    OBJECT_TYPE_CHOICES = [
        ("contact", "Contact"),
        ("company", "Company"),
        ("deal", "Deal"),
    ]

    direction = models.CharField(
        max_length=4,
        choices=DIRECTION_CHOICES,
        verbose_name="Direction",
    )
    object_type = models.CharField(
        max_length=10,
        choices=OBJECT_TYPE_CHOICES,
        verbose_name="HubSpot Object Type",
    )
    hubspot_id = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name="HubSpot Object ID",
    )
    django_model = models.CharField(
        max_length=50,
        verbose_name="Django Model",
        help_text="e.g. 'Policy', 'User', 'Organization'",
    )
    django_id = models.IntegerField(
        verbose_name="Django Object ID",
    )
    action = models.CharField(
        max_length=20,
        verbose_name="Action",
        help_text="e.g. 'create', 'update', 'associate', 'webhook'",
    )
    success = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name="Success",
    )
    error_message = models.TextField(
        blank=True,
        default="",
        verbose_name="Error Message",
    )
    payload_summary = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Payload Summary",
        help_text="Key properties sent or received (for debugging)",
    )

    class Meta:
        db_table = "hubspot_sync_log"
        verbose_name = "HubSpot Sync Log"
        verbose_name_plural = "HubSpot Sync Logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["object_type", "-created_at"]),
            models.Index(fields=["django_model", "django_id"]),
            models.Index(fields=["success", "-created_at"]),
        ]

    def __str__(self):
        status = "✓" if self.success else "✗"
        return f"{status} {self.direction} {self.object_type} {self.django_model}#{self.django_id}"


class HubSpotSyncFailure(models.Model):
    """Dead-letter entry for a webhook event we failed to process.

    A background worker (see ``hubspot_sync/tasks.py``) re-runs entries
    whose ``resolved_at`` is null, incrementing ``retry_count`` each time
    and capping retries in the worker (not here) to keep this table a
    pure data store.
    """

    event_type = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name="Event Type",
        help_text="HubSpot subscriptionType, e.g. 'deal.propertyChange'",
    )
    entity_id = models.CharField(
        max_length=64,
        db_index=True,
        verbose_name="HubSpot Entity ID",
        help_text="objectId from the HubSpot event payload",
    )
    payload = models.JSONField(
        verbose_name="Raw Event Payload",
        help_text="Full event dict as received from HubSpot",
    )
    error = models.TextField(
        verbose_name="Error",
        help_text="Exception repr captured when the event failed",
    )
    retry_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Retry Count",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name="Created At",
    )
    last_retried_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Last Retried At",
    )
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Resolved At",
        help_text="Set when a retry finally succeeds",
    )

    class Meta:
        db_table = "hubspot_sync_failure"
        verbose_name = "HubSpot Sync Failure"
        verbose_name_plural = "HubSpot Sync Failures"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["event_type", "-created_at"]),
            models.Index(fields=["resolved_at", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.event_type} {self.entity_id} (retries={self.retry_count})"
