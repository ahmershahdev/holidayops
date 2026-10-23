import os
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.utils import timezone

from apps.accounts.models import User

ROLES = ("owner", "admin", "member", "viewer", "outsider", "target")


class Command(BaseCommand):
    help = "Confirmed accounts for scripts/attack_simulation.py. Only with ALLOW_SIMULATION=1."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("run", help="A label that makes this run's addresses unique.")

    def handle(self, *args: Any, **options: Any) -> None:
        # Known passwords on confirmed accounts: never on a real deployment.
        if os.environ.get("ALLOW_SIMULATION") != "1":
            raise CommandError("Refused: set ALLOW_SIMULATION=1 (docker/simulation.yml does).")
        password = os.environ.get("SIM_PASSWORD", "")
        if len(password) < 12:
            raise CommandError("Set SIM_PASSWORD to 12 or more characters.")
        for role in ROLES:
            email = f"{role}-{options['run']}@simulation.test"
            user = User.objects.filter(email=email).first() or User(email=email, name=role)
            user.set_password(password)
            user.email_verified_at = timezone.now()
            user.save()
        self.stdout.write(f"{len(ROLES)} accounts for run {options['run']}")
