"""Seed migration: populate known carriers from the codebase."""

from django.db import migrations


KNOWN_CARRIERS = [
    {
        "name": "Limit",
        "am_best_rating": "",
        "appetite_description": "Primary carrier for Corgi instant-quote products (CGL, D&O, Tech E&O, Cyber, etc.)",
        "commission_rates": {},
        "contact_name": "",
        "contact_email": "",
        "contact_phone": "",
        "status": "active",
    },
    {
        "name": "AM Trust Financial Services",
        "am_best_rating": "A-",
        "appetite_description": "Admitted commercial lines carrier. Used for select brokered coverages.",
        "commission_rates": {},
        "contact_name": "",
        "contact_email": "",
        "contact_phone": "",
        "status": "active",
    },
    {
        "name": "Coterie Insurance",
        "am_best_rating": "",
        "appetite_description": "MGA/carrier for small business BOP and commercial lines.",
        "commission_rates": {},
        "contact_name": "",
        "contact_email": "",
        "contact_phone": "",
        "status": "active",
    },
    {
        "name": "NTIC (National Technology Insurance Company)",
        "am_best_rating": "",
        "appetite_description": "Technology E&O and Cyber specialty carrier.",
        "commission_rates": {},
        "contact_name": "",
        "contact_email": "",
        "contact_phone": "",
        "status": "active",
    },
    {
        "name": "Technology Risk Retention Group, Inc.",
        "am_best_rating": "",
        "appetite_description": "Primary RRG carrier for Corgi risk retention group policies. Tech E&O, Cyber, D&O.",
        "commission_rates": {},
        "contact_name": "",
        "contact_email": "",
        "contact_phone": "",
        "status": "active",
    },
    {
        "name": "RT Specialty",
        "am_best_rating": "",
        "appetite_description": "Wholesale broker / E&S carrier for complex and high-limit risks.",
        "commission_rates": {},
        "contact_name": "",
        "contact_email": "",
        "contact_phone": "",
        "status": "active",
    },
    {
        "name": "Nautilus Insurance Group",
        "am_best_rating": "A",
        "appetite_description": "E&S (excess and surplus) carrier for non-standard commercial risks.",
        "commission_rates": {},
        "contact_name": "",
        "contact_email": "",
        "contact_phone": "",
        "status": "active",
    },
]


def seed_carriers(apps, schema_editor):
    Carrier = apps.get_model("carriers", "Carrier")
    for data in KNOWN_CARRIERS:
        Carrier.objects.get_or_create(name=data["name"], defaults=data)


def remove_seeded_carriers(apps, schema_editor):
    Carrier = apps.get_model("carriers", "Carrier")
    names = [c["name"] for c in KNOWN_CARRIERS]
    Carrier.objects.filter(name__in=names).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("carriers", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_carriers, remove_seeded_carriers),
    ]
