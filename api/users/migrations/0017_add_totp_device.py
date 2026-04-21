from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0016_add_active_session"),
    ]

    operations = [
        migrations.CreateModel(
            name="TOTPDevice",
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
                    "secret_key",
                    models.CharField(
                        help_text="Base32-encoded TOTP secret — never expose to clients after setup",
                        max_length=64,
                        verbose_name="Secret Key",
                    ),
                ),
                (
                    "is_verified",
                    models.BooleanField(
                        db_index=True,
                        default=False,
                        help_text="True after the user has successfully confirmed the device with their first valid code",
                        verbose_name="Is Verified",
                    ),
                ),
                (
                    "last_used_at",
                    models.DateTimeField(
                        blank=True,
                        help_text="When the TOTP was last successfully validated",
                        null=True,
                        verbose_name="Last Used At",
                    ),
                ),
                (
                    "backup_codes",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="List of single-use hashed backup codes",
                        verbose_name="Backup Codes",
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="totp_device",
                        to="users.user",
                        verbose_name="User",
                    ),
                ),
            ],
            options={
                "verbose_name": "TOTP Device",
                "verbose_name_plural": "TOTP Devices",
                "db_table": "totp_devices",
            },
        ),
    ]
