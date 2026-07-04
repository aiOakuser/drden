import gzip
import io
from datetime import datetime, timezone
from typing import List

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management import BaseCommand, call_command


class Command(BaseCommand):
    help = "Create a compressed JSON backup of the database and store it in default storage (S3 if configured)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            dest="output",
            default=None,
            help="Destination path in storage. Defaults to backups/db-<timestamp>.json.gz",
        )
        parser.add_argument(
            "--exclude",
            dest="exclude",
            action="append",
            default=["contenttypes"],
            help="Apps or app_label.Model to exclude. Can be provided multiple times.",
        )

    def handle(self, *args, **options):
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        output_path = options["output"] or f"backups/db-{timestamp}.json.gz"
        exclude: List[str] = options.get("exclude") or []

        # Capture dumpdata output to memory
        json_stream = io.StringIO()
        dump_args = [
            "--natural-foreign",
            "--natural-primary",
            "--verbosity",
            "1",
        ]
        for item in exclude:
            dump_args.extend(["--exclude", item])

        call_command("dumpdata", *dump_args, stdout=json_stream)
        json_data = json_stream.getvalue().encode("utf-8")

        # Compress and save to storage
        bytes_buffer = io.BytesIO()
        with gzip.GzipFile(fileobj=bytes_buffer, mode="wb") as gz:
            gz.write(json_data)
        compressed = bytes_buffer.getvalue()

        saved_path = default_storage.save(output_path, ContentFile(compressed))
        self.stdout.write(self.style.SUCCESS(f"Backup written to: {saved_path}"))
