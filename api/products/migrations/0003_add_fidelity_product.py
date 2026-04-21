from django.db import migrations


FIDELITY = {
    "coverage_type": "custom-fidelity",
    "display_name": "Fidelity Bond",
    "description": "Protects the business against loss from dishonest acts by employees handling money or securities.",
    "is_active": True,
    "min_limit": None,
    "max_limit": None,
    "available_retentions": [],
    "rating_tier": "tier2_brokered_form",
    "requires_review": True,
}


def add_fidelity(apps, schema_editor):
    ProductConfiguration = apps.get_model("products", "ProductConfiguration")
    ProductConfiguration.objects.get_or_create(
        coverage_type=FIDELITY["coverage_type"],
        defaults=FIDELITY,
    )


def remove_fidelity(apps, schema_editor):
    ProductConfiguration = apps.get_model("products", "ProductConfiguration")
    ProductConfiguration.objects.filter(
        coverage_type=FIDELITY["coverage_type"]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("products", "0002_seed_product_configurations"),
    ]

    operations = [
        migrations.RunPython(add_fidelity, reverse_code=remove_fidelity),
    ]
