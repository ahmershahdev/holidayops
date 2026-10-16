import datetime
import os
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import User
from apps.calendars.models import Calendar, CalendarSource, CustomDay
from apps.orgs.models import Membership, Organization, Role

DEMO_EMAIL = "demo@holidayops.test"

CUSTOM_DAYS = [
    (datetime.date(2027, 4, 5), "Office move", "closure"),
    (datetime.date(2027, 3, 31), "Quarter close", "half_day"),
    (datetime.date(2027, 4, 3), "Stocktake", "working_day"),
]


class Command(BaseCommand):
    help = "Create a demo user, organization and company calendar (development only)."

    def handle(self, *args: Any, **options: Any) -> None:
        if not settings.DEBUG:
            raise CommandError("seed_demo only runs with DEBUG on.")
        password = os.environ.get("DEMO_PASSWORD", "")
        if len(password) < 10:
            raise CommandError("Set DEMO_PASSWORD (10+ characters) in .env first.")

        with transaction.atomic():
            user, _ = User.objects.get_or_create(email=DEMO_EMAIL, defaults={"name": "Demo"})
            user.set_password(password)
            user.save()
            org, _ = Organization.objects.get_or_create(
                slug="demo-logistics", defaults={"name": "Demo Logistics"}
            )
            Membership.objects.get_or_create(user=user, org=org, defaults={"role": Role.OWNER})
            calendar, created = Calendar.objects.get_or_create(
                org=org,
                slug="karachi-riyadh",
                defaults={"name": "Karachi + Riyadh", "language": "en_US"},
            )
            if created:
                CalendarSource.objects.create(calendar=calendar, country="PK", position=0)
                CalendarSource.objects.create(calendar=calendar, country="SA", position=1)
            for day, name, kind in CUSTOM_DAYS:
                CustomDay.objects.get_or_create(
                    calendar=calendar, date=day, defaults={"name": name, "kind": kind}
                )

        self.stdout.write(self.style.SUCCESS(f"Demo ready: log in as {DEMO_EMAIL}"))
