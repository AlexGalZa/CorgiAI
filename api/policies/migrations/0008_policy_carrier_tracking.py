# Generated manually for carrier/brokerage tracking

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("policies", "0007_migrate_existing_policies"),
    ]

    operations = [
        migrations.AddField(
            model_name="policy",
            name="is_brokered",
            field=models.BooleanField(
                default=False,
                help_text="True if policy is brokered through external carrier",
                verbose_name="Is Brokered",
            ),
        ),
        migrations.AddField(
            model_name="policy",
            name="carrier",
            field=models.CharField(
                default="Technology Risk Retention Group, Inc.",
                help_text="Insurance carrier name (TechRRG for direct, external carrier if brokered)",
                max_length=255,
                verbose_name="Carrier",
            ),
        ),
    ]
