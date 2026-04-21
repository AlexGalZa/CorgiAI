from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("policies", "0036_policy_pending_cancellation_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="policytransaction",
            name="stripe_payout_id",
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text=(
                    "ID of the Stripe payout that settled the charge for this "
                    "transaction. Populated from the charge.succeeded webhook or "
                    "via the backfill_stripe_payouts management command. Used by "
                    "finance to trace money from a policy to the bank deposit."
                ),
                max_length=100,
                null=True,
                verbose_name="Stripe Payout ID",
            ),
        ),
    ]
