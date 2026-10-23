from typing import Any

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.db.models import F


def verify_existing(apps: Any, schema_editor: Any) -> None:
    # Accounts made before verification existed keep working; they were in use already.
    apps.get_model("accounts", "User").objects.update(email_verified_at=F("date_joined"))


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0004_two_factor_and_sso"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="email_verified_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(verify_existing, migrations.RunPython.noop),
        migrations.RenameModel(old_name="PasswordResetCode", new_name="EmailCode"),
        migrations.AddField(
            model_name="emailcode",
            name="purpose",
            field=models.CharField(
                choices=[("reset", "Reset"), ("verify", "Verify")], default="reset", max_length=10
            ),
        ),
        migrations.AlterField(
            model_name="emailcode",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="email_codes",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
