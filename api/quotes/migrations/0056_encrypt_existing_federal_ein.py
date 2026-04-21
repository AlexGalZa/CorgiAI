"""
V3 #52 — Data migration: encrypt existing plaintext federal_ein values.

Iterates all Company records with a non-empty federal_ein and re-saves them
so the EncryptedCharField.get_prep_value() encrypts the value in the DB.
"""

from django.db import migrations


def encrypt_federal_eins(apps, schema_editor):
    """Encrypt all existing plaintext federal_ein values."""
    Company = apps.get_model("quotes", "Company")
    from common.encrypted_fields import encrypt, _ENC_PREFIX

    updated = 0
    for company in Company.objects.filter(federal_ein__isnull=False).exclude(
        federal_ein=""
    ):
        ein = company.federal_ein
        # Skip already-encrypted values
        if isinstance(ein, str) and ein.startswith(_ENC_PREFIX):
            continue
        company.federal_ein = encrypt(ein)
        company.save(update_fields=["federal_ein"])
        updated += 1

    if updated:
        print(f"\n  Encrypted {updated} federal_ein values.")


def decrypt_federal_eins(apps, schema_editor):
    """Reverse migration: decrypt federal_ein values back to plaintext."""
    Company = apps.get_model("quotes", "Company")
    from common.encrypted_fields import decrypt, _ENC_PREFIX

    for company in Company.objects.filter(federal_ein__isnull=False).exclude(
        federal_ein=""
    ):
        ein = company.federal_ein
        if isinstance(ein, str) and ein.startswith(_ENC_PREFIX):
            company.federal_ein = decrypt(ein)
            company.save(update_fields=["federal_ein"])


class Migration(migrations.Migration):
    dependencies = [
        ("quotes", "0055_add_encrypted_pii_fields"),
    ]

    operations = [
        migrations.RunPython(encrypt_federal_eins, decrypt_federal_eins),
    ]
