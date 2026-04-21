from django.conf import settings
from django.db import models
from common.models import TimestampedModel


class BrokeredQuoteRequest(TimestampedModel):
    """
    Tracks both:
    1. Skyvern-automated brokered requests (quote FK, form_payload, run_id)
    2. Manual pipeline requests from AEs/brokers (company_name, requester_email, etc.)

    Fields from (1) are nullable so manual requests don't require a linked Quote.
    """

    # ── Pipeline statuses (manual brokering flow) ──────────────────
    PIPELINE_STATUS_CHOICES = [
        ("received", "Received"),
        ("submitted", "Submitted"),
        ("otm", "Out to Market"),
        ("quoted", "Quoted"),
        ("on_hold", "On Hold"),
        ("denied", "Denied"),
        ("recalled", "Recalled"),
        ("blocked", "Blocked"),
        ("stalled", "Stalled"),
        ("cancelled", "Cancelled"),
        ("bound", "Bound"),
    ]

    # ── Legacy Skyvern statuses ────────────────────────────────────
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In Progress"
        QUOTED = "quoted", "Quoted"
        DECLINED = "declined", "Declined"
        FAILED = "failed", "Failed"

    # ── Skyvern fields (nullable for manual requests) ──────────────
    quote = models.ForeignKey(
        "quotes.Quote",
        on_delete=models.CASCADE,
        related_name="brokered_quote_requests",
        verbose_name="Quote",
        null=True,
        blank=True,
    )
    coverage_type = models.CharField(
        max_length=50,
        verbose_name="Coverage Type (Skyvern)",
        help_text="Single coverage type for Skyvern automation, e.g. workers-comp",
        blank=True,
        default="",
    )
    form_payload = models.JSONField(
        verbose_name="Form Payload",
        help_text="Coverage-specific form data sent to the Skyvern workflow",
        null=True,
        blank=True,
    )
    run_id = models.CharField(
        max_length=100, null=True, blank=True, verbose_name="Run ID"
    )
    quote_url = models.URLField(
        max_length=500, null=True, blank=True, verbose_name="Quote URL"
    )
    external_quote_number = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="External Quote Number",
    )

    # ── Manual pipeline fields ─────────────────────────────────────
    company_name = models.CharField(
        max_length=255, blank=True, default="", verbose_name="Company Name"
    )
    status = models.CharField(
        max_length=30,
        choices=PIPELINE_STATUS_CHOICES,
        default="received",
        verbose_name="Status",
        db_index=True,
    )
    coverage_types = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Coverage Types",
        help_text="List of coverage type codes, e.g. ['cgl', 'cyber']",
    )
    carrier = models.CharField(
        max_length=100, blank=True, default="", verbose_name="Carrier"
    )
    requested_coverage_detail = models.TextField(
        blank=True, default="", verbose_name="Requested Coverage Detail"
    )
    aggregate_limit = models.CharField(
        max_length=50, blank=True, default="", verbose_name="Aggregate Limit"
    )
    per_occurrence_limit = models.CharField(
        max_length=50, blank=True, default="", verbose_name="Per Occurrence Limit"
    )
    retention = models.CharField(
        max_length=50, blank=True, default="", verbose_name="Retention"
    )
    blocker_type = models.CharField(
        max_length=50, blank=True, default="", verbose_name="Blocker Type"
    )
    blocker_detail = models.TextField(
        blank=True, default="", verbose_name="Blocker Detail"
    )
    premium_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Premium Amount",
    )
    decline_reason = models.TextField(
        null=True, blank=True, verbose_name="Decline Reason"
    )
    requester_email = models.EmailField(
        blank=True, default="", verbose_name="Requester Email"
    )
    client_email = models.EmailField(
        blank=True, default="", verbose_name="Client Email"
    )
    client_contact_url = models.CharField(
        max_length=500, blank=True, default="", verbose_name="Client Contact URL"
    )
    django_admin_url = models.CharField(
        max_length=500, blank=True, default="", verbose_name="Django Admin URL"
    )
    notes = models.TextField(blank=True, default="", verbose_name="Notes")
    additional_notes = models.TextField(
        blank=True, default="", verbose_name="Additional Notes"
    )
    missing_docs_note = models.TextField(
        blank=True, default="", verbose_name="Missing Documents Note"
    )
    is_bound = models.BooleanField(default=False, verbose_name="Is Bound")
    custom_product_created = models.BooleanField(
        default=False, verbose_name="Custom Product Created"
    )
    docs_uploaded = models.BooleanField(default=False, verbose_name="Docs Uploaded")
    stripe_confirmed = models.BooleanField(
        default=False, verbose_name="Stripe Confirmed"
    )

    # ── Shared fields ──────────────────────────────────────────────
    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("urgent", "Urgent"),
    ]
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_brokered_requests",
        verbose_name="Assigned To",
    )
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default="medium",
        db_index=True,
        verbose_name="Priority",
    )

    class Meta:
        db_table = "brokered_quote_requests"
        verbose_name = "Brokered Quote Request"
        verbose_name_plural = "Brokered Quote Requests"

    def __str__(self):
        name = self.company_name or (
            self.quote.quote_number if self.quote_id else str(self.id)
        )
        return f"{name} – {self.status}"

    @property
    def requester_name(self):
        return self.requester_email.split("@")[0] if self.requester_email else ""

    @property
    def coverage_type_display(self):
        return (
            ", ".join(self.coverage_types)
            if self.coverage_types
            else self.coverage_type
        )

    def get_carrier_display(self):
        return self.carrier
