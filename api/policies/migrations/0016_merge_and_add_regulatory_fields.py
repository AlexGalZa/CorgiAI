from decimal import Decimal
from django.db import migrations, models


def backfill_regulatory_fields(apps, schema_editor):
    PolicyTransaction = apps.get_model("policies", "PolicyTransaction")
    StateAllocation = apps.get_model("policies", "StateAllocation")

    STATE_TAX_RATES = {
        "AL": 1.035,
        "AK": 1.027,
        "AZ": 1.03,
        "AR": 1.025,
        "CA": 1.023,
        "CO": 1.03,
        "CT": 1.0175,
        "DE": 1.02,
        "DC": 1.017,
        "FL": 1.0175,
        "GA": 1.0275,
        "HI": 1.0435,
        "ID": 1.025,
        "IL": 1.005,
        "IN": 1.025,
        "IA": 1.02,
        "KS": 1.02,
        "KY": 1.02,
        "LA": 1.0475,
        "ME": 1.02,
        "MD": 1.02,
        "MA": 1.02,
        "MI": 1.0125,
        "MN": 1.02,
        "MS": 1.03,
        "MO": 1.02,
        "MT": 1.0275,
        "NE": 1.01,
        "NV": 1.035,
        "NH": 1.02,
        "NJ": 1.021,
        "NM": 1.0303,
        "NY": 1.0185,
        "NC": 1.019,
        "ND": 1.0175,
        "OH": 1.014,
        "OK": 1.0225,
        "OR": 1.0215,
        "PA": 1.02,
        "RI": 1.02,
        "SC": 1.0175,
        "SD": 1.025,
        "TN": 1.0225,
        "TX": 1.0185,
        "UT": 1.0225,
        "VT": 1.02,
        "VA": 1.0225,
        "WA": 1.02,
        "WV": 1.03,
        "WI": 1.02,
        "WY": 1.025,
    }

    ADMIN_FEE_RATE = Decimal("0.22")
    ADMIN_FEE_RECIPIENT = "Corgi Administration, LLC"
    COLLECTOR_ENTITY = "Corgi Insurance Services, Inc."

    for txn in PolicyTransaction.objects.select_related(
        "policy__quote__company__business_address"
    ).all():
        policy = txn.policy
        is_brokered = policy.is_brokered
        state = policy.quote.company.business_address.state

        txn.taxes_assessments_delta = (
            txn.tax_amount if txn.tax_amount and txn.tax_amount > 0 else None
        )
        txn.total_billed_delta = policy.premium
        txn.collected_amount = policy.premium
        txn.collected_date = txn.accounting_date
        txn.collector_entity = COLLECTOR_ENTITY

        if not is_brokered:
            txn.admin_fee_rate = ADMIN_FEE_RATE
            txn.admin_fee_amount = (
                txn.gross_written_premium * ADMIN_FEE_RATE
            ).quantize(Decimal("0.01"))
            txn.admin_fee_recipient_entity = ADMIN_FEE_RECIPIENT

        txn.save()

    for alloc in StateAllocation.objects.select_related("transaction__policy").all():
        policy = alloc.transaction.policy
        is_brokered = policy.is_brokered
        state = alloc.state

        if alloc.allocation_percent > Decimal("1"):
            alloc.allocation_percent = (
                alloc.allocation_percent / Decimal("100")
            ).quantize(Decimal("0.0001"))

        if not is_brokered:
            tax_rate = Decimal(str(STATE_TAX_RATES.get(state, 1.0)))
            if tax_rate > 1:
                alloc.allocated_taxes = (
                    alloc.allocated_premium * (tax_rate - 1)
                ).quantize(Decimal("0.01"))

        alloc.save()


class Migration(migrations.Migration):
    dependencies = [
        ("policies", "0014_backfill_stripe_customer_id"),
        ("policies", "0015_add_tax_rate_to_transaction"),
    ]

    operations = [
        migrations.AddField(
            model_name="policytransaction",
            name="policy_fee_delta",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=15,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="policytransaction",
            name="membership_fee_delta",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=15,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="policytransaction",
            name="taxes_assessments_delta",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=15,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="policytransaction",
            name="total_billed_delta",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=15,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="policytransaction",
            name="collected_amount",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=15,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="policytransaction",
            name="collected_date",
            field=models.DateField(
                blank=True,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="policytransaction",
            name="collector_entity",
            field=models.CharField(
                blank=True,
                max_length=100,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="policytransaction",
            name="admin_fee_rate",
            field=models.DecimalField(
                blank=True,
                decimal_places=4,
                max_digits=5,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="policytransaction",
            name="admin_fee_amount",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=15,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="policytransaction",
            name="admin_fee_recipient_entity",
            field=models.CharField(
                blank=True,
                max_length=100,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="policytransaction",
            name="commission_rate",
            field=models.DecimalField(
                blank=True,
                decimal_places=4,
                max_digits=5,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="policytransaction",
            name="commission_amount",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=15,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="stateallocation",
            name="allocated_policy_fee",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=15,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="stateallocation",
            name="allocated_membership_fee",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=15,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="stateallocation",
            name="allocated_taxes",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=15,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="stateallocation",
            name="allocation_percent",
            field=models.DecimalField(
                decimal_places=4,
                max_digits=7,
            ),
        ),
        migrations.RunPython(backfill_regulatory_fields, migrations.RunPython.noop),
    ]
