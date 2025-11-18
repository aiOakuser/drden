from __future__ import annotations

import os
from typing import Dict, Any

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction

from designer_portfolio.models import DesignerProfile


class Command(BaseCommand):
    help = "Create or restore specified designer users and configure their profiles"

    def add_arguments(self, parser):
        parser.add_argument(
            "--inactive",
            action="store_true",
            help="Create users as inactive (default: active)",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        make_inactive: bool = options.get("inactive", False)

        # Map of users to restore with their desired profile configuration
        # For 'seri', read contact email from environment to avoid committing secrets.
        users_to_restore = [
            {"username": "caukin", "portfolio_website": "https://caukin.aioak.co"},
            {"username": "jturner", "portfolio_website": "https://jturner.aioak.co"},
            {"username": "rossmason", "portfolio_website": "https://rossmason.aioak.co"},
            {"username": "Over-Stimulated", "portfolio_website": "https://stimulated.aioak.co"},
            {"username": "m1director", "portfolio_website": "https://m1director.aioak.co"},
            {
                "username": "seri",
                # Prefer environment variable; if empty, leaves contact hidden until set
                "contact_email": os.getenv("SERI_CONTACT_EMAIL", "").strip(),
            },
            {"username": "myrym", "portfolio_website": "https://myrym.aioak.co"},
        ]

        created_count = 0
        updated_count = 0
        profile_updates = 0

        for entry in users_to_restore:
            username: str = entry["username"]
            profile_fields: Dict[str, Any] = {}

            if entry.get("portfolio_website"):
                profile_fields["portfolio_website"] = entry["portfolio_website"]
            if entry.get("contact_email"):
                profile_fields["contact_email"] = entry["contact_email"]

            user, created = User.objects.get_or_create(username=username)

            # Ensure account is active so it appears in public listings
            was_active = user.is_active
            user.is_active = not make_inactive

            # Do not set a real password in code; mark as unusable if newly created
            if created:
                user.email = user.email or ""
                user.set_unusable_password()
                created_count += 1
            else:
                updated_count += int(user.is_active != was_active)

            user.save()

            # Ensure a DesignerProfile exists and update requested fields
            profile, _ = DesignerProfile.objects.get_or_create(user=user)

            changed = False
            for field_name, field_value in profile_fields.items():
                if getattr(profile, field_name) != field_value:
                    setattr(profile, field_name, field_value)
                    changed = True

            if changed:
                profile.save()
                profile_updates += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f"Processed user '{username}': user_created={created}, profile_updated={changed}"
                )
            )

        self.stdout.write("")
        self.stdout.write(self.style.NOTICE("Summary:"))
        self.stdout.write(f"  Users created: {created_count}")
        self.stdout.write(f"  Users updated (active state): {updated_count}")
        self.stdout.write(f"  Profiles updated: {profile_updates}")
        self.stdout.write("")
        self.stdout.write(
            "Tip: Set SERI_CONTACT_EMAIL in your environment before running to show the email icon for 'seri'."
        )
