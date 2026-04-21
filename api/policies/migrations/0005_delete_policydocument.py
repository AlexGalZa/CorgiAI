# Generated manually to delete PolicyDocument model

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("policies", "0004_policy_billing_frequency_policy_monthly_premium_and_more"),
        # Ensure data is migrated to UserDocument before deleting
        ("users", "0003_migrate_policy_documents_to_user_documents"),
    ]

    operations = [
        migrations.DeleteModel(
            name="PolicyDocument",
        ),
    ]
