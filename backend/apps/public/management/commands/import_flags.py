import shutil
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.core import list_countries
from apps.public.flags import FLAG_DIR, UnsafeSvg, sanitize


class Command(BaseCommand):
    help = "Import sanitised 4x3 flags from an unpacked flag-icons package (npm pack flag-icons)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("package_dir", type=Path)

    def handle(self, *args: Any, **options: Any) -> None:
        source = options["package_dir"] / "flags" / "4x3"
        if not source.is_dir():
            raise CommandError(f"{source} not found.")
        FLAG_DIR.mkdir(parents=True, exist_ok=True)
        before = after = 0
        for code in sorted(list_countries()):
            raw = (source / f"{code.lower()}.svg").read_text(encoding="utf-8")
            try:
                clean = sanitize(raw)
            except UnsafeSvg as exc:
                raise CommandError(f"{code}: {exc}") from exc
            (FLAG_DIR / f"{code.lower()}.svg").write_text(clean, encoding="utf-8", newline="\n")
            before += len(raw.encode())
            after += len(clean.encode())
        shutil.copyfile(options["package_dir"] / "LICENSE", FLAG_DIR / "LICENSE.txt")
        count = len(list_countries())
        self.stdout.write(f"{count} flags, {before // 1024} KB -> {after // 1024} KB.")
