"""
Certificate of Insurance models for the Corgi Insurance platform.

Supports custom COI generation with holder information, endorsement types,
and service location details. Each custom certificate generates a unique
COI number derived from the parent COI.
"""

from django.db import models
from common.models import StateChoices, TimestampedModel
from users.models import User, UserDocument


class EndorsementType(models.TextChoices):
    WAIVER_OF_SUBROGATION = "waiver_of_subrogation", "Waiver of Subrogation"
    PRIMARY_AND_NON_CONTRIBUTORY = (
        "primary_and_non_contributory",
        "Primary and Non-Contributory",
    )
    JOB_SERVICE_LOCATION = "job_service_location", "Job/Service Location"
    JOB_SERVICE_YOU_PROVIDE = "job_service_you_provide", "Job/Service You Provide"
    THIRTY_DAY_NOTICE = "thirty_day_notice", "30 Day Notice of Cancellation"
    COVERAGE_FOLLOWER = "coverage_follower", "Coverage Follower"


class CustomCertificate(TimestampedModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="custom_certificates",
    )
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="custom_certificates",
    )
    coi_number = models.CharField(max_length=50, db_index=True)
    custom_coi_number = models.CharField(max_length=60, unique=True)
    holder_name = models.CharField(max_length=255)
    holder_second_line = models.CharField(max_length=255, blank=True, default="")
    holder_street_address = models.CharField(max_length=255)
    holder_suite = models.CharField(max_length=100, blank=True, default="")
    holder_city = models.CharField(max_length=100)
    holder_state = models.CharField(max_length=2, choices=StateChoices.choices)
    holder_zip = models.CharField(max_length=10)
    is_additional_insured = models.BooleanField(default=False)
    endorsements = models.JSONField(default=list)
    service_location_job = models.CharField(max_length=255, blank=True, default="")
    service_location_address = models.CharField(max_length=500, blank=True, default="")
    service_you_provide_job = models.CharField(max_length=255, blank=True, default="")
    service_you_provide_service = models.TextField(blank=True, default="")
    document = models.OneToOneField(
        UserDocument,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="custom_certificate",
    )

    CERTIFICATE_STATUS_CHOICES = [
        ("active", "Active"),
        ("revoked", "Revoked"),
        ("expired", "Expired"),
    ]

    status = models.CharField(
        max_length=10,
        choices=CERTIFICATE_STATUS_CHOICES,
        default="active",
        db_index=True,
        verbose_name="Status",
        help_text="Current status of this certificate",
    )
    revoked_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Revoked At",
        help_text="Timestamp when this certificate was revoked",
    )
    revoked_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="revoked_certificates",
        verbose_name="Revoked By",
        help_text="User who revoked this certificate",
    )

    class Meta:
        db_table = "custom_certificates"
        ordering = ["-created_at"]
        unique_together = [("user", "organization", "coi_number", "holder_name")]

    def __str__(self):
        return f"Custom Certificate {self.custom_coi_number} for {self.holder_name}"

    @property
    def holder_full_address(self) -> str:
        lines = [self.holder_street_address]
        if self.holder_suite:
            lines.append(self.holder_suite)
        lines.append(f"{self.holder_city}, {self.holder_state} {self.holder_zip}")
        return "\n".join(lines)

    @classmethod
    def generate_custom_coi_number(cls, coi_number: str) -> str:
        existing_count = cls.objects.filter(coi_number=coi_number).count()
        sequence = existing_count + 1
        return f"{coi_number}-{sequence:02d}"


class AdditionalInsured(TimestampedModel):
    """
    Represents an additional insured party on a policy.

    Customers can add/remove additional insureds from the portal.
    When added, a custom COI certificate is auto-generated and emailed
    to the additional insured's email address.
    """

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="additional_insureds",
        verbose_name="Organization",
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="added_additional_insureds",
        verbose_name="Created By",
    )
    coi_number = models.CharField(
        max_length=50,
        db_index=True,
        verbose_name="COI Number",
        help_text="The base COI number this additional insured is linked to.",
    )

    # Additional insured details
    name = models.CharField(
        max_length=255,
        verbose_name="Name",
        help_text="Full legal name of the additional insured.",
    )
    address = models.CharField(
        max_length=500,
        blank=True,
        default="",
        verbose_name="Address",
        help_text="Mailing address of the additional insured.",
    )
    email = models.EmailField(
        blank=True,
        default="",
        verbose_name="Email",
        help_text="Email address to send the COI copy to.",
    )
    phone = models.CharField(
        max_length=30,
        blank=True,
        default="",
        verbose_name="Phone",
        help_text="Contact phone number.",
    )

    # Link to the generated certificate
    certificate = models.OneToOneField(
        CustomCertificate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="additional_insured_record",
        verbose_name="Generated Certificate",
        help_text="The CustomCertificate generated for this additional insured.",
    )

    STATUS_CHOICES = [
        ("active", "Active"),
        ("removed", "Removed"),
    ]
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="active",
        db_index=True,
        verbose_name="Status",
    )
    removed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Removed At",
    )
    removed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="removed_additional_insureds",
        verbose_name="Removed By",
    )

    class Meta:
        db_table = "additional_insureds"
        verbose_name = "Additional Insured"
        verbose_name_plural = "Additional Insureds"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Additional Insured: {self.name} (COI {self.coi_number})"
