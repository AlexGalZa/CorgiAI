from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("common", "0004_add_compliance_deadline"),
        ("users", "0015_add_account_lockout_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="DataAccessLog",
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
                    "model_name",
                    models.CharField(
                        db_index=True,
                        help_text="Name of the model accessed (e.g. 'Quote', 'Policy')",
                        max_length=100,
                        verbose_name="Model Name",
                    ),
                ),
                (
                    "object_id",
                    models.CharField(
                        blank=True,
                        db_index=True,
                        help_text="Primary key of the accessed object",
                        max_length=100,
                        null=True,
                        verbose_name="Object ID",
                    ),
                ),
                (
                    "action",
                    models.CharField(
                        choices=[
                            ("view", "View"),
                            ("export", "Export"),
                            ("modify", "Modify"),
                            ("delete", "Delete"),
                        ],
                        db_index=True,
                        help_text="Type of data access",
                        max_length=10,
                        verbose_name="Action",
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
                    "extra",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Additional context (endpoint, query params, etc.)",
                        verbose_name="Extra",
                    ),
                ),
                (
                    "timestamp",
                    models.DateTimeField(
                        auto_now_add=True,
                        db_index=True,
                        help_text="When the access occurred",
                        verbose_name="Timestamp",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        help_text="User who accessed the data",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="data_access_logs",
                        to="users.user",
                        verbose_name="User",
                    ),
                ),
            ],
            options={
                "verbose_name": "Data Access Log",
                "verbose_name_plural": "Data Access Logs",
                "db_table": "data_access_logs",
                "ordering": ["-timestamp"],
            },
        ),
        migrations.AddIndex(
            model_name="dataaccesslog",
            index=models.Index(
                fields=["user", "-timestamp"], name="data_access_user_ts_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="dataaccesslog",
            index=models.Index(
                fields=["model_name", "object_id"], name="data_access_model_obj_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="dataaccesslog",
            index=models.Index(
                fields=["action", "-timestamp"], name="data_access_action_ts_idx"
            ),
        ),
    ]
