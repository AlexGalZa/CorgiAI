from django.db import models

from common.models import TimestampedModel


class Demo(TimestampedModel):
    """A scheduled demo call between a prospective customer and an Account Executive."""

    STATUS_CHOICES = [
        ("scheduled", "Scheduled"),
        ("held", "Held"),
        ("no_show", "No Show"),
        ("cancelled", "Cancelled"),
    ]

    customer_email = models.EmailField(
        verbose_name="Customer Email",
        help_text="Email of the prospective customer booking the demo",
    )
    customer_name = models.CharField(
        max_length=255,
        verbose_name="Customer Name",
        help_text="Full name of the prospective customer",
    )
    ae = models.ForeignKey(
        "producers.Producer",
        on_delete=models.PROTECT,
        related_name="demos",
        verbose_name="Account Executive",
        help_text="The AE assigned to host this demo",
    )
    scheduled_for = models.DateTimeField(
        verbose_name="Scheduled For",
        help_text="Start time of the demo",
    )
    duration_minutes = models.IntegerField(
        default=30,
        verbose_name="Duration (minutes)",
        help_text="Expected length of the demo in minutes",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="scheduled",
        verbose_name="Status",
    )
    join_url = models.TextField(
        blank=True,
        verbose_name="Join URL",
        help_text="Video conference join link",
    )
    recording_url = models.TextField(
        blank=True,
        verbose_name="Recording URL",
        help_text="Recording link populated after the demo",
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Notes",
        help_text="AE notes captured after the demo",
    )

    class Meta:
        db_table = "demos"
        verbose_name = "Demo"
        verbose_name_plural = "Demos"
        ordering = ["-scheduled_for"]
        indexes = [
            models.Index(fields=["ae", "scheduled_for"], name="demos_ae_sched_idx"),
            models.Index(
                fields=["status", "scheduled_for"], name="demos_status_sched_idx"
            ),
        ]

    def __str__(self):
        return f"Demo: {self.customer_name} with {self.ae.name} @ {self.scheduled_for:%Y-%m-%d %H:%M} [{self.status}]"
