import gzip
import io
import os
import re
import tempfile
from typing import Optional

from django.apps import apps
from django.core.management.color import no_style
from django.core.files.storage import default_storage
from django.core.management import BaseCommand, call_command
from django.db import connection


class Command(BaseCommand):
    help = "Restore the database from a compressed JSON backup stored in default storage (S3 if configured)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--input",
            dest="input",
            default=None,
            help="Path in storage to the .json.gz backup. Defaults to latest in backups/.",
        )
        parser.add_argument(
            "--noinput",
            action="store_true",
            dest="noinput",
            help="Do not prompt for confirmation.",
        )
        parser.add_argument(
            "--flush",
            action="store_true",
            dest="flush",
            help="Flush existing data before loading the backup (recommended when restoring into a non-empty DB).",
        )
        parser.add_argument(
            "--skip-migrate",
            action="store_true",
            dest="skip_migrate",
            help="Skip running migrations before loading data.",
        )
        parser.add_argument(
            "--ignore-nonexistent",
            action="store_true",
            dest="ignore_nonexistent",
            help="Ignore objects/fields for apps/models that no longer exist.",
        )

    def _find_latest_backup(self) -> Optional[str]:
        prefix = "backups"
        if not default_storage.exists(prefix):
            return None
        _, files = default_storage.listdir(prefix)
        candidates = [
            f"{prefix}/{name}" for name in files if re.match(r"db-\\d{8}-\\d{6}\\.json\\.gz$", name)
        ]
        if not candidates:
            return None
        # Sort lexicographically; timestamp ensures correct order
        candidates.sort()
        return candidates[-1]

    def _reset_sequences(self) -> None:
        """
        After loading fixtures with explicit PKs, bring database sequences back in sync
        so future inserts don't hit duplicate-key errors.
        """
        models = list(apps.get_models(include_auto_created=True))
        sql_list = connection.ops.sequence_reset_sql(no_style(), models)
        if not sql_list:
            return
        with connection.cursor() as cursor:
            for sql in sql_list:
                cursor.execute(sql)

    def handle(self, *args, **options):
        input_path = options.get("input") or self._find_latest_backup()
        if not input_path:
            self.stderr.write("No backup found. Provide --input or create a backup first.")
            return

        if not options.get("noinput"):
            confirm = input(
                f"This will import data from {input_path} and may overwrite existing records. Continue? [y/N]: "
            ).strip().lower()
            if confirm not in {"y", "yes"}:
                self.stdout.write("Aborted.")
                return

        if not default_storage.exists(input_path):
            self.stderr.write(f"Backup not found: {input_path}")
            return

        # Ensure schema exists and content types / permissions are present.
        # This is critical when backups exclude `contenttypes` (common) but include
        # `auth.permission` rows that reference content types via natural keys.
        did_migrate = False
        if not options.get("skip_migrate"):
            call_command("migrate", interactive=False, verbosity=1)
            did_migrate = True

        # Optional: wipe current data to avoid unique/constraint collisions.
        # NOTE: `flush` removes contenttypes/permissions too, so if we migrated above
        # we must re-run migrations to re-create them before loaddata runs.
        if options.get("flush"):
            call_command("flush", interactive=False, verbosity=1)
            if did_migrate:
                call_command("migrate", interactive=False, verbosity=1)

        # Read and decompress
        with default_storage.open(input_path, "rb") as f:
            compressed = f.read()
        with gzip.GzipFile(fileobj=io.BytesIO(compressed), mode="rb") as gz:
            json_bytes = gz.read()

        # Write to a temporary file and delegate to loaddata
        with tempfile.NamedTemporaryFile("wb", suffix=".json", delete=False) as tmp:
            tmp.write(json_bytes)
            temp_path = tmp.name

        try:
            loaddata_kwargs = {"verbosity": 1}
            if options.get("ignore_nonexistent"):
                loaddata_kwargs["ignorenonexistent"] = True
            call_command("loaddata", temp_path, **loaddata_kwargs)
            self._reset_sequences()
            self.stdout.write(self.style.SUCCESS(f"Restore completed from {input_path}"))
        finally:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
