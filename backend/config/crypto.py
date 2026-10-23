"""Encryption at rest for secrets the app must read back: authenticator-app secrets and webhook
signing secrets. Docs: docs/security.md, "Encryption at rest".

Fernet (AES-128-CBC with HMAC-SHA256) with keys from FIELD_ENCRYPTION_KEYS, comma-separated: the
first encrypts, all of them decrypt, so a key is rotated by putting the new one first and running
`manage.py reencrypt`. Separate from SECRET_KEY, so rotating one never breaks the other."""

from typing import Any

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models

# Every Fernet token starts with these bytes (version 0x80 + timestamp), base64-encoded.
TOKEN_PREFIX = "gAAAAA"  # noqa: S105 - a format marker, not a secret


def _fernet() -> MultiFernet:
    keys = settings.FIELD_ENCRYPTION_KEYS
    if not keys:
        raise ImproperlyConfigured(
            'Set FIELD_ENCRYPTION_KEYS (make one with: python -c "from cryptography.fernet '
            'import Fernet; print(Fernet.generate_key().decode())").'
        )
    try:
        return MultiFernet([Fernet(key) for key in keys])
    except ValueError as error:
        raise ImproperlyConfigured("FIELD_ENCRYPTION_KEYS holds a malformed key.") from error


def encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken as error:
        raise ImproperlyConfigured(
            "A stored secret doesn't decrypt with FIELD_ENCRYPTION_KEYS: was a key removed?"
        ) from error


def rotate(token: str) -> str:
    """Re-encrypt with the first key."""
    return _fernet().rotate(token.encode()).decode()


class EncryptedCharField(models.CharField):  # type: ignore[type-arg]
    """Plain text in Python, a Fernet token in the database. Not searchable or orderable."""

    def get_prep_value(self, value: Any) -> Any:
        value = super().get_prep_value(value)
        if value is None or value == "":
            return value
        return encrypt(str(value))

    def from_db_value(self, value: Any, expression: Any, connection: Any) -> Any:
        if value is None or value == "":
            return value
        return decrypt(value)
