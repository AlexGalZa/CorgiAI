# Generated for H20 — Email Response Notification + 7h Auto-Delete.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("emails", "0001_add_email_log"),
        ("policies", "0036_policy_pending_cancellation_status"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="EmailContext",
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
                    "thread_id",
                    models.CharField(
                        db_index=True,
                        help_text="Provider-supplied thread / conversation identifier",
                        max_length=255,
                        unique=True,
                        verbose_name="Thread ID",
                    ),
                ),
                (
                    "last_messages",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text='Rolling array of recent messages, capped at 5. Each element: {"from": str, "snippet": str, "received_at": iso8601}.',
                        verbose_name="Last Messages",
                    ),
                ),
                (
                    "expires_at",
                    models.DateTimeField(
                        db_index=True,
                        help_text="Row is pruned after this time (created_at + 7h).",
                        verbose_name="Expires At",
                    ),
                ),
                (
                    "policy",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="email_contexts",
                        to="policies.policy",
                        verbose_name="Related Policy",
                    ),
                ),
                (
                    "salesperson",
                    models.ForeignKey(
                        blank=True,
                        help_text="Staff user owning this thread (receives reply notifications)",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="email_contexts",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Salesperson",
                    ),
                ),
            ],
            options={
                "verbose_name": "Email Context",
                "verbose_name_plural": "Email Contexts",
                "db_table": "email_contexts",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["expires_at"], name="email_ctx_expires_idx"),
                    models.Index(
                        fields=["salesperson", "expires_at"],
                        name="email_ctx_sp_exp_idx",
                    ),
                ],
            },
        ),
    ]
