"""
Initial migration for webhook delivery system.
Creates WebhookEndpoint and WebhookDelivery tables.
"""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("organizations", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="WebhookEndpoint",
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
                    models.DateTimeField(auto_now_add=True, verbose_name="Created At"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Updated At"),
                ),
                ("url", models.URLField(max_length=500, verbose_name="Endpoint URL")),
                (
                    "secret",
                    models.CharField(max_length=255, verbose_name="Signing Secret"),
                ),
                (
                    "subscribed_events",
                    models.JSONField(default=list, verbose_name="Subscribed Events"),
                ),
                ("is_active", models.BooleanField(default=True, verbose_name="Active")),
                (
                    "description",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=255,
                        verbose_name="Description",
                    ),
                ),
                (
                    "org",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="webhook_endpoints",
                        to="organizations.organization",
                        verbose_name="Organization",
                    ),
                ),
            ],
            options={
                "verbose_name": "Webhook Endpoint",
                "verbose_name_plural": "Webhook Endpoints",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="WebhookDelivery",
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
                    models.DateTimeField(auto_now_add=True, verbose_name="Created At"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Updated At"),
                ),
                (
                    "endpoint",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="deliveries",
                        to="webhooks.webhookendpoint",
                        verbose_name="Endpoint",
                    ),
                ),
                (
                    "event_type",
                    models.CharField(
                        max_length=100,
                        verbose_name="Event Type",
                        choices=[
                            ("quote.created", "quote.created"),
                            ("policy.bound", "policy.bound"),
                            ("claim.filed", "claim.filed"),
                            ("payment.failed", "payment.failed"),
                            ("policy.cancelled", "policy.cancelled"),
                            ("policy.renewed", "policy.renewed"),
                        ],
                    ),
                ),
                ("payload", models.JSONField(verbose_name="Payload")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("delivered", "Delivered"),
                            ("failed", "Failed"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=20,
                        verbose_name="Status",
                    ),
                ),
                (
                    "attempts",
                    models.PositiveSmallIntegerField(
                        default=0, verbose_name="Attempts"
                    ),
                ),
                (
                    "last_attempt_at",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="Last Attempt At"
                    ),
                ),
                (
                    "response_status",
                    models.IntegerField(
                        blank=True, null=True, verbose_name="HTTP Response Status"
                    ),
                ),
                (
                    "response_body",
                    models.TextField(
                        blank=True, default="", verbose_name="Response Body"
                    ),
                ),
                (
                    "error_message",
                    models.TextField(
                        blank=True, default="", verbose_name="Error Message"
                    ),
                ),
            ],
            options={
                "verbose_name": "Webhook Delivery",
                "verbose_name_plural": "Webhook Deliveries",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="webhookdelivery",
            index=models.Index(
                fields=["status", "created_at"], name="webhookdeli_status_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="webhookdelivery",
            index=models.Index(
                fields=["endpoint", "event_type"], name="webhookdeli_endpoint_event_idx"
            ),
        ),
    ]
