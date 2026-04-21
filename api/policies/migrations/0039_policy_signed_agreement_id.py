from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("policies", "0038_revenuesplit"),
    ]

    operations = [
        migrations.AddField(
            model_name="policy",
            name="signed_agreement_id",
            field=models.CharField(
                blank=True,
                help_text=(
                    "Reference ID of the signed membership agreement document "
                    "(e.g. DocuSign envelope ID). Required for Crime and Umbrella "
                    "products. Populated by the membership agreement flow (H5)."
                ),
                max_length=100,
                null=True,
                verbose_name="Signed Membership Agreement ID",
            ),
        ),
    ]
