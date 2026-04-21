"""
User and authentication models for the Corgi Insurance platform.

Provides a custom User model with email-based auth, OTP login codes,
password reset codes, impersonation logging, and org-scoped document storage.

Models:
- ``User``: Custom user with email as username, JWT-based auth.
- ``ImpersonationLog``: Audit trail for admin impersonation sessions.
- ``PasswordResetCode``: Time-limited 6-digit reset codes.
- ``EmailLoginCode``: Time-limited 6-digit OTP login codes.
- ``UserDocument``: S3-backed documents (policies, certificates, receipts).
"""

from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.contrib.postgres.fields import ArrayField
from django.utils import timezone as django_timezone
from common.models import TimestampedModel, BaseDocument


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin, TimestampedModel):
    ROLE_CHOICES = [
        ("admin", "Admin"),
        ("ae", "Account Executive"),
        ("ae_underwriting", "AE + Underwriting"),
        ("bdr", "Business Development Rep"),
        ("finance", "Finance"),
        ("broker", "Broker"),
        ("claims_adjuster", "Claims Adjuster"),
        ("customer_support", "Customer Support"),
        ("read_only", "Read-Only API"),
        ("policyholder", "Policyholder"),
    ]

    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    phone_number = models.CharField(max_length=20, blank=True)
    company_name = models.CharField(max_length=255, blank=True)
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="policyholder",
        db_index=True,
        verbose_name="Role",
        help_text="Policyholders can only access the portal.",
    )
    is_active = models.BooleanField(default=True, db_index=True)
    is_staff = models.BooleanField(default=False)
    hubspot_contact_id = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        db_index=True,
        verbose_name="HubSpot Contact ID",
        help_text="ID of the corresponding HubSpot Contact for CRM sync",
    )
    avatar_url = models.URLField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name="Avatar URL",
        help_text="URL to the user's avatar image",
    )
    timezone = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="Timezone",
        help_text="User's preferred timezone (e.g. 'America/New_York')",
    )
    notification_preferences = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Notification Preferences",
        help_text="User notification settings: {email_quotes, email_claims, email_billing, push_enabled}",
    )
    failed_login_attempts = models.IntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        verbose_name = "user"
        verbose_name_plural = "users"

    def __str__(self):
        return self.email

    @property
    def is_locked(self) -> bool:
        if self.locked_until and self.locked_until > django_timezone.now():
            return True
        return False

    def record_failed_login(self) -> None:
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= 5:
            from datetime import timedelta

            self.locked_until = django_timezone.now() + timedelta(minutes=30)
        self.save(update_fields=["failed_login_attempts", "locked_until"])

    def reset_failed_logins(self) -> None:
        if self.failed_login_attempts > 0 or self.locked_until:
            self.failed_login_attempts = 0
            self.locked_until = None
            self.save(update_fields=["failed_login_attempts", "locked_until"])

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()


class LoginEvent(TimestampedModel):
    """Records every successful and failed login attempt with IP and user-agent."""

    METHOD_CHOICES = [
        ("otp", "Email OTP"),
        ("password", "Password"),
        ("refresh", "Token Refresh"),
        ("impersonation", "Impersonation"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="login_events",
        verbose_name="User",
        null=True,
        blank=True,
        help_text="Null for failed attempts where user could not be resolved",
    )
    email = models.EmailField(
        verbose_name="Email",
        help_text="Email used in the login attempt (always recorded)",
    )
    method = models.CharField(
        max_length=20,
        choices=METHOD_CHOICES,
        verbose_name="Login Method",
    )
    success = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name="Success",
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="IP Address",
    )
    user_agent = models.TextField(
        blank=True,
        default="",
        verbose_name="User Agent",
    )
    failure_reason = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="Failure Reason",
        help_text="Reason for failed login (e.g. 'invalid_code', 'wrong_password', 'locked')",
    )
    country = models.CharField(
        max_length=2,
        blank=True,
        default="",
        verbose_name="Country Code",
        help_text="ISO 3166-1 alpha-2 country code from IP geolocation (if available)",
    )

    class Meta:
        db_table = "login_events"
        verbose_name = "Login Event"
        verbose_name_plural = "Login Events"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["email", "-created_at"]),
            models.Index(fields=["ip_address", "-created_at"]),
            models.Index(fields=["success", "-created_at"]),
        ]

    def __str__(self):
        status = "✓" if self.success else "✗"
        return f"{status} {self.email} via {self.method} from {self.ip_address or 'unknown'}"


class ImpersonationLog(TimestampedModel):
    admin_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="impersonation_sessions",
        verbose_name="Admin User",
    )
    impersonated_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="impersonated_by",
        verbose_name="Impersonated User",
    )
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        db_table = "impersonation_logs"
        verbose_name = "Impersonation Log"
        verbose_name_plural = "Impersonation Logs"
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.admin_user.email} → {self.impersonated_user.email}"


class PasswordResetCode(TimestampedModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="password_reset_codes",
    )
    code = models.CharField(max_length=6)
    is_used = models.BooleanField(default=False)
    attempts = models.IntegerField(default=0)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = "password_reset_codes"

    def is_valid(self):
        return (
            not self.is_used
            and self.attempts < 5
            and self.expires_at > django_timezone.now()
        )

    def __str__(self):
        return f"Reset code for {self.user.email}"


class EmailLoginCode(TimestampedModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="login_codes",
    )
    code = models.CharField(max_length=6)
    is_used = models.BooleanField(default=False)
    attempts = models.IntegerField(default=0)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = "email_login_codes"

    def is_valid(self):
        return (
            not self.is_used
            and self.attempts < 5
            and self.expires_at > django_timezone.now()
        )

    def __str__(self):
        return f"Login code for {self.user.email}"


class TOTPDevice(TimestampedModel):
    """
    TOTP (Time-based One-Time Password) device for two-factor authentication (V3 #54).

    Stores a per-user TOTP secret. The secret is never returned to clients after setup;
    only the QR URI is provided during enrollment.

    Workflow:
        1. POST /api/v1/auth/totp/setup   → generates secret + QR provisioning URI
        2. POST /api/v1/auth/totp/verify  → verifies the first code to activate the device
        3. POST /api/v1/auth/totp/validate → verifies code during login
    """

    ISSUER_NAME = "Corgi Insurance"

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="totp_device",
        verbose_name="User",
    )
    secret_key = models.CharField(
        max_length=64,
        verbose_name="Secret Key",
        help_text="Base32-encoded TOTP secret — never expose to clients after setup",
    )
    is_verified = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name="Is Verified",
        help_text="True after the user has successfully confirmed the device with their first valid code",
    )
    last_used_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Last Used At",
        help_text="When the TOTP was last successfully validated",
    )
    backup_codes = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Backup Codes",
        help_text="List of single-use hashed backup codes",
    )

    class Meta:
        db_table = "totp_devices"
        verbose_name = "TOTP Device"
        verbose_name_plural = "TOTP Devices"

    def __str__(self):
        status = "verified" if self.is_verified else "pending"
        return f"TOTP({self.user.email}) [{status}]"

    def get_provisioning_uri(self) -> str:
        """Return the otpauth:// URI for QR code generation."""
        import pyotp

        totp = pyotp.TOTP(self.secret_key)
        return totp.provisioning_uri(name=self.user.email, issuer_name=self.ISSUER_NAME)

    def verify_code(self, code: str, valid_window: int = 1) -> bool:
        """
        Verify a TOTP code.  *valid_window* allows ±1 time steps (30s each)
        to tolerate minor clock skew.
        """
        import pyotp

        totp = pyotp.TOTP(self.secret_key)
        return totp.verify(code, valid_window=valid_window)

    def activate(self, code: str) -> bool:
        """Verify and activate the device. Returns True on success."""
        from django.utils import timezone

        if self.verify_code(code):
            self.is_verified = True
            self.last_used_at = timezone.now()
            self.save(update_fields=["is_verified", "last_used_at"])
            return True
        return False


class ActiveSession(TimestampedModel):
    """
    Tracks active authenticated sessions for session management (V3 #56).

    Created on login; updated on each authenticated request via middleware.
    Sessions inactive for more than SESSION_INACTIVITY_HOURS are auto-expired.
    """

    SESSION_INACTIVITY_HOURS = 24

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="active_sessions",
        verbose_name="User",
    )
    session_key = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        verbose_name="Session Key",
        help_text="Opaque identifier for this session (JWT jti or random token)",
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="IP Address",
    )
    user_agent = models.TextField(
        blank=True,
        default="",
        verbose_name="User Agent",
    )
    last_activity = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Last Activity",
        help_text="Timestamp of the most recent request on this session",
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name="Is Active",
        help_text="False if the session was explicitly revoked or expired",
    )
    revoked_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Revoked At",
    )

    class Meta:
        db_table = "active_sessions"
        verbose_name = "Active Session"
        verbose_name_plural = "Active Sessions"
        ordering = ["-last_activity"]
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["session_key"]),
        ]

    def __str__(self):
        return f"{self.user.email} — {self.session_key[:12]}… ({'active' if self.is_active else 'revoked'})"

    def revoke(self):
        from django.utils import timezone

        self.is_active = False
        self.revoked_at = timezone.now()
        self.save(update_fields=["is_active", "revoked_at"])

    def touch(self):
        """Update last_activity to now."""
        from django.utils import timezone

        self.last_activity = timezone.now()
        self.save(update_fields=["last_activity"])

    @property
    def is_expired(self) -> bool:
        from datetime import timedelta
        from django.utils import timezone

        cutoff = timezone.now() - timedelta(hours=self.SESSION_INACTIVITY_HOURS)
        return self.last_activity < cutoff


class TwoFactorDeliveryLog(TimestampedModel):
    """Audit trail for each 2FA code delivery attempt (C4)."""

    CHANNEL_CHOICES = [
        ("email", "Email"),
        ("sms", "SMS"),
    ]
    STATUS_CHOICES = [
        ("sent", "Sent"),
        ("failed", "Failed"),
        ("retried", "Retried"),
        ("fallback", "Fallback"),
        ("skipped", "Skipped"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="two_factor_delivery_logs",
    )
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES)
    provider_msg_id = models.CharField(max_length=255, blank=True, default="")
    error = models.TextField(blank=True, default="")

    class Meta:
        db_table = "two_factor_delivery_logs"
        verbose_name = "Two-Factor Delivery Log"
        verbose_name_plural = "Two-Factor Delivery Logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["status", "-created_at"]),
        ]

    def __str__(self):
        who = self.user.email if self.user_id else "deleted-user"
        return f"2FA {self.channel}/{self.status} -> {who}"


class UserDocument(BaseDocument):
    CATEGORY_CHOICES = [
        ("policy", "Policy"),
        ("certificate", "Certificate"),
        ("endorsement", "Endorsement"),
        ("receipt", "Receipt"),
        ("loss_run", "Loss Run Report"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="user_documents",
    )
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default="policy",
        verbose_name="Category",
    )
    title = models.CharField(
        max_length=255,
        verbose_name="Title",
        help_text="Display title for the document (e.g., 'Errors & Omissions')",
    )
    policy_numbers = ArrayField(
        models.CharField(max_length=50),
        default=list,
        blank=True,
        verbose_name="Policy Numbers",
        help_text="Associated policy numbers for this document",
    )
    effective_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Effective Date",
    )
    expiration_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Expiration Date",
    )

    class Meta:
        db_table = "user_documents"
        verbose_name = "User Document"
        verbose_name_plural = "User Documents"
        ordering = ["category", "-created_at"]

    def __str__(self):
        return f"{self.title} - {self.user.email}"
