from django.db import models
from django.utils import timezone


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At",
        help_text="Timestamp when this record was created",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Updated At",
        help_text="Timestamp when this record was last updated",
    )

    class Meta:
        abstract = True


class SoftDeleteManager(models.Manager):
    """Default manager that excludes soft-deleted records."""

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class SoftDeleteAllManager(models.Manager):
    """Manager that includes soft-deleted records."""

    pass


class SoftDeleteModel(models.Model):
    """Mixin for soft-delete support. For future use — not applied to existing models yet."""

    is_deleted = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name="Is Deleted",
        help_text="Soft-delete flag. True means the record is logically deleted.",
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Deleted At",
        help_text="Timestamp when this record was soft-deleted",
    )

    objects = SoftDeleteManager()
    all_objects = SoftDeleteAllManager()

    class Meta:
        abstract = True

    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at"])

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=["is_deleted", "deleted_at"])


class BaseDocument(TimestampedModel):
    file_type = models.CharField(max_length=50)
    original_filename = models.CharField(max_length=255)
    file_size = models.BigIntegerField(help_text="Size in bytes")
    mime_type = models.CharField(max_length=100)
    s3_key = models.CharField(max_length=500)
    s3_url = models.URLField(max_length=1000)

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class Notification(TimestampedModel):
    """User/org notification for the ops dashboard and portal."""

    NOTIFICATION_TYPES = [
        ("info", "Info"),
        ("warning", "Warning"),
        ("error", "Error"),
        ("success", "Success"),
        ("quote_update", "Quote Update"),
        ("policy_update", "Policy Update"),
        ("claim_update", "Claim Update"),
        ("billing", "Billing"),
        ("system", "System"),
    ]

    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name="User",
        help_text="User this notification is for",
    )
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
        verbose_name="Organization",
        help_text="Organization context for this notification (null = user-level)",
    )
    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES,
        default="info",
        db_index=True,
        verbose_name="Type",
        help_text="Type/category of the notification",
    )
    title = models.CharField(
        max_length=255,
        verbose_name="Title",
        help_text="Short title for the notification",
    )
    message = models.TextField(
        verbose_name="Message",
        help_text="Full notification message body",
    )
    read_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Read At",
        help_text="Timestamp when the user read this notification",
    )
    action_url = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name="Action URL",
        help_text="URL to navigate to when the notification is clicked",
    )
    # GenericForeignKey for related object
    related_content_type = models.ForeignKey(
        "contenttypes.ContentType",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Related Content Type",
    )
    related_object_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Related Object ID",
    )

    class Meta:
        db_table = "notifications"
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["user", "read_at"]),
        ]

    def __str__(self):
        return f"{self.title} → {self.user}"

    @property
    def is_read(self):
        return self.read_at is not None


class AuditLogEntry(models.Model):
    """Structured audit log for the admin dashboard."""

    ACTION_CHOICES = [
        ("create", "Create"),
        ("update", "Update"),
        ("delete", "Delete"),
        ("login", "Login"),
        ("logout", "Logout"),
        ("impersonate", "Impersonate"),
        ("export", "Export"),
        ("approve", "Approve"),
        ("decline", "Decline"),
    ]

    user = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_log_entries",
        verbose_name="User",
        help_text="User who performed the action",
    )
    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        db_index=True,
        verbose_name="Action",
        help_text="Type of action performed",
    )
    model_name = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name="Model Name",
        help_text="Name of the model that was affected (e.g. 'Quote', 'Policy')",
    )
    object_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Object ID",
        help_text="Primary key of the affected object",
    )
    changes = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Changes",
        help_text="JSON dict of changed fields: {field: {old: ..., new: ...}}",
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="IP Address",
        help_text="IP address of the request",
    )
    user_agent = models.TextField(
        null=True,
        blank=True,
        verbose_name="User Agent",
        help_text="Browser/client user agent string",
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name="Timestamp",
        help_text="When the action occurred",
    )

    class Meta:
        db_table = "audit_log_entries"
        verbose_name = "Audit Log Entry"
        verbose_name_plural = "Audit Log Entries"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["user", "-timestamp"]),
            models.Index(fields=["model_name", "object_id"]),
        ]

    def __str__(self):
        user_str = self.user.email if self.user else "system"
        return f"{user_str} {self.action} {self.model_name} {self.object_id or ''}"


class TypeToSignRecord(TimestampedModel):
    """
    Electronic signature record for "type your full name to sign" flows.

    Stores:
    - The signer's typed full name (the "signature")
    - Timestamp of signing (auto-set at creation)
    - IP address of the signer's request
    - Optional user FK (if authenticated)
    - A GenericForeignKey pointing to the signed document/model

    This provides a lightweight, legally-defensible audit trail for
    click-wrap / type-to-sign agreements without a third-party e-sign service.
    """

    signed_name = models.CharField(
        max_length=255,
        verbose_name="Signed Name",
        help_text="The full name typed by the signer as their electronic signature.",
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="IP Address",
        help_text="IP address of the signer at time of signing.",
    )
    user_agent = models.TextField(
        blank=True,
        default="",
        verbose_name="User Agent",
        help_text="Browser/client user agent string at time of signing.",
    )
    signer = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="signatures",
        verbose_name="Signer",
        help_text="Authenticated user who signed, if available.",
    )
    # The document being signed (GenericForeignKey)
    signed_content_type = models.ForeignKey(
        "contenttypes.ContentType",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Signed Document Type",
        help_text="ContentType of the model being signed.",
    )
    signed_object_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Signed Object ID",
        help_text="PK of the model instance being signed.",
    )
    # Agreement text snapshot (capture what was agreed to)
    agreement_text = models.TextField(
        blank=True,
        default="",
        verbose_name="Agreement Text",
        help_text="Snapshot of the agreement text presented at signing.",
    )

    class Meta:
        db_table = "type_to_sign_records"
        verbose_name = "Signature Record"
        verbose_name_plural = "Signature Records"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Signature by '{self.signed_name}' at {self.created_at}"


class DataAccessLog(models.Model):
    """
    SOC 2-compliant data access audit log.

    Records every view, export, modification, or deletion of sensitive data.
    Supplements AuditLogEntry (which covers admin write operations) with
    read/view access tracking for SOC 2 Type II compliance.
    """

    ACTION_CHOICES = [
        ("view", "View"),
        ("export", "Export"),
        ("modify", "Modify"),
        ("delete", "Delete"),
    ]

    user = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="data_access_logs",
        verbose_name="User",
        help_text="User who accessed the data",
    )
    model_name = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name="Model Name",
        help_text="Name of the model accessed (e.g. 'Quote', 'Policy')",
    )
    object_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Object ID",
        help_text="Primary key of the accessed object",
    )
    action = models.CharField(
        max_length=10,
        choices=ACTION_CHOICES,
        db_index=True,
        verbose_name="Action",
        help_text="Type of data access",
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="IP Address",
        help_text="IP address of the request",
    )
    user_agent = models.TextField(
        null=True,
        blank=True,
        verbose_name="User Agent",
        help_text="Browser/client user agent string",
    )
    extra = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Extra",
        help_text="Additional context (endpoint, query params, etc.)",
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name="Timestamp",
        help_text="When the access occurred",
    )

    class Meta:
        db_table = "data_access_logs"
        verbose_name = "Data Access Log"
        verbose_name_plural = "Data Access Logs"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["user", "-timestamp"]),
            models.Index(fields=["model_name", "object_id"]),
            models.Index(fields=["action", "-timestamp"]),
        ]

    def __str__(self):
        user_str = self.user.email if self.user else "system"
        return f"{user_str} {self.action} {self.model_name} {self.object_id or ''}"


class StateChoices(models.TextChoices):
    AL = "AL", "Alabama"
    AK = "AK", "Alaska"
    AZ = "AZ", "Arizona"
    AR = "AR", "Arkansas"
    CA = "CA", "California"
    CO = "CO", "Colorado"
    CT = "CT", "Connecticut"
    DE = "DE", "Delaware"
    FL = "FL", "Florida"
    GA = "GA", "Georgia"
    HI = "HI", "Hawaii"
    ID = "ID", "Idaho"
    IL = "IL", "Illinois"
    IN = "IN", "Indiana"
    IA = "IA", "Iowa"
    KS = "KS", "Kansas"
    KY = "KY", "Kentucky"
    LA = "LA", "Louisiana"
    ME = "ME", "Maine"
    MD = "MD", "Maryland"
    MA = "MA", "Massachusetts"
    MI = "MI", "Michigan"
    MN = "MN", "Minnesota"
    MS = "MS", "Mississippi"
    MO = "MO", "Missouri"
    MT = "MT", "Montana"
    NE = "NE", "Nebraska"
    NV = "NV", "Nevada"
    NH = "NH", "New Hampshire"
    NJ = "NJ", "New Jersey"
    NM = "NM", "New Mexico"
    NY = "NY", "New York"
    NC = "NC", "North Carolina"
    ND = "ND", "North Dakota"
    OH = "OH", "Ohio"
    OK = "OK", "Oklahoma"
    OR = "OR", "Oregon"
    PA = "PA", "Pennsylvania"
    RI = "RI", "Rhode Island"
    SC = "SC", "South Carolina"
    SD = "SD", "South Dakota"
    TN = "TN", "Tennessee"
    TX = "TX", "Texas"
    UT = "UT", "Utah"
    VT = "VT", "Vermont"
    VA = "VA", "Virginia"
    WA = "WA", "Washington"
    WV = "WV", "West Virginia"
    WI = "WI", "Wisconsin"
    WY = "WY", "Wyoming"
    DC = "DC", "District of Columbia"
    AS = "AS", "American Samoa"
    GU = "GU", "Guam"
    MP = "MP", "Northern Mariana Islands"
    PR = "PR", "Puerto Rico"
    VI = "VI", "Virgin Islands"


# ── Compliance Calendar (V3 #29) ──────────────────────────────────────────────


class ComplianceDeadline(TimestampedModel):
    """
    Tracks compliance obligations for Corgi's insurance operations.

    Examples:
        - License renewal: California Producer License expires 2026-05-31
        - Carrier filing: Technology RRG quarterly NAIC filing due 2026-04-15
        - Regulatory: E&S stamping office registration renewal 2026-06-01
        - Audit: Annual SOC 2 audit kickoff 2026-07-01

    The `check_compliance_deadlines` management command sends alerts
    for deadlines due within the configured advance notice window.
    """

    TYPE_CHOICES = [
        ("license_renewal", "License Renewal"),
        ("carrier_filing", "Carrier Filing"),
        ("regulatory", "Regulatory"),
        ("audit", "Audit"),
    ]

    STATUS_CHOICES = [
        ("open", "Open"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("overdue", "Overdue"),
        ("waived", "Waived"),
    ]

    title = models.CharField(
        max_length=255,
        verbose_name="Title",
        help_text="Short description of the compliance obligation",
    )
    deadline_date = models.DateField(
        db_index=True,
        verbose_name="Deadline Date",
        help_text="Date by which the obligation must be completed",
    )
    type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        db_index=True,
        verbose_name="Type",
    )
    responsible_person = models.CharField(
        max_length=255,
        verbose_name="Responsible Person",
        help_text="Name or email of the person responsible for completing this task",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="open",
        db_index=True,
        verbose_name="Status",
    )
    description = models.TextField(
        blank=True,
        verbose_name="Description",
        help_text="Full description, instructions, or reference links",
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Notes",
        help_text="Internal notes or progress updates",
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Completed At",
        help_text="When this deadline was marked as completed",
    )
    alert_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Alert Sent At",
        help_text="When the last compliance alert was sent for this deadline",
    )

    class Meta:
        db_table = "compliance_deadlines"
        verbose_name = "Compliance Deadline"
        verbose_name_plural = "Compliance Deadlines"
        ordering = ["deadline_date", "type"]
        indexes = [
            models.Index(fields=["status", "deadline_date"]),
            models.Index(fields=["type", "deadline_date"]),
        ]

    def __str__(self):
        return f"[{self.get_type_display()}] {self.title} — {self.deadline_date} ({self.get_status_display()})"

    @property
    def is_overdue(self) -> bool:
        from django.utils import timezone

        return (
            self.status not in ("completed", "waived")
            and self.deadline_date < timezone.now().date()
        )

    @property
    def days_until_deadline(self) -> int:
        from django.utils import timezone

        delta = self.deadline_date - timezone.now().date()
        return delta.days


# ─── Feature Flags ────────────────────────────────────────────────────────────


class FeatureFlag(TimestampedModel):
    """
    A runtime feature flag.

    Controls whether a feature is active, optionally scoped by:
    - Global on/off
    - Percentage rollout (deterministic by org/user ID)
    - Org allowlist (M2M to Organization)
    - Staff-only gate

    Full service/admin/templatetag implementation in common/feature_flags.py.
    """

    key = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Flag Key",
        help_text="Unique identifier, e.g. 'new_portal_dashboard'",
        db_index=True,
    )
    description = models.TextField(
        blank=True,
        default="",
        verbose_name="Description",
        help_text="Human-readable description of what this flag controls",
    )
    is_enabled = models.BooleanField(
        default=False,
        verbose_name="Enabled",
        help_text="Master switch — if False, flag is off for everyone",
    )
    rollout_percentage = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="Rollout %",
        help_text="0 = nobody, 100 = everyone (within enabled scope). Deterministic by user/org ID hash.",
    )
    allowed_orgs = models.ManyToManyField(
        "organizations.Organization",
        blank=True,
        related_name="feature_flags",
        verbose_name="Allowed Orgs",
        help_text="Orgs explicitly allowlisted regardless of rollout %",
    )
    staff_only = models.BooleanField(
        default=False,
        verbose_name="Staff Only",
        help_text="If True, only staff (is_staff=True) users can see this feature",
    )

    class Meta:
        verbose_name = "Feature Flag"
        verbose_name_plural = "Feature Flags"
        ordering = ["key"]

    def __str__(self):
        state = "ON" if self.is_enabled else "OFF"
        return f"{self.key} [{state}]"


class PlatformConfig(TimestampedModel):
    """Key-value configuration store for platform options.

    Stores JSON values that can be edited in Django admin by superusers.
    Used for options like limit choices, retention choices, carrier lists,
    coverage types, fee rates, and other values that may change over time
    without requiring a code deploy.

    The ``category`` field groups related configs in the admin UI.
    """

    CATEGORY_CHOICES = [
        ("underwriting", "Underwriting"),
        ("brokerage", "Brokerage"),
        ("billing", "Billing & Fees"),
        ("carriers", "Carriers"),
        ("coverages", "Coverages"),
        ("general", "General"),
    ]

    key = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        verbose_name="Config Key",
        help_text="Unique identifier, e.g. 'limit_options', 'carrier_list'",
    )
    value = models.JSONField(
        verbose_name="Value (JSON)",
        help_text="JSON value — array, object, number, or string",
    )
    category = models.CharField(
        max_length=30,
        choices=CATEGORY_CHOICES,
        default="general",
        db_index=True,
        verbose_name="Category",
    )
    description = models.TextField(
        blank=True,
        default="",
        verbose_name="Description",
        help_text="Human-readable description of what this config controls",
    )

    class Meta:
        db_table = "platform_config"
        verbose_name = "Platform Config"
        verbose_name_plural = "Platform Config"
        ordering = ["category", "key"]

    def __str__(self):
        return f"{self.key} ({self.category})"

    @classmethod
    def get(cls, key: str, default=None):
        """Get a config value by key with optional default."""
        try:
            return cls.objects.get(key=key).value
        except cls.DoesNotExist:
            return default

    @classmethod
    def get_many(cls, keys: list[str]) -> dict:
        """Get multiple config values in one query."""
        configs = cls.objects.filter(key__in=keys).values_list("key", "value")
        return dict(configs)
