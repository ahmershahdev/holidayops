from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.orgs.models import Organization, Plan


class Command(BaseCommand):
    help = "Set an organization's plan (there is no billing yet)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("org_slug")
        parser.add_argument("plan", choices=Plan.values)

    def handle(self, *args: Any, **options: Any) -> None:
        updated = Organization.objects.filter(slug=options["org_slug"]).update(plan=options["plan"])
        if not updated:
            raise CommandError(f"No organization with slug {options['org_slug']!r}.")
        self.stdout.write(f"{options['org_slug']} is now on {options['plan']}.")
