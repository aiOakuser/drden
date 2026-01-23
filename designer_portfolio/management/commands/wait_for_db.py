import os
import time

from django.core.management import BaseCommand
from django.db import connections
from django.db.utils import OperationalError


class Command(BaseCommand):
    help = "Wait for the default database connection to be available."

    def add_arguments(self, parser):
        parser.add_argument(
            "--timeout",
            type=int,
            default=int(os.getenv("DB_WAIT_TIMEOUT", "60")),
            help="Max seconds to wait for the database (DB_WAIT_TIMEOUT).",
        )
        parser.add_argument(
            "--interval",
            type=float,
            default=float(os.getenv("DB_WAIT_INTERVAL", "2")),
            help="Seconds between retries (DB_WAIT_INTERVAL).",
        )

    def handle(self, *args, **options):
        timeout = max(0, int(options["timeout"]))
        interval = max(0.5, float(options["interval"]))
        deadline = time.monotonic() + timeout
        attempt = 0

        while True:
            attempt += 1
            try:
                connections["default"].cursor()
            except OperationalError:
                if time.monotonic() >= deadline:
                    self.stderr.write(
                        self.style.ERROR(
                            f"Database still unavailable after {timeout}s."
                        )
                    )
                    raise
                self.stdout.write(
                    f"Database unavailable (attempt {attempt}); retrying in {interval}s..."
                )
                time.sleep(interval)
            else:
                self.stdout.write(self.style.SUCCESS("Database is available."))
                break
