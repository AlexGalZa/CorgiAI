from decimal import Decimal

from django.db import migrations, models


def backfill_tax_rate(apps, schema_editor):
    from rating.constants import STATE_TAX_RATES

    PolicyTransaction = apps.get_model("policies", "PolicyTransaction")
    StateAllocation = apps.get_model("policies", "StateAllocation")

    transactions = PolicyTransaction.objects.all()

    for transaction in transactions:
        allocation = StateAllocation.objects.filter(transaction=transaction).first()
        if allocation:
            state = allocation.state
            tax_rate = Decimal(str(STATE_TAX_RATES.get(state, 1.0)))
            transaction.tax_rate = tax_rate
            transaction.save(update_fields=["tax_rate"])


def reverse_backfill(apps, schema_editor):
    PolicyTransaction = apps.get_model("policies", "PolicyTransaction")
    PolicyTransaction.objects.update(tax_rate=None)


class Migration(migrations.Migration):
    dependencies = [
        ("policies", "0014_add_policy_transaction_and_state_allocation"),
    ]

    operations = [
        migrations.AddField(
            model_name="policytransaction",
            name="tax_rate",
            field=models.DecimalField(
                blank=True,
                decimal_places=4,
                max_digits=5,
                null=True,
            ),
        ),
        migrations.RunPython(backfill_tax_rate, reverse_backfill),
    ]
