# C4: 2FA code delivery audit log for email/SMS retry + fallback.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0022_add_read_only_role"),
    ]

    operations = [
        migrations.CreateModel(
            name="TwoFactorDeliveryLog",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "channel",
                    models.CharField(
                        choices=[("email", "Email"), ("sms", "SMS")], max_length=10
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("sent", "Sent"),
                            ("failed", "Failed"),
                            ("retried", "Retried"),
                            ("fallback", "Fallback"),
                            ("skipped", "Skipped"),
                        ],
                        max_length=12,
                    ),
                ),
                (
                    "provider_msg_id",
                    models.CharField(blank=True, default="", max_length=255),
                ),
                ("error", models.TextField(blank=True, default="")),
                (
                    "user",
                    models.ForeignKey(
                        null=True,
                        blank=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="two_factor_delivery_logs",
                        to="users.user",
                    ),
                ),
            ],
            options={
                "verbose_name": "Two-Factor Delivery Log",
                "verbose_name_plural": "Two-Factor Delivery Logs",
                "db_table": "two_factor_delivery_logs",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="twofactordeliverylog",
            index=models.Index(
                fields=["user", "-created_at"], name="two_factor__user_id_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="twofactordeliverylog",
            index=models.Index(
                fields=["status", "-created_at"], name="two_factor__status_idx"
            ),
        ),
    ]
