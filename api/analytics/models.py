"""
Analytics models for the Corgi Insurance platform.

Models:
- ScheduledReport: Configuration for automated weekly/monthly report emails.
"""

from django.db import models
from common.models import TimestampedModel


class ScheduledReport(TimestampedModel):
    REPORT_TYPE_CHOICES = [
        ("earned_premium", "Earned Premium Report"),
        ("pipeline", "Pipeline Report"),
        ("loss_ratio", "Loss Ratio Report"),
        ("broker_performance", "Broker Performance Report"),
        ("claims_summary", "Claims Summary Report"),
    ]

    FREQUENCY_CHOICES = [
        ("weekly", "Weekly"),
        ("monthly", "Monthly"),
    ]

    name = models.CharField(
        max_length=255,
        verbose_name="Report Name",
        help_text="Human-readable name for this scheduled report",
    )
    report_type = models.CharField(
        max_length=50,
        choices=REPORT_TYPE_CHOICES,
        db_index=True,
        verbose_name="Report Type",
    )
    frequency = models.CharField(
        max_length=10,
        choices=FREQUENCY_CHOICES,
        default="weekly",
        verbose_name="Frequency",
    )
    recipients = models.JSONField(
        default=list,
        verbose_name="Recipients",
        help_text="JSON array of email addresses to send the report to",
    )
    last_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Last Sent At",
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name="Is Active",
        help_text="Whether this scheduled report is enabled",
    )
    extra_filters = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Extra Filters",
        help_text="Optional filters passed to the report generator (e.g. carrier, coverage_type)",
    )

    class Meta:
        verbose_name = "Scheduled Report"
        verbose_name_plural = "Scheduled Reports"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.get_frequency_display()} {self.get_report_type_display()})"

    def is_due(self):
        """Return True if this report is due to be sent based on frequency and last_sent_at."""
        from django.utils import timezone
        from datetime import timedelta

        if not self.is_active:
            return False

        if self.last_sent_at is None:
            return True

        now = timezone.now()
        if self.frequency == "weekly":
            return (now - self.last_sent_at) >= timedelta(days=7)
        elif self.frequency == "monthly":
            # Approximate: 28 days minimum
            return (now - self.last_sent_at) >= timedelta(days=28)

        return False
