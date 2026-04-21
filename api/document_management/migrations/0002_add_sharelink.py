"""Adds the ShareLink model for time-limited public document share URLs."""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("document_management", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ShareLink",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="Timestamp when this record was created",
                        verbose_name="Created At",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        help_text="Timestamp when this record was last updated",
                        verbose_name="Updated At",
                    ),
                ),
                (
                    "token",
                    models.CharField(
                        db_index=True,
                        help_text="URL-safe token used as the public share identifier",
                        max_length=64,
                        unique=True,
                        verbose_name="Token",
                    ),
                ),
                (
                    "resource_type",
                    models.CharField(
                        choices=[("certificate", "Certificate"), ("claim", "Claim")],
                        db_index=True,
                        max_length=20,
                        verbose_name="Resource Type",
                    ),
                ),
                (
                    "resource_id",
                    models.BigIntegerField(
                        help_text="PK of the shared resource (CustomCertificate or ClaimDocument)",
                        verbose_name="Resource ID",
                    ),
                ),
                (
                    "expires_at",
                    models.DateTimeField(
                        help_text="When this share link stops resolving",
                        verbose_name="Expires At",
                    ),
                ),
                (
                    "revoked_at",
                    models.DateTimeField(
                        blank=True,
                        help_text="Timestamp when this link was manually revoked (null = active)",
                        null=True,
                        verbose_name="Revoked At",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="created_share_links",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Created By",
                    ),
                ),
            ],
            options={
                "verbose_name": "Share Link",
                "verbose_name_plural": "Share Links",
                "db_table": "document_share_links",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(
                        fields=["resource_type", "resource_id"],
                        name="document_sh_resourc_2b3f5e_idx",
                    )
                ],
            },
        ),
    ]
