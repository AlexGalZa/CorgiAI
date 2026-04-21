import hashlib
import secrets

from django.db import models
from django.conf import settings

from common.models import TimestampedModel
from api_keys.constants import API_KEY_PREFIX, API_KEY_PREFIX_LENGTH


def generate_api_key():
    raw = API_KEY_PREFIX + secrets.token_urlsafe(32)
    prefix = raw[:API_KEY_PREFIX_LENGTH]
    key_hash = hashlib.sha256(raw.encode()).hexdigest()
    return raw, prefix, key_hash


def generate_invite_token():
    return secrets.token_urlsafe(32)


class ApiKey(TimestampedModel):
    organization = models.ForeignKey(
        "organizations.Organization",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="api_keys",
        verbose_name="Organization",
    )
    name = models.CharField(
        max_length=255,
        verbose_name="Name",
        help_text='Descriptive label for this key, e.g. "Agency X production"',
    )
    prefix = models.CharField(
        max_length=16,
        unique=True,
        verbose_name="Prefix",
        help_text="First 16 characters of the raw key, used for fast lookup",
    )
    key_hash = models.CharField(
        max_length=64,
        verbose_name="Key Hash",
        help_text="SHA-256 hash of the raw key (plaintext is never stored)",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Active",
    )
    last_used_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Last Used At",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_api_keys",
        verbose_name="Created By",
    )

    class Meta:
        db_table = "external_api_keys"
        verbose_name = "API Key"
        verbose_name_plural = "API Keys"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.prefix}…)"


class ApiKeyInvite(TimestampedModel):
    token = models.CharField(
        max_length=64,
        unique=True,
        verbose_name="Token",
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Expires At",
    )
    is_used = models.BooleanField(
        default=False,
        verbose_name="Used",
    )
    used_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Used At",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_api_key_invites",
        verbose_name="Created By",
    )

    partner_first_name = models.CharField(max_length=150, blank=True, default="")
    partner_last_name = models.CharField(max_length=150, blank=True, default="")
    partner_org_name = models.CharField(max_length=255, blank=True, default="")
    partner_email = models.EmailField(blank=True, default="")

    api_key = models.OneToOneField(
        ApiKey,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="invite",
        verbose_name="API Key",
    )

    class Meta:
        db_table = "external_api_key_invites"
        verbose_name = "API Key Invite"
        verbose_name_plural = "API Key Invites"
        ordering = ["-created_at"]

    def __str__(self):
        status = "used" if self.is_used else "pending"
        return f"Invite {self.token[:12]}… ({status})"

    def is_valid(self):
        from django.utils import timezone

        if self.is_used:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        return True
