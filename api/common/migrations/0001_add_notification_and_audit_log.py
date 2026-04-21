"""Add Notification and AuditLogEntry models."""

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("contenttypes", "0002_remove_content_type_name"),
        ("organizations", "0004_backfill_personal_org_names"),
    ]

    operations = [
        migrations.CreateModel(
            name="Notification",
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
                    "notification_type",
                    models.CharField(
                        choices=[
                            ("info", "Info"),
                            ("warning", "Warning"),
                            ("error", "Error"),
                            ("success", "Success"),
                            ("quote_update", "Quote Update"),
                            ("policy_update", "Policy Update"),
                            ("claim_update", "Claim Update"),
                            ("billing", "Billing"),
                            ("system", "System"),
                        ],
                        db_index=True,
                        default="info",
                        help_text="Type/category of the notification",
                        max_length=20,
                        verbose_name="Type",
                    ),
                ),
                (
                    "title",
                    models.CharField(
                        help_text="Short title for the notification",
                        max_length=255,
                        verbose_name="Title",
                    ),
                ),
                (
                    "message",
                    models.TextField(
                        help_text="Full notification message body",
                        verbose_name="Message",
                    ),
                ),
                (
                    "read_at",
                    models.DateTimeField(
                        blank=True,
                        db_index=True,
                        help_text="Timestamp when the user read this notification",
                        null=True,
                        verbose_name="Read At",
                    ),
                ),
                (
                    "action_url",
                    models.CharField(
                        blank=True,
                        help_text="URL to navigate to when the notification is clicked",
                        max_length=500,
                        null=True,
                        verbose_name="Action URL",
                    ),
                ),
                (
                    "related_object_id",
                    models.PositiveIntegerField(
                        blank=True, null=True, verbose_name="Related Object ID"
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        help_text="User this notification is for",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notifications",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="User",
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        blank=True,
                        help_text="Organization context for this notification (null = user-level)",
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notifications",
                        to="organizations.organization",
                        verbose_name="Organization",
                    ),
                ),
                (
                    "related_content_type",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="contenttypes.contenttype",
                        verbose_name="Related Content Type",
                    ),
                ),
            ],
            options={
                "db_table": "notifications",
                "verbose_name": "Notification",
                "verbose_name_plural": "Notifications",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="notification",
            index=models.Index(
                fields=["user", "-created_at"], name="notificatio_user_id_created_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="notification",
            index=models.Index(
                fields=["user", "read_at"], name="notificatio_user_id_read_at_idx"
            ),
        ),
        migrations.CreateModel(
            name="AuditLogEntry",
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
                    "action",
                    models.CharField(
                        choices=[
                            ("create", "Create"),
                            ("update", "Update"),
                            ("delete", "Delete"),
                            ("login", "Login"),
                            ("logout", "Logout"),
                            ("impersonate", "Impersonate"),
                            ("export", "Export"),
                            ("approve", "Approve"),
                            ("decline", "Decline"),
                        ],
                        db_index=True,
                        help_text="Type of action performed",
                        max_length=20,
                        verbose_name="Action",
                    ),
                ),
                (
                    "model_name",
                    models.CharField(
                        db_index=True,
                        help_text="Name of the model that was affected (e.g. 'Quote', 'Policy')",
                        max_length=100,
                        verbose_name="Model Name",
                    ),
                ),
                (
                    "object_id",
                    models.CharField(
                        blank=True,
                        db_index=True,
                        help_text="Primary key of the affected object",
                        max_length=100,
                        null=True,
                        verbose_name="Object ID",
                    ),
                ),
                (
                    "changes",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="JSON dict of changed fields: {field: {old: ..., new: ...}}",
                        verbose_name="Changes",
                    ),
                ),
                (
                    "ip_address",
                    models.GenericIPAddressField(
                        blank=True,
                        help_text="IP address of the request",
                        null=True,
                        verbose_name="IP Address",
                    ),
                ),
                (
                    "user_agent",
                    models.TextField(
                        blank=True,
                        help_text="Browser/client user agent string",
                        null=True,
                        verbose_name="User Agent",
                    ),
                ),
                (
                    "timestamp",
                    models.DateTimeField(
                        auto_now_add=True,
                        db_index=True,
                        help_text="When the action occurred",
                        verbose_name="Timestamp",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        help_text="User who performed the action",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="audit_log_entries",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="User",
                    ),
                ),
            ],
            options={
                "db_table": "audit_log_entries",
                "verbose_name": "Audit Log Entry",
                "verbose_name_plural": "Audit Log Entries",
                "ordering": ["-timestamp"],
            },
        ),
        migrations.AddIndex(
            model_name="auditlogentry",
            index=models.Index(
                fields=["user", "-timestamp"], name="audit_log_user_timestamp_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="auditlogentry",
            index=models.Index(
                fields=["model_name", "object_id"], name="audit_log_model_object_idx"
            ),
        ),
    ]
