from decimal import Decimal
from django.db import migrations


def fix_allocation_percent_scale(apps, schema_editor):
    StateAllocation = apps.get_model("policies", "StateAllocation")

    for alloc in StateAllocation.objects.all():
        if alloc.allocation_percent > Decimal("1"):
            alloc.allocation_percent = (
                alloc.allocation_percent / Decimal("100")
            ).quantize(Decimal("0.0001"))
            alloc.save()


class Migration(migrations.Migration):
    dependencies = [
        ("policies", "0016_merge_and_add_regulatory_fields"),
    ]

    operations = [
        migrations.RunPython(fix_allocation_percent_scale, migrations.RunPython.noop),
    ]
