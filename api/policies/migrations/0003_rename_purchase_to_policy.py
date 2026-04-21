# Generated manually for app rename from purchases to policies

import secrets
import string

import django.db.models.deletion
from django.db import migrations, models


def generate_short_id(length=8):
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def populate_policy_numbers(apps, schema_editor):
    """Populate policy_number for existing records."""
    Policy = apps.get_model("policies", "Policy")
    for policy in Policy.objects.all():
        if not policy.policy_number:
            policy.policy_number = generate_short_id()
            policy.save(update_fields=["policy_number"])


class Migration(migrations.Migration):
    dependencies = [
        ("policies", "0002_alter_purchasedocument_options_and_more"),
        ("quotes", "0007_change_under_review_to_needs_review"),
    ]

    operations = [
        # 1. Rename the Purchase model to Policy
        migrations.RenameModel(
            old_name="Purchase",
            new_name="Policy",
        ),
        # 2. Rename the PurchaseDocument model to PolicyDocument
        migrations.RenameModel(
            old_name="PurchaseDocument",
            new_name="PolicyDocument",
        ),
        # 3. Rename the FK field from 'purchase' to 'policy' in PolicyDocument
        migrations.RenameField(
            model_name="policydocument",
            old_name="purchase",
            new_name="policy",
        ),
        # 4. Add the policy_number field
        migrations.AddField(
            model_name="policy",
            name="policy_number",
            field=models.CharField(
                default="", max_length=20, verbose_name="Policy Number"
            ),
            preserve_default=False,
        ),
        # 5. Populate policy_number from quote_number
        migrations.RunPython(populate_policy_numbers, migrations.RunPython.noop),
        # 6. Make policy_number unique after populating
        migrations.AlterField(
            model_name="policy",
            name="policy_number",
            field=models.CharField(
                max_length=20, unique=True, verbose_name="Policy Number"
            ),
        ),
        # 7. Update db_table for Policy
        migrations.AlterModelTable(
            name="policy",
            table="policies",
        ),
        # 8. Update db_table for PolicyDocument
        migrations.AlterModelTable(
            name="policydocument",
            table="policy_documents",
        ),
        # 9. Update model options for Policy
        migrations.AlterModelOptions(
            name="policy",
            options={
                "ordering": ["-created_at"],
                "verbose_name": "Policy",
                "verbose_name_plural": "Policies",
            },
        ),
        # 10. Update the related_name on the Quote FK from 'purchase' to 'policy'
        migrations.AlterField(
            model_name="policy",
            name="quote",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="policy",
                to="quotes.quote",
                verbose_name="Quote",
            ),
        ),
    ]
