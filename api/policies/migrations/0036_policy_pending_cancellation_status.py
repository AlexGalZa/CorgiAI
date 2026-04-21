from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("policies", "0035_policy_hubspot_deal_id"),
    ]

    operations = [
        migrations.AlterField(
            model_name="policy",
            name="status",
            field=models.CharField(
                choices=[
                    ("active", "Active"),
                    ("past_due", "Past Due"),
                    ("pending_cancellation", "Pending Cancellation"),
                    ("cancelled", "Cancelled"),
                    ("expired", "Expired"),
                    ("non_renewed", "Non-renewed"),
                ],
                db_index=True,
                default="active",
                max_length=20,
                verbose_name="Status",
            ),
        ),
    ]
