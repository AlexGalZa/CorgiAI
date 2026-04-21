from django.db import migrations


def update_driver_band_forward(apps, schema_editor):
    """Update driver_band from '3_5' to '0_5' in HNOA coverage data."""
    Quote = apps.get_model("quotes", "Quote")

    # Update coverage_data
    quotes_with_hnoa = Quote.objects.filter(
        coverage_data__has_key="hired-and-non-owned-auto"
    )

    updated_count = 0
    for quote in quotes_with_hnoa:
        changed = False

        # Update coverage_data
        if (
            quote.coverage_data.get("hired-and-non-owned-auto", {}).get("driver_band")
            == "3_5"
        ):
            quote.coverage_data["hired-and-non-owned-auto"]["driver_band"] = "0_5"
            changed = True

        # Update form_data_snapshot if it exists
        if quote.form_data_snapshot:
            # Check hired_non_owned_auto in form_data_snapshot
            if (
                quote.form_data_snapshot.get("hired_non_owned_auto", {}).get(
                    "driver_band"
                )
                == "3_5"
            ):
                quote.form_data_snapshot["hired_non_owned_auto"]["driver_band"] = "0_5"
                changed = True

            # Check limits_retentions snapshot
            if quote.form_data_snapshot.get("limits_retentions", {}).get(
                "hired-and-non-owned-auto"
            ):
                # This is just limits/retentions, no driver_band here
                pass

        if changed:
            quote.save(update_fields=["coverage_data", "form_data_snapshot"])
            updated_count += 1

    print(f"Updated {updated_count} quotes with driver_band 3_5 -> 0_5")


def update_driver_band_reverse(apps, schema_editor):
    """Reverse: Update driver_band from '0_5' back to '3_5'."""
    Quote = apps.get_model("quotes", "Quote")

    quotes_with_hnoa = Quote.objects.filter(
        coverage_data__has_key="hired-and-non-owned-auto"
    )

    updated_count = 0
    for quote in quotes_with_hnoa:
        changed = False

        if (
            quote.coverage_data.get("hired-and-non-owned-auto", {}).get("driver_band")
            == "0_5"
        ):
            quote.coverage_data["hired-and-non-owned-auto"]["driver_band"] = "3_5"
            changed = True

        if quote.form_data_snapshot:
            if (
                quote.form_data_snapshot.get("hired_non_owned_auto", {}).get(
                    "driver_band"
                )
                == "0_5"
            ):
                quote.form_data_snapshot["hired_non_owned_auto"]["driver_band"] = "3_5"
                changed = True

        if changed:
            quote.save(update_fields=["coverage_data", "form_data_snapshot"])
            updated_count += 1

    print(f"Reverted {updated_count} quotes with driver_band 0_5 -> 3_5")


class Migration(migrations.Migration):
    dependencies = [
        ("quotes", "0022_add_is_technology_company"),
    ]

    operations = [
        migrations.RunPython(update_driver_band_forward, update_driver_band_reverse),
    ]
