"""
Document management models for organizing customer documents.

DocumentFolder provides a nested folder structure per organization,
allowing admins to organize documents (UserDocument) into categorized
folders instead of raw S3 link lists.
"""

from django.db import models
from common.models import TimestampedModel


class DocumentFolder(TimestampedModel):
    """A folder for organizing documents per organization.

    Supports nesting via the self-referential parent FK.
    Folders are org-scoped: one org cannot see another's folders.

    Example hierarchy:
        Acme Corp/
        ├── 2024 Policies/
        │   ├── CGL Policy
        │   └── E&O Policy
        └── Claims/
            └── 2024 Claim #001
    """

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="document_folders",
        verbose_name="Organization",
    )
    name = models.CharField(
        max_length=255,
        verbose_name="Folder Name",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        verbose_name="Parent Folder",
        help_text="Parent folder for nesting. Null = root folder.",
    )
    description = models.TextField(
        blank=True,
        default="",
        verbose_name="Description",
        help_text="Optional description of what this folder contains",
    )
    color = models.CharField(
        max_length=20,
        blank=True,
        default="",
        verbose_name="Color",
        help_text="Optional hex color for visual organization (e.g. #ff5c00)",
    )
    created_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_folders",
        verbose_name="Created By",
    )

    class Meta:
        db_table = "document_folders"
        verbose_name = "Document Folder"
        verbose_name_plural = "Document Folders"
        ordering = ["name"]
        unique_together = [("organization", "parent", "name")]

    def __str__(self):
        if self.parent:
            return f"{self.parent} / {self.name}"
        return self.name

    @property
    def full_path(self) -> str:
        """Return the full path from root to this folder."""
        parts = [self.name]
        node = self.parent
        while node:
            parts.insert(0, node.name)
            node = node.parent
        return " / ".join(parts)

    @property
    def depth(self) -> int:
        """Return nesting depth (0 = root)."""
        d = 0
        node = self.parent
        while node:
            d += 1
            node = node.parent
        return d


class DocumentFolderItem(TimestampedModel):
    """Associates a UserDocument with a DocumentFolder."""

    folder = models.ForeignKey(
        DocumentFolder,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Folder",
    )
    document = models.ForeignKey(
        "users.UserDocument",
        on_delete=models.CASCADE,
        related_name="folder_items",
        verbose_name="Document",
    )
    added_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Added By",
    )

    class Meta:
        db_table = "document_folder_items"
        verbose_name = "Document Folder Item"
        verbose_name_plural = "Document Folder Items"
        unique_together = [("folder", "document")]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.document.title} → {self.folder}"


class ShareLink(TimestampedModel):
    """Tokenized share link for a claim document or certificate.

    Customers generate a public, time-limited URL that surfaces an S3
    signed-URL for the underlying document. Supports manual revocation.
    """

    RESOURCE_TYPE_CHOICES = [
        ("certificate", "Certificate"),
        ("claim", "Claim"),
    ]

    token = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        verbose_name="Token",
        help_text="URL-safe token used as the public share identifier",
    )
    resource_type = models.CharField(
        max_length=20,
        choices=RESOURCE_TYPE_CHOICES,
        db_index=True,
        verbose_name="Resource Type",
    )
    resource_id = models.BigIntegerField(
        verbose_name="Resource ID",
        help_text="PK of the shared resource (CustomCertificate or ClaimDocument)",
    )
    expires_at = models.DateTimeField(
        verbose_name="Expires At",
        help_text="When this share link stops resolving",
    )
    created_by = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="created_share_links",
        verbose_name="Created By",
    )
    revoked_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Revoked At",
        help_text="Timestamp when this link was manually revoked (null = active)",
    )

    class Meta:
        db_table = "document_share_links"
        verbose_name = "Share Link"
        verbose_name_plural = "Share Links"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["resource_type", "resource_id"]),
        ]

    def __str__(self):
        return f"ShareLink<{self.resource_type}:{self.resource_id}> {self.token[:8]}…"

    @property
    def is_expired(self) -> bool:
        from django.utils import timezone

        return self.expires_at <= timezone.now()

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None

    @property
    def is_active(self) -> bool:
        return not self.is_revoked and not self.is_expired
