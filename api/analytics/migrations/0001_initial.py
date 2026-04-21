from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ScheduledReport",
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
                    "name",
                    models.CharField(
                        max_length=255,
                        verbose_name="Report Name",
                        help_text="Human-readable name for this scheduled report",
                    ),
                ),
                (
                    "report_type",
                    models.CharField(
                        choices=[
                            ("earned_premium", "Earned Premium Report"),
                            ("pipeline", "Pipeline Report"),
                            ("loss_ratio", "Loss Ratio Report"),
                            ("broker_performance", "Broker Performance Report"),
                            ("claims_summary", "Claims Summary Report"),
                        ],
                        db_index=True,
                        max_length=50,
                        verbose_name="Report Type",
                    ),
                ),
                (
                    "frequency",
                    models.CharField(
                        choices=[("weekly", "Weekly"), ("monthly", "Monthly")],
                        default="weekly",
                        max_length=10,
                        verbose_name="Frequency",
                    ),
                ),
                (
                    "recipients",
                    models.JSONField(
                        default=list,
                        verbose_name="Recipients",
                        help_text="JSON array of email addresses",
                    ),
                ),
                (
                    "last_sent_at",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="Last Sent At"
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        db_index=True,
                        default=True,
                        verbose_name="Is Active",
                        help_text="Whether this scheduled report is enabled",
                    ),
                ),
                (
                    "extra_filters",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        verbose_name="Extra Filters",
                        help_text="Optional filters passed to the report generator",
                    ),
                ),
            ],
            options={
                "verbose_name": "Scheduled Report",
                "verbose_name_plural": "Scheduled Reports",
                "ordering": ["name"],
            },
        ),
    ]
