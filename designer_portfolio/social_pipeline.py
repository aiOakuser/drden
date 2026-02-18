"""Custom social-auth pipeline helpers for designer Google login."""

from __future__ import annotations

import secrets
from typing import Any, Dict, Optional

from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string
from django.utils.text import slugify
from social_core.exceptions import AuthForbidden

from .auth_utils import ensure_designer_access
from .emails import send_registration_notifications


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return False


def _username_meta():
    UserModel = get_user_model()
    field = UserModel._meta.get_field(UserModel.USERNAME_FIELD)
    return field, UserModel.USERNAME_FIELD


def _build_base_username(details: Optional[Dict[str, Any]], response: Optional[Dict[str, Any]]) -> str:
    candidate_sources = [
        (details or {}).get("username"),
        (details or {}).get("email"),
        (response or {}).get("email"),
        (details or {}).get("fullname"),
        (response or {}).get("name"),
        (response or {}).get("given_name"),
    ]

    for candidate in candidate_sources:
        if candidate:
            slug = slugify(candidate, allow_unicode=False)
            if slug:
                return slug[:150]  # temporary cap, will trim to field length later

    # Fallback: generate a pseudo-random slug
    return slugify(get_random_string(12), allow_unicode=False) or secrets.token_hex(4)


def _dedupe_username(base_username: str) -> str:
    field, field_name = _username_meta()
    max_length = getattr(field, "max_length", 150) or 150
    normalized = base_username[:max_length] or secrets.token_hex(4)

    UserModel = get_user_model()
    lookup = f"{field_name}__iexact"

    if not UserModel.objects.filter(**{lookup: normalized}).exists():
        return normalized

    suffix = 1
    base = normalized
    while True:
        suffix_text = f"-{suffix}"
        candidate = f"{base[: max_length - len(suffix_text)]}{suffix_text}".strip("-")
        if not candidate:
            candidate = secrets.token_hex(4)
        if not UserModel.objects.filter(**{lookup: candidate}).exists():
            return candidate
        suffix += 1


def generate_username(strategy, details=None, backend=None, user=None, response=None, *args, **kwargs):
    """Ensure a sanitized, unique username for social-auth user creation."""
    if user is not None or kwargs.get("username"):
        return {}

    base_username = _build_base_username(details, response)
    unique_username = _dedupe_username(base_username)
    return {"username": unique_username}


def ensure_verified_email(strategy, details=None, backend=None, response=None, *args, **kwargs):
    """Require verified Google email addresses before allowing login."""
    if backend is None or getattr(backend, "name", "") != "google-oauth2":
        return

    email = (details or {}).get("email") or (response or {}).get("email")
    if not email:
        raise AuthForbidden(backend, "Google account did not return an email address.")

    indicators = [
        (details or {}).get("email_verified"),
        (response or {}).get("email_verified"),
        (response or {}).get("verified_email"),
    ]

    if any(_coerce_bool(flag) for flag in indicators):
        return

    raise AuthForbidden(backend, "Google account email must be verified before signing in.")


def sync_user_details(strategy, backend=None, user=None, details=None, response=None, *args, **kwargs):
    """Keep Django user + designer profile metadata aligned with Google data."""
    if user is None:
        return

    details = details or {}
    response = response or {}

    email = (details.get("email") or response.get("email") or "").strip()
    first_name = (details.get("first_name") or response.get("given_name") or "").strip()
    last_name = (details.get("last_name") or response.get("family_name") or "").strip()

    if (not first_name or not last_name) and details.get("fullname"):
        parts = [part.strip() for part in details["fullname"].split(" ", 1) if part.strip()]
        if parts:
            first_name = first_name or parts[0]
            if len(parts) > 1:
                last_name = last_name or parts[1]

    user_updates = []

    if email and user.email.lower() != email.lower():
        user.email = email
        user_updates.append("email")

    if first_name and user.first_name != first_name:
        user.first_name = first_name
        user_updates.append("first_name")

    if last_name and user.last_name != last_name:
        user.last_name = last_name
        user_updates.append("last_name")

    if user_updates:
        user.save(update_fields=user_updates)

    ensure_designer_access(user)

    profile = getattr(user, "designer_profile", None)
    if not profile:
        return

    profile_updates = []

    if email and not getattr(profile, "contact_email", "").strip():
        profile.contact_email = email
        profile_updates.append("contact_email")

    if profile_updates:
        profile.save(update_fields=profile_updates)


def credit_referral_on_social_signup(strategy, backend=None, user=None, is_new=False, *args, **kwargs):
    """Credit referrer when a new user signs up via OAuth (Google, LinkedIn, etc.)."""
    if not user or not is_new:
        return

    request = getattr(strategy, "request", None)
    if not request:
        return

    ref_code = request.session.pop("referral_code", None)
    ref_source = request.session.pop("referral_source", None)
    if not ref_code:
        return

    try:
        from .services.referrals import credit_referral_on_signup

        credit_referral_on_signup(
            user=user,
            referral_code=ref_code,
            source=ref_source,
            ip=request.META.get("REMOTE_ADDR"),
            ua=request.META.get("HTTP_USER_AGENT"),
        )
    except Exception:
        pass


def send_welcome_notification(strategy, backend=None, user=None, is_new=False, *args, **kwargs):
    """Fire the same registration email workflow for new social-auth users."""
    if not user or not is_new:
        return

    request = getattr(strategy, "request", None)
    backend_name = getattr(backend, "name", "") if backend else ""
    source_label = backend_name.strip() or "oauth"

    try:
        send_registration_notifications(user, request=request, source=f"oauth:{source_label}")
    except Exception:
        # Never block login because an email provider behaved badly.
        return

