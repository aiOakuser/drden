from django.core.management.base import BaseCommand
from django.utils.text import slugify
from designer_portfolio.models import Collection


class Command(BaseCommand):
    help = "Regenerate slugs for all Collections to match name-year"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview slug changes without saving to the database",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force regenerate all slugs, even if they already match",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        force = options["force"]
        updated_count = 0

        for collection in Collection.objects.all():
            base_slug = slugify(f"{collection.name}-{collection.year}")
            slug = base_slug
            counter = 1

            # Ensure uniqueness
            while Collection.objects.filter(slug=slug).exclude(pk=collection.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            # Conditions for updating:
            # 1. Slug is empty
            # 2. Slug differs
            # 3. Force flag is set
            if force or not collection.slug or collection.slug != slug:
                old_slug = collection.slug or "(empty)"
                if dry_run:
                    self.stdout.write(
                        self.style.WARNING(
                            f"[DRY RUN] Would update slug for '{collection.name} ({collection.year})' "
                            f"from '{old_slug}' → '{slug}'"
                        )
                    )
                else:
                    collection.slug = slug
                    collection.save(update_fields=["slug"])
                    updated_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Updated slug for '{collection.name} ({collection.year})' "
                            f"from '{old_slug}' → '{slug}'"
                        )
                    )

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run complete. No changes saved."))
        else:
            if updated_count == 0:
                self.stdout.write(self.style.WARNING("No slugs needed updating."))
            else:
                self.stdout.write(self.style.SUCCESS(f"Done. Updated {updated_count} slugs."))
