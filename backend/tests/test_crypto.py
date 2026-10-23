from io import StringIO
from typing import Any

import pytest
from cryptography.fernet import Fernet
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.db import connection

from apps.accounts.models import TwoFactor
from apps.webhooks.models import Webhook
from config import crypto
from tests.factories import OrgFactory, UserFactory

pytestmark = pytest.mark.django_db


def stored(table: str, pk: int) -> str:
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT secret FROM {table} WHERE id = %s", [pk])
        return str(cursor.fetchone()[0])


def test_secrets_are_ciphertext_in_the_database() -> None:
    device = TwoFactor.objects.create(user=UserFactory.create(), secret="JBSWY3DPEHPK3PXP")
    hook = Webhook.objects.create(org=OrgFactory.create(), url="https://example.com/hook")
    for table, row, plain in (
        ("accounts_twofactor", device, "JBSWY3DPEHPK3PXP"),
        ("webhooks_webhook", hook, hook.secret),
    ):
        raw = stored(table, row.pk)
        assert raw.startswith(crypto.TOKEN_PREFIX)
        assert plain not in raw
        assert type(row).objects.get(pk=row.pk).secret == plain


def test_rotation_reencrypts_with_the_new_key(settings: Any) -> None:
    device = TwoFactor.objects.create(user=UserFactory.create(), secret="JBSWY3DPEHPK3PXP")
    old = settings.FIELD_ENCRYPTION_KEYS[0]
    new = Fernet.generate_key().decode()
    settings.FIELD_ENCRYPTION_KEYS = [new, old]
    call_command("reencrypt", stdout=StringIO())
    settings.FIELD_ENCRYPTION_KEYS = [new]
    assert TwoFactor.objects.get(pk=device.pk).secret == "JBSWY3DPEHPK3PXP"


def test_a_missing_or_wrong_key_fails_loudly(settings: Any) -> None:
    device = TwoFactor.objects.create(user=UserFactory.create(), secret="JBSWY3DPEHPK3PXP")
    settings.FIELD_ENCRYPTION_KEYS = [Fernet.generate_key().decode()]
    with pytest.raises(ImproperlyConfigured):
        TwoFactor.objects.get(pk=device.pk)
    settings.FIELD_ENCRYPTION_KEYS = []
    with pytest.raises(ImproperlyConfigured):
        crypto.encrypt("x")
    settings.FIELD_ENCRYPTION_KEYS = ["not-a-key"]
    with pytest.raises(ImproperlyConfigured):
        crypto.encrypt("x")


def test_the_migration_encrypts_plain_rows() -> None:
    from importlib import import_module

    migration = import_module("apps.accounts.migrations.0006_encrypt_two_factor_secret")
    device = TwoFactor.objects.create(user=UserFactory.create(), secret="JBSWY3DPEHPK3PXP")
    with connection.cursor() as cursor:
        cursor.execute("UPDATE accounts_twofactor SET secret = %s", ["JBSWY3DPEHPK3PXP"])
    migration.encrypt_existing(None, connection.schema_editor())
    assert stored("accounts_twofactor", device.pk).startswith(crypto.TOKEN_PREFIX)
    assert TwoFactor.objects.get(pk=device.pk).secret == "JBSWY3DPEHPK3PXP"
