"""
Regenerate social post copy from live DB context + OpenAI.

Examples:
  python manage.py regenerate_social_content
  python manage.py regenerate_social_content --no-save --output social-bundle.json
  python manage.py regenerate_social_content --quiet

Cron (production server, weekly):
  0 15 * * 1 cd /app && /venv/bin/python manage.py regenerate_social_content >> /var/log/social_regen.log 2>&1
"""

import json

from django.core.management.base import BaseCommand, CommandError

from marketing.social_regenerator import regenerate_bundle


class Command(BaseCommand):
    help = "Regenerate Instagram / LinkedIn / X copy from site context (OpenAI); saves SocialContentBundle by default."

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-save",
            action="store_true",
            help="Do not write SocialContentBundle to the database.",
        )
        parser.add_argument(
            "--output",
            metavar="PATH",
            help="Write platforms JSON to this file (UTF-8).",
        )
        parser.add_argument(
            "--quiet",
            action="store_true",
            help="Suppress stdout (still logs errors to stderr).",
        )

    def handle(self, *args, **options):
        no_save = options["no_save"]
        out_path = options.get("output")
        quiet = options["quiet"]

        bundle = regenerate_bundle(save=not no_save)

        payload = {
            "success": bundle.success,
            "model_used": bundle.model_used,
            "created_at": bundle.created_at.isoformat() if bundle.pk else None,
            "platforms": bundle.platforms,
            "error": bundle.error,
        }

        if out_path:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)

        if not quiet:
            if bundle.success:
                self.stdout.write(self.style.SUCCESS("Social content regenerated."))
                self.stdout.write(json.dumps(bundle.platforms, indent=2, ensure_ascii=False))
                if bundle.pk:
                    self.stdout.write(f"Saved bundle id={bundle.pk}")
            else:
                self.stderr.write(self.style.ERROR(bundle.error or "Unknown error"))

        if not bundle.success:
            raise CommandError(bundle.error or "Social content regeneration failed")
