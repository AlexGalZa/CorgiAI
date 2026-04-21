# Generated for Trello 3.6 — Commission cancellations + monthly cadence

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("producers", "0003_commissionpayout"),
    ]

    operations = [
        migrations.AlterField(
            model_name="commissionpayout",
            name="status",
            field=models.CharField(
                choices=[
                    ("calculated", "Calculated"),
                    ("approved", "Approved"),
                    ("paid", "Paid"),
                    ("reversed", "Reversed"),
                ],
                db_index=True,
                default="calculated",
                max_length=20,
                verbose_name="Status",
            ),
        ),
        migrations.AddField(
            model_name="commissionpayout",
            name="reversal_reason",
            field=models.CharField(
                blank=True,
                help_text="Populated when status='reversed' (e.g., 'policy_cancelled')",
                max_length=255,
                verbose_name="Reversal Reason",
            ),
        ),
        migrations.AddField(
            model_name="commissionpayout",
            name="reversed_at",
            field=models.DateTimeField(
                blank=True,
                help_text="Timestamp when this payout was reversed",
                null=True,
                verbose_name="Reversed At",
            ),
        ),
        migrations.AddField(
            model_name="commissionpayout",
            name="period_start",
            field=models.DateField(
                blank=True,
                help_text="Start of the accrual period this payout covers (for monthly payouts)",
                null=True,
                verbose_name="Period Start",
            ),
        ),
        migrations.AddField(
            model_name="commissionpayout",
            name="period_end",
            field=models.DateField(
                blank=True,
                help_text="End of the accrual period this payout covers (for monthly payouts)",
                null=True,
                verbose_name="Period End",
            ),
        ),
    ]
