import re
from django.db import migrations, models


def clean_stripe_invoice_ids(apps, schema_editor):
    """Remove _{policy_id} suffix from stripe_invoice_id and deduplicate."""
    Payment = apps.get_model("policies", "Payment")

    # Pattern to match _<number> suffix at the end
    suffix_pattern = re.compile(r"_\d+$")

    # First pass: clean up suffixes
    payments_to_update = []
    for payment in Payment.objects.all():
        original_id = payment.stripe_invoice_id
        cleaned_id = suffix_pattern.sub("", original_id)

        if cleaned_id != original_id:
            payment.stripe_invoice_id = cleaned_id
            payments_to_update.append(payment)

    # Bulk update the cleaned IDs
    if payments_to_update:
        Payment.objects.bulk_update(payments_to_update, ["stripe_invoice_id"])

    # Second pass: remove duplicates (keep the one with highest amount for each stripe_id + policy combo)
    seen = set()
    duplicates_to_delete = []

    for payment in Payment.objects.all().order_by("-amount"):
        key = (payment.stripe_invoice_id, payment.policy_id)
        if key in seen:
            duplicates_to_delete.append(payment.id)
        else:
            seen.add(key)

    if duplicates_to_delete:
        Payment.objects.filter(id__in=duplicates_to_delete).delete()


def reverse_clean(apps, schema_editor):
    """Cannot reverse the data cleanup - just pass."""
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("policies", "0012_alter_policy_premium"),
    ]

    operations = [
        # Step 1: Remove the unique constraint on stripe_invoice_id
        migrations.AlterField(
            model_name="payment",
            name="stripe_invoice_id",
            field=models.CharField(
                max_length=255,
                verbose_name="Stripe Invoice ID",
                help_text="Real Stripe payment intent or invoice ID",
            ),
        ),
        # Step 2: Clean up data (remove suffixes and deduplicate)
        migrations.RunPython(clean_stripe_invoice_ids, reverse_clean),
    ]
