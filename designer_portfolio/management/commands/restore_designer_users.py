from django.core.management.base import BaseCommand

from designer_portfolio.core_designers import ensure_core_designers


class Command(BaseCommand):
    help = "Create or restore specified designer users and configure their profiles"

    def add_arguments(self, parser):
        parser.add_argument(
            "--inactive",
            action="store_true",
            help="Create users as inactive (default: active)",
        )

    def handle(self, *args, **options):
        make_inactive: bool = options.get("inactive", False)

        summary = ensure_core_designers(
            make_inactive=make_inactive,
            notifier=lambda msg: self.stdout.write(self.style.SUCCESS(msg)),
        )

        self.stdout.write("")
        self.stdout.write(self.style.NOTICE("Summary:"))
        self.stdout.write(f"  Users created: {summary['created']}")
        self.stdout.write(f"  Users activated: {summary['activated']}")
        self.stdout.write(f"  Profiles updated: {summary['profiles_updated']}")
        self.stdout.write("")
        self.stdout.write(
            "Tip: Set SERI_CONTACT_EMAIL in your environment before running to show the email icon for 'seri'."
        )
