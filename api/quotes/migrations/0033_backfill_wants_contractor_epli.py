"""
Data migration to backfill wants_contractor_epli for existing quotes.

For quotes where:
- employment_practices_liability.uses_contractors is True
- employment_practices_liability.contractor_count exists and > 0

We set wants_contractor_epli = True (assuming they wanted coverage since they provided count).
"""

from django.db import migrations


def backfill_wants_contractor_epli(apps, schema_editor):
    Quote = apps.get_model("quotes", "Quote")

    updated_count = 0
    for quote in Quote.objects.all():
        coverage_data = quote.coverage_data or {}
        epl_data = coverage_data.get("employment_practices_liability", {})

        # Check if this quote has contractors but no wants_contractor_epli set
        uses_contractors = epl_data.get("uses_contractors")
        contractor_count = epl_data.get("contractor_count")
        wants_contractor_epli = epl_data.get("wants_contractor_epli")

        if (
            uses_contractors is True
            and contractor_count is not None
            and contractor_count > 0
            and wants_contractor_epli is None
        ):
            # Set wants_contractor_epli to True since they provided contractor count
            epl_data["wants_contractor_epli"] = True
            coverage_data["employment_practices_liability"] = epl_data
            quote.coverage_data = coverage_data
            quote.save(update_fields=["coverage_data"])
            updated_count += 1

    if updated_count > 0:
        print(f"\n  Updated {updated_count} quotes with wants_contractor_epli=True")


def reverse_backfill(apps, schema_editor):
    # Remove wants_contractor_epli from all quotes (reverse migration)
    Quote = apps.get_model("quotes", "Quote")

    for quote in Quote.objects.all():
        coverage_data = quote.coverage_data or {}
        epl_data = coverage_data.get("employment_practices_liability", {})

        if "wants_contractor_epli" in epl_data:
            del epl_data["wants_contractor_epli"]
            coverage_data["employment_practices_liability"] = epl_data
            quote.coverage_data = coverage_data
            quote.save(update_fields=["coverage_data"])


class Migration(migrations.Migration):
    dependencies = [
        ("quotes", "0032_add_parent_quote"),
    ]

    operations = [
        migrations.RunPython(backfill_wants_contractor_epli, reverse_backfill),
    ]
