from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("policies", "0040_entityexpense"),
    ]

    operations = [
        migrations.AddField(
            model_name="policy",
            name="last_hubspot_sync_hash",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="",
                help_text=(
                    "sha256 of the last payload pushed to HubSpot. Used to "
                    "detect inbound-webhook echoes and skip redundant pushes."
                ),
                max_length=64,
                verbose_name="Last HubSpot Sync Hash",
            ),
        ),
        migrations.AddField(
            model_name="policy",
            name="last_reconciled_at",
            field=models.DateTimeField(
                blank=True,
                db_index=True,
                help_text=(
                    "Timestamp of the last Stripe reconciliation pass that "
                    "inspected this policy (regardless of drift outcome)."
                ),
                null=True,
                verbose_name="Last Reconciled At",
            ),
        ),
    ]
