"""
V3 #52 — PII Encryption at rest.

- Alter Company.federal_ein to use EncryptedCharField (wider column for ciphertext)
- Add Company.bank_account_number (EncryptedCharField)
- Add Company.bank_routing_number (EncryptedCharField)

The EncryptedCharField.contribute_to_class() multiplies max_length by 4 + 120
at runtime, so the DB column is already wide enough to hold Fernet ciphertext.
"""

from django.db import migrations
import common.encrypted_fields


class Migration(migrations.Migration):
    dependencies = [
        ("quotes", "0054_add_soft_delete_fields"),
    ]

    operations = [
        # Widen federal_ein column to accommodate ciphertext (4×20 + 120 = 200)
        migrations.AlterField(
            model_name="company",
            name="federal_ein",
            field=common.encrypted_fields.EncryptedCharField(
                blank=True,
                help_text="Federal Employer Identification Number — encrypted at rest",
                max_length=20,
                null=True,
                verbose_name="Federal EIN",
            ),
        ),
        # Add bank_account_number
        migrations.AddField(
            model_name="company",
            name="bank_account_number",
            field=common.encrypted_fields.EncryptedCharField(
                blank=True,
                help_text="ACH bank account number — encrypted at rest",
                max_length=50,
                null=True,
                verbose_name="Bank Account Number",
            ),
        ),
        # Add bank_routing_number
        migrations.AddField(
            model_name="company",
            name="bank_routing_number",
            field=common.encrypted_fields.EncryptedCharField(
                blank=True,
                help_text="ACH routing number — encrypted at rest",
                max_length=20,
                null=True,
                verbose_name="Bank Routing Number",
            ),
        ),
    ]
