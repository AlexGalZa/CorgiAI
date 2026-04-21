"""Add assigned_to, priority, notes, external_quote_number to BrokeredQuoteRequest."""

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("brokered", "0006_rename_skyvern_run_id_to_run_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="brokeredquoterequest",
            name="assigned_to",
            field=models.ForeignKey(
                blank=True,
                help_text="Underwriter assigned to handle this brokered request",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="assigned_brokered_requests",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Assigned To",
            ),
        ),
        migrations.AddField(
            model_name="brokeredquoterequest",
            name="priority",
            field=models.CharField(
                choices=[
                    ("low", "Low"),
                    ("medium", "Medium"),
                    ("high", "High"),
                    ("urgent", "Urgent"),
                ],
                db_index=True,
                default="medium",
                help_text="Priority level for underwriter review",
                max_length=10,
                verbose_name="Priority",
            ),
        ),
        migrations.AddField(
            model_name="brokeredquoterequest",
            name="notes",
            field=models.TextField(
                blank=True,
                help_text="Internal notes about this brokered request",
                null=True,
                verbose_name="Notes",
            ),
        ),
        migrations.AddField(
            model_name="brokeredquoterequest",
            name="external_quote_number",
            field=models.CharField(
                blank=True,
                help_text="Quote number from the external carrier",
                max_length=100,
                null=True,
                verbose_name="External Quote Number",
            ),
        ),
    ]
