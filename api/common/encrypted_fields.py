"""
Fernet-based encrypted Django model fields for PII at rest.

Usage
-----
    from common.encrypted_fields import EncryptedCharField, EncryptedTextField

    class MyModel(models.Model):
        ssn = EncryptedCharField(max_length=20, blank=True)
        notes = EncryptedTextField(blank=True)

Settings
--------
    ENCRYPTION_KEY   - base64-url-encoded 32-byte Fernet key.
                       Generate with: Fernet.generate_key().decode()
                       Defaults to a key derived from SECRET_KEY (dev only).

Security notes
--------------
- Fernet uses AES-128-CBC + HMAC-SHA256. Each value is independently
  encrypted with a random IV, so identical plaintexts produce different
  ciphertexts.
- Encrypted values are stored as base64 strings prefixed with "enc::".
  The prefix lets the field distinguish between already-encrypted and
  legacy plaintext values (migration-safe).
- The raw database column stores up to max_length*3 bytes (base64
  overhead + Fernet overhead ~100 bytes). max_length is therefore the
  length of the *plaintext*, not the stored ciphertext.
"""

import base64
import logging

from django.conf import settings
from django.db import models

logger = logging.getLogger(__name__)

_ENC_PREFIX = "enc::"


def _get_fernet():
    """Return a cached Fernet instance.  Lazy to avoid import-time errors."""
    from cryptography.fernet import Fernet

    key = getattr(settings, "ENCRYPTION_KEY", None)
    if not key:
        # Fallback: derive a 32-byte key from SECRET_KEY (dev/test only)
        import hashlib

        raw = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
        key = base64.urlsafe_b64encode(raw).decode()
        logger.warning(
            "ENCRYPTION_KEY not set — using SECRET_KEY derivation. Set ENCRYPTION_KEY in production!"
        )
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt(value: str) -> str:
    """Encrypt *value* and return a prefixed base64 string."""
    if not value:
        return value
    if isinstance(value, str) and value.startswith(_ENC_PREFIX):
        return value  # already encrypted
    fernet = _get_fernet()
    token = fernet.encrypt(value.encode()).decode()
    return f"{_ENC_PREFIX}{token}"


def decrypt(value: str) -> str:
    """Decrypt a prefixed base64 string and return the plaintext."""
    if not value:
        return value
    if isinstance(value, str) and value.startswith(_ENC_PREFIX):
        token = value[len(_ENC_PREFIX) :]
        fernet = _get_fernet()
        try:
            return fernet.decrypt(token.encode()).decode()
        except Exception:
            logger.exception("Failed to decrypt value — returning raw")
            return value
    # Legacy plaintext — return as-is
    return value


class EncryptedMixin:
    """
    Mixin that encrypts on set and decrypts on get.

    The DB column is sized as CharField(max_length=max_length * 4 + 100)
    to accommodate Fernet + base64 overhead.
    """

    def contribute_to_class(self, cls, name):
        super().contribute_to_class(cls, name)
        # Increase the actual DB column length to hold the ciphertext.
        # Fernet token ≈ 73 + len(plaintext) bytes, base64-encoded → ~1.4×.
        # We use 4× the stated max_length + 120 as a safe upper bound.
        if hasattr(self, "max_length") and self.max_length:
            self.max_length = self.max_length * 4 + 120

    def from_db_value(self, value, expression, connection):
        return decrypt(value) if value is not None else value

    def to_python(self, value):
        return decrypt(value) if value and isinstance(value, str) else value

    def get_prep_value(self, value):
        if value is None or value == "":
            return value
        return encrypt(value)


class EncryptedCharField(EncryptedMixin, models.CharField):
    """
    CharField whose value is transparently encrypted at rest using Fernet.

    *max_length* refers to the maximum plaintext length; the DB column is
    automatically widened to accommodate the ciphertext.
    """

    def __init__(self, *args, **kwargs):
        # Store original max_length for documentation purposes.
        self._plaintext_max_length = kwargs.get("max_length", 255)
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        # Restore original max_length for migrations so re-runs are stable.
        kwargs["max_length"] = self._plaintext_max_length
        return name, path, args, kwargs


class EncryptedTextField(EncryptedMixin, models.TextField):
    """
    TextField whose value is transparently encrypted at rest using Fernet.
    """

    def from_db_value(self, value, expression, connection):
        return decrypt(value) if value is not None else value

    def to_python(self, value):
        return decrypt(value) if value and isinstance(value, str) else value

    def get_prep_value(self, value):
        if value is None or value == "":
            return value
        return encrypt(value)
