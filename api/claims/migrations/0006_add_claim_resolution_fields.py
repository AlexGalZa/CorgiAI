"""Add incident_date, loss_amount_estimate, resolution_date, resolution_notes to Claim."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("claims", "0005_claim_organization_not_null"),
    ]

    operations = [
        migrations.AddField(
            model_name="claim",
            name="incident_date",
            field=models.DateField(
                blank=True,
                help_text="Date when the incident occurred",
                null=True,
                verbose_name="Incident Date",
            ),
        ),
        migrations.AddField(
            model_name="claim",
            name="loss_amount_estimate",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Estimated total loss amount",
                max_digits=15,
                null=True,
                verbose_name="Loss Amount Estimate",
            ),
        ),
        migrations.AddField(
            model_name="claim",
            name="resolution_date",
            field=models.DateField(
                blank=True,
                help_text="Date when the claim was resolved",
                null=True,
                verbose_name="Resolution Date",
            ),
        ),
        migrations.AddField(
            model_name="claim",
            name="resolution_notes",
            field=models.TextField(
                blank=True,
                help_text="Notes about the claim resolution",
                null=True,
                verbose_name="Resolution Notes",
            ),
        ),
    ]
