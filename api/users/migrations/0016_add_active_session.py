from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0015_add_account_lockout_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="ActiveSession",
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
                    "session_key",
                    models.CharField(
                        db_index=True,
                        help_text="Opaque identifier for this session (JWT jti or random token)",
                        max_length=64,
                        unique=True,
                        verbose_name="Session Key",
                    ),
                ),
                (
                    "ip_address",
                    models.GenericIPAddressField(
                        blank=True, null=True, verbose_name="IP Address"
                    ),
                ),
                (
                    "user_agent",
                    models.TextField(blank=True, default="", verbose_name="User Agent"),
                ),
                (
                    "last_activity",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="Timestamp of the most recent request on this session",
                        verbose_name="Last Activity",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        db_index=True,
                        default=True,
                        help_text="False if the session was explicitly revoked or expired",
                        verbose_name="Is Active",
                    ),
                ),
                (
                    "revoked_at",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="Revoked At"
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="active_sessions",
                        to="users.user",
                        verbose_name="User",
                    ),
                ),
            ],
            options={
                "verbose_name": "Active Session",
                "verbose_name_plural": "Active Sessions",
                "db_table": "active_sessions",
                "ordering": ["-last_activity"],
            },
        ),
        migrations.AddIndex(
            model_name="activesession",
            index=models.Index(
                fields=["user", "is_active"], name="active_sess_user_active_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="activesession",
            index=models.Index(fields=["session_key"], name="active_sess_key_idx"),
        ),
    ]
