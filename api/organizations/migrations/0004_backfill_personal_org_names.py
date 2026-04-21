from django.db import migrations


def backfill_personal_org_names(apps, schema_editor):
    Organization = apps.get_model("organizations", "Organization")
    for org in Organization.objects.filter(is_personal=True).select_related("owner"):
        company_name = (org.owner.company_name or "").strip()
        org.name = company_name if company_name else "Personal"
        org.save(update_fields=["name"])


def reverse_backfill(apps, schema_editor):
    Organization = apps.get_model("organizations", "Organization")
    Organization.objects.filter(is_personal=True).update(name="Personal")


class Migration(migrations.Migration):
    dependencies = [
        ("organizations", "0003_create_personal_orgs"),
    ]

    operations = [
        migrations.RunPython(backfill_personal_org_names, reverse_backfill),
    ]
