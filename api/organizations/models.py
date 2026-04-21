"""
Organization models for multi-tenancy in the Corgi Insurance platform.

All business data (quotes, policies, claims, certificates, documents)
is scoped to an organization. Every user gets a personal org on registration.

Models:
- ``Organization``: Team workspace with an owner.
- ``OrganizationMember``: User ↔ Organization membership with role.
- ``OrganizationInvite``: Invite link with optional expiry and usage limits.

Roles: owner (full control) → editor (create/edit) → viewer (read only).
"""

import string
import random

from django.conf import settings
from django.db import models
from django.utils import timezone

from common.models import TimestampedModel


class Organization(TimestampedModel):
    name = models.CharField(
        max_length=255,
        verbose_name="Name",
        help_text="Display name of the organization",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_organizations",
        verbose_name="Owner",
        help_text="User who owns this organization",
    )
    is_personal = models.BooleanField(
        default=False,
        verbose_name="Is Personal",
        help_text="True if this is a user's auto-created personal organization",
    )
    hubspot_company_id = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        db_index=True,
        verbose_name="HubSpot Company ID",
        help_text="ID of the corresponding HubSpot Company for CRM sync",
    )
    logo_url = models.URLField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name="Logo URL",
        help_text="URL to the organization's logo image",
    )
    website = models.URLField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name="Website",
        help_text="Organization's website URL",
    )
    industry = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Industry",
        help_text="Industry or sector the organization operates in",
    )
    phone = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name="Phone",
        help_text="Organization's primary phone number",
    )
    billing_email = models.EmailField(
        null=True,
        blank=True,
        verbose_name="Billing Email",
        help_text="Email address for billing communications",
    )
    billing_street = models.CharField(max_length=255, blank=True)
    billing_city = models.CharField(max_length=100, blank=True)
    billing_state = models.CharField(max_length=2, blank=True)
    billing_zip = models.CharField(max_length=10, blank=True)
    billing_country = models.CharField(max_length=2, default="US", blank=True)

    class Meta:
        db_table = "organizations_organization"
        verbose_name = "Organization"
        verbose_name_plural = "Organizations"
        ordering = ["name"]

    def __str__(self):
        return self.name


class OrganizationMember(TimestampedModel):
    ROLE_CHOICES = [
        ("owner", "Owner"),
        ("editor", "Editor"),
        ("viewer", "Viewer"),
    ]

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="members",
        verbose_name="Organization",
        help_text="Organization this membership belongs to",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="organization_memberships",
        verbose_name="User",
        help_text="User who is a member of the organization",
    )
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        verbose_name="Role",
        help_text="Member's role: owner (full control), editor (create/edit), viewer (read only)",
    )

    class Meta:
        db_table = "organizations_organizationmember"
        verbose_name = "Organization Member"
        verbose_name_plural = "Organization Members"
        unique_together = ["organization", "user"]
        ordering = ["organization", "role"]

    def __str__(self):
        return f"{self.user} - {self.organization} ({self.role})"


class OrganizationInvite(TimestampedModel):
    ROLE_CHOICES = [
        ("editor", "Editor"),
        ("viewer", "Viewer"),
    ]

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="invites",
        verbose_name="Organization",
        help_text="Organization this invite is for",
    )
    code = models.CharField(
        max_length=12,
        unique=True,
        db_index=True,
        verbose_name="Invite Code",
        help_text="Unique invite code for joining the organization",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Created By",
        help_text="User who created this invite",
    )
    default_role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default="viewer",
        verbose_name="Default Role",
        help_text="Role assigned to users who accept this invite",
    )
    max_uses = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Max Uses",
        help_text="Maximum number of times this invite can be used (null = unlimited)",
    )
    use_count = models.IntegerField(
        default=0,
        verbose_name="Use Count",
        help_text="Number of times this invite has been used",
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Expires At",
        help_text="When this invite expires (null = never)",
    )
    is_revoked = models.BooleanField(
        default=False,
        verbose_name="Is Revoked",
        help_text="Whether this invite has been manually revoked",
    )

    class Meta:
        db_table = "organizations_organizationinvite"
        verbose_name = "Organization Invite"
        verbose_name_plural = "Organization Invites"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.code} - {self.organization}"

    def is_valid(self) -> bool:
        if self.is_revoked:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        if self.max_uses is not None and self.use_count >= self.max_uses:
            return False
        return True

    @staticmethod
    def generate_code() -> str:
        chars = string.ascii_uppercase + string.digits
        while True:
            code = "".join(random.choices(chars, k=8))
            if not OrganizationInvite.objects.filter(code=code).exists():
                return code
