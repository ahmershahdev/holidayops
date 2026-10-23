from typing import Any

from django.db import migrations

import config.crypto
from config.crypto import TOKEN_PREFIX, encrypt


def encrypt_existing(apps: Any, schema_editor: Any) -> None:
    # Raw SQL: the model field would try to decrypt the plain values still stored.
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT id, secret FROM accounts_twofactor")
        for pk, secret in cursor.fetchall():
            if secret and not secret.startswith(TOKEN_PREFIX):
                cursor.execute(
                    "UPDATE accounts_twofactor SET secret = %s WHERE id = %s", [encrypt(secret), pk]
                )


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0005_email_verification"),
    ]

    operations = [
        migrations.AlterField(
            model_name="twofactor",
            name="secret",
            field=config.crypto.EncryptedCharField(max_length=255),
        ),
        migrations.RunPython(encrypt_existing, migrations.RunPython.noop),
    ]
