from datetime import date
from dateutil.relativedelta import relativedelta
from django.db import migrations


def backfill_regulatory_fields(apps, schema_editor):
    Policy = apps.get_model("policies", "Policy")

    policies = Policy.objects.select_related(
        "quote__company__business_address",
    ).all()

    for policy in policies:
        company = policy.quote.company
        addr = company.business_address

        policy.insured_legal_name = company.entity_legal_name
        policy.insured_fein = company.federal_ein
        policy.mailing_address = {
            "street": addr.street_address,
            "suite": addr.suite,
            "city": addr.city,
            "state": addr.state,
            "zip": addr.zip,
        }
        policy.principal_state = addr.state
        policy.producer_name = "Corgi Insurance Services, Inc."

        if policy.billing_frequency == "annual":
            policy.paid_to_date = policy.expiration_date
        else:
            today = date.today()
            months_elapsed = (today.year - policy.effective_date.year) * 12 + (
                today.month - policy.effective_date.month
            )
            next_period = policy.effective_date + relativedelta(
                months=months_elapsed + 1
            )
            policy.paid_to_date = next_period

        policy.save(
            update_fields=[
                "insured_legal_name",
                "insured_fein",
                "mailing_address",
                "principal_state",
                "paid_to_date",
                "producer_name",
            ]
        )


class Migration(migrations.Migration):
    dependencies = [
        ("policies", "0018_add_policy_regulatory_fields"),
    ]

    operations = [
        migrations.RunPython(
            backfill_regulatory_fields,
            migrations.RunPython.noop,
        ),
    ]
