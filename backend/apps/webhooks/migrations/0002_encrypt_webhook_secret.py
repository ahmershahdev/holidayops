from typing import Any

from django.db import migrations

import apps.webhooks.models
import config.crypto
from config.crypto import TOKEN_PREFIX, encrypt


def encrypt_existing(apps: Any, schema_editor: Any) -> None:
    # Raw SQL: the model field would try to decrypt the plain values still stored.
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT id, secret FROM webhooks_webhook")
        for pk, secret in cursor.fetchall():
            if secret and not secret.startswith(TOKEN_PREFIX):
                cursor.execute(
                    "UPDATE webhooks_webhook SET secret = %s WHERE id = %s", [encrypt(secret), pk]
                )


class Migration(migrations.Migration):
    dependencies = [
        ("webhooks", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="webhook",
            name="secret",
            field=config.crypto.EncryptedCharField(
                default=apps.webhooks.models.new_secret, max_length=255
            ),
        ),
        migrations.RunPython(encrypt_existing, migrations.RunPython.noop),
    ]
