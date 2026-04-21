"""
Migration: Add DunningRecord model for Stripe payment dunning flow.
"""

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("stripe_integration", "0001_add_refund_request"),
        ("policies", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="DunningRecord",
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
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "policy",
                    models.ForeignKey(
                        help_text="The policy with a failed payment.",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="dunning_records",
                        to="policies.policy",
                        verbose_name="Policy",
                    ),
                ),
                (
                    "attempt_count",
                    models.PositiveSmallIntegerField(
                        default=1,
                        help_text="Number of payment attempts made (including the initial failure).",
                        verbose_name="Attempt Count",
                    ),
                ),
                (
                    "first_failed_at",
                    models.DateTimeField(
                        default=django.utils.timezone.now,
                        help_text="When the initial payment failure occurred.",
                        verbose_name="First Failed At",
                    ),
                ),
                (
                    "next_retry_at",
                    models.DateTimeField(
                        blank=True,
                        help_text="Scheduled datetime for the next retry attempt.",
                        null=True,
                        verbose_name="Next Retry At",
                    ),
                ),
                (
                    "last_attempt_at",
                    models.DateTimeField(
                        blank=True,
                        help_text="When the most recent retry was attempted.",
                        null=True,
                        verbose_name="Last Attempt At",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("active", "Active — awaiting retry"),
                            ("resolved", "Resolved — payment recovered"),
                            (
                                "cancelled",
                                "Cancelled — policy cancelled after max retries",
                            ),
                        ],
                        db_index=True,
                        default="active",
                        max_length=15,
                        verbose_name="Status",
                    ),
                ),
                (
                    "stripe_invoice_id",
                    models.CharField(
                        blank=True,
                        help_text="The Stripe invoice that failed.",
                        max_length=255,
                        null=True,
                        verbose_name="Stripe Invoice ID",
                    ),
                ),
                (
                    "stripe_subscription_id",
                    models.CharField(
                        blank=True,
                        help_text="The Stripe subscription associated with this dunning record.",
                        max_length=255,
                        null=True,
                        verbose_name="Stripe Subscription ID",
                    ),
                ),
                (
                    "failure_reason",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="The last payment failure reason from Stripe.",
                        max_length=255,
                        verbose_name="Failure Reason",
                    ),
                ),
                (
                    "notes",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text="Internal notes about this dunning record.",
                        verbose_name="Notes",
                    ),
                ),
                (
                    "resolved_at",
                    models.DateTimeField(
                        blank=True,
                        help_text="When this dunning record was resolved.",
                        null=True,
                        verbose_name="Resolved At",
                    ),
                ),
            ],
            options={
                "verbose_name": "Dunning Record",
                "verbose_name_plural": "Dunning Records",
                "db_table": "dunning_records",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="dunningrecord",
            index=models.Index(
                fields=["status", "next_retry_at"], name="dunning_status_retry_idx"
            ),
        ),
    ]
