"""Initial migration for the hubspot_sync app.

Creates:
  - HubSpotSyncLog    (audit log of every sync attempt)
  - HubSpotSyncFailure (dead-letter for failed inbound webhook events)

This migration touches only tables owned by the hubspot_sync app; no
cross-app schema changes are performed.
"""

import django.db.models.deletion  # noqa: F401  (kept for future FK fields)
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="HubSpotSyncLog",
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
                    "direction",
                    models.CharField(
                        choices=[
                            ("push", "Django → HubSpot"),
                            ("pull", "HubSpot → Django"),
                        ],
                        max_length=4,
                        verbose_name="Direction",
                    ),
                ),
                (
                    "object_type",
                    models.CharField(
                        choices=[
                            ("contact", "Contact"),
                            ("company", "Company"),
                            ("deal", "Deal"),
                        ],
                        max_length=10,
                        verbose_name="HubSpot Object Type",
                    ),
                ),
                (
                    "hubspot_id",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=50,
                        verbose_name="HubSpot Object ID",
                    ),
                ),
                (
                    "django_model",
                    models.CharField(
                        help_text="e.g. 'Policy', 'User', 'Organization'",
                        max_length=50,
                        verbose_name="Django Model",
                    ),
                ),
                ("django_id", models.IntegerField(verbose_name="Django Object ID")),
                (
                    "action",
                    models.CharField(
                        help_text="e.g. 'create', 'update', 'associate', 'webhook'",
                        max_length=20,
                        verbose_name="Action",
                    ),
                ),
                (
                    "success",
                    models.BooleanField(
                        db_index=True, default=False, verbose_name="Success"
                    ),
                ),
                (
                    "error_message",
                    models.TextField(
                        blank=True, default="", verbose_name="Error Message"
                    ),
                ),
                (
                    "payload_summary",
                    models.JSONField(
                        blank=True,
                        help_text="Key properties sent or received (for debugging)",
                        null=True,
                        verbose_name="Payload Summary",
                    ),
                ),
            ],
            options={
                "verbose_name": "HubSpot Sync Log",
                "verbose_name_plural": "HubSpot Sync Logs",
                "db_table": "hubspot_sync_log",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="hubspotsynclog",
            index=models.Index(
                fields=["object_type", "-created_at"],
                name="hubspot_syn_object__f0b4d7_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="hubspotsynclog",
            index=models.Index(
                fields=["django_model", "django_id"],
                name="hubspot_syn_django__2f1a8e_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="hubspotsynclog",
            index=models.Index(
                fields=["success", "-created_at"], name="hubspot_syn_success_8c3d5b_idx"
            ),
        ),
        migrations.CreateModel(
            name="HubSpotSyncFailure",
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
                    "event_type",
                    models.CharField(
                        db_index=True,
                        help_text="HubSpot subscriptionType, e.g. 'deal.propertyChange'",
                        max_length=100,
                        verbose_name="Event Type",
                    ),
                ),
                (
                    "entity_id",
                    models.CharField(
                        db_index=True,
                        help_text="objectId from the HubSpot event payload",
                        max_length=64,
                        verbose_name="HubSpot Entity ID",
                    ),
                ),
                (
                    "payload",
                    models.JSONField(
                        help_text="Full event dict as received from HubSpot",
                        verbose_name="Raw Event Payload",
                    ),
                ),
                (
                    "error",
                    models.TextField(
                        help_text="Exception repr captured when the event failed",
                        verbose_name="Error",
                    ),
                ),
                (
                    "retry_count",
                    models.PositiveIntegerField(default=0, verbose_name="Retry Count"),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, db_index=True, verbose_name="Created At"
                    ),
                ),
                (
                    "last_retried_at",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="Last Retried At"
                    ),
                ),
                (
                    "resolved_at",
                    models.DateTimeField(
                        blank=True,
                        help_text="Set when a retry finally succeeds",
                        null=True,
                        verbose_name="Resolved At",
                    ),
                ),
            ],
            options={
                "verbose_name": "HubSpot Sync Failure",
                "verbose_name_plural": "HubSpot Sync Failures",
                "db_table": "hubspot_sync_failure",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="hubspotsyncfailure",
            index=models.Index(
                fields=["event_type", "-created_at"],
                name="hubspot_syn_event_t_a1b2c3_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="hubspotsyncfailure",
            index=models.Index(
                fields=["resolved_at", "-created_at"],
                name="hubspot_syn_resolve_d4e5f6_idx",
            ),
        ),
    ]
