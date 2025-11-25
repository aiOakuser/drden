from __future__ import annotations

import os
from typing import Dict, Any, Callable, Optional

from django.contrib.auth.models import User
from django.db import transaction

from designer_portfolio.models import DesignerProfile

Notifier = Optional[Callable[[str], None]]
PROFILE_FIELD_NAMES: tuple[str, ...] = (
    "portfolio_website",
    "contact_email",
    "region_area",
    "country",
    "state_province",
    "county",
    "city",
    "location",
)


def _notify(notifier: Notifier, message: str) -> None:
    if notifier:
        notifier(message)


def _designer_seed_entries() -> list[Dict[str, Any]]:
    """
    Return the canonical list of designer accounts that should always exist.
    Environment-sensitive fields (like emails) are resolved here so that they
    stay up to date across both management commands and automatic bootstrap steps.
    """
    return [
        {
            "username": "caukin",
            "portfolio_website": "https://caukin.aioak.co",
            "region_area": "West Coast",
            "country": "United States",
            "state_province": "California",
            "county": "Los Angeles County",
            "city": "Los Angeles",
            "location": "Los Angeles, CA, USA",
        },
        {
            "username": "jturner",
            "portfolio_website": "https://jturner.aioak.co",
            "region_area": "West Coast",
            "country": "United States",
            "state_province": "California",
            "county": "Los Angeles County",
            "city": "Los Angeles",
            "location": "Los Angeles, CA, USA",
        },
        {"username": "rossmason", "portfolio_website": "https://rossmason.aioak.co"},
        {
            "username": "Over-Stimulated",
            "portfolio_website": "https://stimulated.aioak.co",
            "region_area": "West Coast",
            "country": "United States",
            "state_province": "California",
            "county": "Los Angeles County",
            "city": "Los Angeles",
            "location": "Los Angeles, CA, USA",
        },
        {
            "username": "m1director",
            "portfolio_website": "https://m1director.aioak.co",
            "region_area": "West Coast",
            "country": "United States",
            "state_province": "California",
            "county": "Los Angeles County",
            "city": "Los Angeles",
            "location": "Los Angeles, CA, USA",
        },
        {
            "username": "prettypearl",
            # Prefer environment variable; if empty, leaves contact hidden until set
            "contact_email": os.getenv("PRETTYPEARL_CONTACT_EMAIL", "").strip(),
        },
        {"username": "myrym", "portfolio_website": "https://myrym.aioak.co"},
        {"username": "ateliernova", "portfolio_website": "https://ateliernova.aioak.co"},
        {"username": "solstice", "portfolio_website": "https://solstice.aioak.co"},
        {"username": "modohaus", "portfolio_website": "https://modohaus.aioak.co"},
        {"username": "lumenknit", "portfolio_website": "https://lumenknit.aioak.co"},
    ]


@transaction.atomic
def ensure_core_designers(make_inactive: bool = False, notifier: Notifier = None) -> dict[str, int]:
    """
    Idempotently create/update the default designer accounts so production restores
    always bring them back after a database reset.
    """
    created_count = 0
    activated_count = 0
    profile_updates = 0

    desired_active_state = not make_inactive

    for entry in _designer_seed_entries():
        username = entry["username"]

        profile_fields: Dict[str, Any] = {
            field_name: entry[field_name]
            for field_name in PROFILE_FIELD_NAMES
            if entry.get(field_name)
        }

        user, created = User.objects.get_or_create(username=username)

        user_needs_save = created
        if created:
            user.email = user.email or ""
            user.set_unusable_password()
            created_count += 1

        if user.is_active != desired_active_state:
            user.is_active = desired_active_state
            user_needs_save = True
            if not created and desired_active_state:
                activated_count += 1

        if user_needs_save:
            user.save()
            _notify(notifier, f"User '{username}' saved (created={created}, active={user.is_active}).")

        profile, _ = DesignerProfile.objects.get_or_create(user=user)
        profile_changed = False

        for field_name, field_value in profile_fields.items():
            if getattr(profile, field_name) != field_value:
                setattr(profile, field_name, field_value)
                profile_changed = True

        if profile_changed:
            profile.save()
            profile_updates += 1
            _notify(notifier, f"Profile for '{username}' updated.")

    return {
        "created": created_count,
        "activated": activated_count,
        "profiles_updated": profile_updates,
    }
