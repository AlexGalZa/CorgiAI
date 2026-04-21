# H18: Django Read-Only API Key Provisioning
# Extends User.role choices to include 'read_only'.
#
# NOTE: The H18 spec referenced `0014_add_read_only_role.py`, but the users
# migration history has advanced since then (latest pre-existing migration is
# 0021_user_hubspot_contact_id). This migration is the equivalent `AlterField`
# on the current head of the `users` app.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0021_user_hubspot_contact_id"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="role",
            field=models.CharField(
                choices=[
                    ("admin", "Admin"),
                    ("ae", "Account Executive"),
                    ("ae_underwriting", "AE + Underwriting"),
                    ("bdr", "Business Development Rep"),
                    ("finance", "Finance"),
                    ("broker", "Broker"),
                    ("claims_adjuster", "Claims Adjuster"),
                    ("customer_support", "Customer Support"),
                    ("read_only", "Read-Only API"),
                    ("policyholder", "Policyholder"),
                ],
                db_index=True,
                default="policyholder",
                help_text="Policyholders can only access the portal.",
                max_length=20,
                verbose_name="Role",
            ),
        ),
    ]
