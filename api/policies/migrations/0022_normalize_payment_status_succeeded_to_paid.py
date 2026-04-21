from django.db import migrations


def normalize_payment_status(apps, schema_editor):
    Payment = apps.get_model("policies", "Payment")
    Payment.objects.filter(status="succeeded").update(status="paid")


def reverse_normalize_payment_status(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("policies", "0021_remove_producer_fields_add_cession"),
    ]

    operations = [
        migrations.RunPython(
            normalize_payment_status, reverse_normalize_payment_status
        ),
    ]
