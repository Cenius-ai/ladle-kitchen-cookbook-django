"""Alias for :mod:`seed_demo` so both `seed` and `seed_demo` work."""

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Populate the demo household (same as seed_demo)."

    def add_arguments(self, parser):
        parser.add_argument("--quiet", action="store_true", help="Only print the summary line.")

    def handle(self, *args, **options):
        call_command(
            "seed_demo",
            quiet=options.get("quiet", False),
            stdout=self.stdout,
            stderr=self.stderr,
        )
