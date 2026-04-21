"""
SLA tracking models for the Corgi Insurance platform.

Tracks response time SLAs for quotes, claims, and support interactions.
"""

from django.db import models

from common.models import TimestampedModel


class SLAMetric(TimestampedModel):
    """
    Tracks SLA compliance for operational entities.
    Hook into quote creation (start SLA) and quote response (complete SLA).
    """

    METRIC_TYPE_CHOICES = [
        ("quote_turnaround", "Quote Turnaround"),
        ("claim_acknowledgment", "Claim Acknowledgment"),
        ("support_response", "Support Response"),
    ]

    # Default SLA targets in hours
    DEFAULT_TARGET_HOURS = {
        "quote_turnaround": 24,
        "claim_acknowledgment": 4,
        "support_response": 8,
    }

    metric_type = models.CharField(
        max_length=30,
        choices=METRIC_TYPE_CHOICES,
        db_index=True,
        verbose_name="Metric Type",
    )
    target_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        verbose_name="Target Hours",
        help_text="SLA target in hours (e.g. 24.0 for 1 business day)",
    )
    # Generic FK pattern — store entity type and ID without a hard FK
    entity_type = models.CharField(
        max_length=50,
        verbose_name="Entity Type",
        help_text="Model type, e.g. 'quote', 'claim', 'support_ticket'",
    )
    entity_id = models.IntegerField(
        db_index=True,
        verbose_name="Entity ID",
        help_text="Primary key of the related entity",
    )
    started_at = models.DateTimeField(
        verbose_name="Started At",
        help_text="When the SLA clock started",
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Completed At",
        help_text="When the SLA was satisfied (null = still open)",
    )
    breached = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name="Breached",
        help_text="True if the SLA target was missed",
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Notes",
    )

    class Meta:
        db_table = "sla_metrics"
        verbose_name = "SLA Metric"
        verbose_name_plural = "SLA Metrics"
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["metric_type", "breached"]),
        ]

    def __str__(self):
        status = (
            "BREACHED" if self.breached else ("open" if not self.completed_at else "ok")
        )
        return f"{self.get_metric_type_display()} [{self.entity_type}#{self.entity_id}] — {status}"

    @property
    def elapsed_hours(self):
        """Hours elapsed since SLA started (or until completion if done)."""
        from decimal import Decimal
        from django.utils import timezone

        end = self.completed_at or timezone.now()
        delta = end - self.started_at
        return Decimal(str(round(delta.total_seconds() / 3600, 2)))

    def check_and_update_breach(self) -> bool:
        """
        Check if this SLA has been breached and update the field.
        Returns True if breached.
        """
        from django.utils import timezone

        if self.completed_at:
            elapsed = (self.completed_at - self.started_at).total_seconds() / 3600
        else:
            elapsed = (timezone.now() - self.started_at).total_seconds() / 3600

        breached = elapsed > float(self.target_hours)
        if breached != self.breached:
            self.breached = breached
            self.save(update_fields=["breached", "updated_at"])
        return breached
