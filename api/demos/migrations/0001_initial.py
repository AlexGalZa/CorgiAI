import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("producers", "0004_commissionpayout_reversal_and_period"),
    ]

    operations = [
        migrations.CreateModel(
            name="Demo",
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
                    "customer_email",
                    models.EmailField(
                        help_text="Email of the prospective customer booking the demo",
                        max_length=254,
                        verbose_name="Customer Email",
                    ),
                ),
                (
                    "customer_name",
                    models.CharField(
                        help_text="Full name of the prospective customer",
                        max_length=255,
                        verbose_name="Customer Name",
                    ),
                ),
                (
                    "scheduled_for",
                    models.DateTimeField(
                        help_text="Start time of the demo", verbose_name="Scheduled For"
                    ),
                ),
                (
                    "duration_minutes",
                    models.IntegerField(
                        default=30,
                        help_text="Expected length of the demo in minutes",
                        verbose_name="Duration (minutes)",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("scheduled", "Scheduled"),
                            ("held", "Held"),
                            ("no_show", "No Show"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="scheduled",
                        max_length=20,
                        verbose_name="Status",
                    ),
                ),
                (
                    "join_url",
                    models.TextField(
                        blank=True,
                        help_text="Video conference join link",
                        verbose_name="Join URL",
                    ),
                ),
                (
                    "recording_url",
                    models.TextField(
                        blank=True,
                        help_text="Recording link populated after the demo",
                        verbose_name="Recording URL",
                    ),
                ),
                (
                    "notes",
                    models.TextField(
                        blank=True,
                        help_text="AE notes captured after the demo",
                        verbose_name="Notes",
                    ),
                ),
                (
                    "ae",
                    models.ForeignKey(
                        help_text="The AE assigned to host this demo",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="demos",
                        to="producers.producer",
                        verbose_name="Account Executive",
                    ),
                ),
            ],
            options={
                "verbose_name": "Demo",
                "verbose_name_plural": "Demos",
                "db_table": "demos",
                "ordering": ["-scheduled_for"],
            },
        ),
        migrations.AddIndex(
            model_name="demo",
            index=models.Index(
                fields=["ae", "scheduled_for"], name="demos_ae_sched_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="demo",
            index=models.Index(
                fields=["status", "scheduled_for"], name="demos_status_sched_idx"
            ),
        ),
    ]
