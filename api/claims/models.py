"""
Claims models for the Corgi Insurance platform.

Tracks insurance claims from submission through resolution, with
financial tracking fields for paid losses, LAE, and case reserves.

Status flow: submitted → under_review → approved/denied → closed
"""

from django.db import models

from common.models import StateChoices, TimestampedModel, SoftDeleteModel, BaseDocument
from common.utils import generate_short_id
from policies.models import Policy
from users.models import User


class Claim(SoftDeleteModel, TimestampedModel):
    STATUS_CHOICES = [
        ("submitted", "Submitted"),
        ("under_review", "Under Review"),
        ("approved", "Approved"),
        ("denied", "Denied"),
        ("closed", "Closed"),
    ]

    claim_number = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="Claim Number",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="claims",
        verbose_name="User",
    )
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="claims",
    )
    policy = models.ForeignKey(
        Policy,
        on_delete=models.PROTECT,
        related_name="claims",
        verbose_name="Policy",
    )
    organization_name = models.CharField(
        max_length=255,
        verbose_name="Organization Name",
    )
    first_name = models.CharField(
        max_length=100,
        verbose_name="First Name",
    )
    last_name = models.CharField(
        max_length=100,
        verbose_name="Last Name",
    )
    email = models.EmailField(
        verbose_name="Email",
    )
    phone_number = models.CharField(
        max_length=20,
        verbose_name="Phone Number",
    )
    description = models.TextField(
        verbose_name="Description",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="submitted",
        db_index=True,
        verbose_name="Status",
    )
    admin_notes = models.TextField(
        blank=True,
        default="",
        verbose_name="Admin Notes",
    )
    claim_report_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Claim Report Date",
    )
    loss_state = models.CharField(
        max_length=2,
        choices=StateChoices.choices,
        null=True,
        blank=True,
        verbose_name="Loss State",
    )
    paid_loss = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Paid Loss",
    )
    paid_lae = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Paid LAE",
    )
    case_reserve_loss = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Case Reserve Loss",
    )
    case_reserve_lae = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Case Reserve LAE",
    )
    incident_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Incident Date",
        help_text="Date when the incident occurred",
    )
    loss_amount_estimate = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Loss Amount Estimate",
        help_text="Estimated total loss amount",
    )
    resolution_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Resolution Date",
        help_text="Date when the claim was resolved",
    )
    resolution_notes = models.TextField(
        null=True,
        blank=True,
        verbose_name="Resolution Notes",
        help_text="Notes about the claim resolution",
    )

    class Meta:
        db_table = "claims"
        verbose_name = "Claim"
        verbose_name_plural = "Claims"
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.claim_number:
            self.claim_number = f"CLM-{generate_short_id(8)}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Claim {self.claim_number}"


class ClaimDocument(BaseDocument):
    claim = models.ForeignKey(
        Claim,
        on_delete=models.CASCADE,
        related_name="documents",
        verbose_name="Claim",
    )

    class Meta:
        db_table = "claim_documents"
        verbose_name = "Claim Document"
        verbose_name_plural = "Claim Documents"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.original_filename} - {self.claim.claim_number}"
