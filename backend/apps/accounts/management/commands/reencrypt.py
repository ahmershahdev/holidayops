from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import TwoFactor
from apps.webhooks.models import Webhook


class Command(BaseCommand):
    help = "Re-encrypt stored secrets with the first FIELD_ENCRYPTION_KEYS key (key rotation)."

    def handle(self, *args: Any, **options: Any) -> None:
        count = 0
        with transaction.atomic():
            for model in (TwoFactor, Webhook):
                for row in model.objects.select_for_update().only("pk", "secret"):
                    row.save(update_fields=["secret"])
                    count += 1
        self.stdout.write(f"Re-encrypted {count} secrets. Old keys can now be removed.")
