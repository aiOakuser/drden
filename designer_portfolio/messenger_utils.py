"""
Utilities for designer-to-designer messenger on GlobalDesignerHub.

Enforces platform-only policy: no personal contact sharing, no external links.
Messenger requires $4.99/month or higher subscription; frozen accounts are blocked.
"""

from __future__ import annotations

import re
from typing import Tuple

from .models import DesignerProfile, UserSubscription


# Patterns that indicate prohibited content (contact info, external URLs)
EMAIL_PATTERN = re.compile(
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    re.IGNORECASE,
)
# Common phone patterns: (123) 456-7890, 123-456-7890, +1 123 456 7890, 1234567890
PHONE_PATTERN = re.compile(
    r"(\+?\d{1,4}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{2,4}[-.\s]?\d{2,4}([-.\s]?\d{2,4})?",
)
# URLs - http, https, www., or common TLDs
URL_PATTERN = re.compile(
    r"https?://[^\s]+|www\.[^\s]+|[a-zA-Z0-9][-a-zA-Z0-9]*\.(com|net|org|io|co|me|link|be|portfolio)[^\s]*",
    re.IGNORECASE,
)
# Social handles: @username, instagram.com/user, linkedin.com/in/...
SOCIAL_PATTERN = re.compile(
    r"@[a-zA-Z0-9_]{2,}|(?:instagram|linkedin|twitter|facebook|tiktok|behance|dribbble)\.com/[^\s]+",
    re.IGNORECASE,
)


def message_contains_prohibited_content(text: str) -> Tuple[bool, str | None]:
    """
    Check if message contains personal contact info or external links.
    Returns (True, error_message) if prohibited content found, else (False, None).
    """
    if not text or not text.strip():
        return False, None

    # Normalize: collapse whitespace for pattern matching
    normalized = " ".join(text.split())

    if EMAIL_PATTERN.search(normalized):
        return True, (
            "Sharing email addresses is not allowed. "
            "Please keep all communication within GlobalDesignerHub."
        )
    if PHONE_PATTERN.search(normalized):
        # Allow very short number sequences (e.g. "3.14" or "Room 205")
        for m in PHONE_PATTERN.finditer(normalized):
            num = re.sub(r"\D", "", m.group(0))
            if len(num) >= 7:  # Likely a phone number
                return True, (
                    "Sharing phone numbers is not allowed. "
                    "Please keep all communication within GlobalDesignerHub."
                )
    if URL_PATTERN.search(normalized):
        return True, (
            "Sharing website or portfolio links is not allowed. "
            "Please keep all communication within GlobalDesignerHub."
        )
    if SOCIAL_PATTERN.search(normalized):
        return True, (
            "Sharing social media handles or profiles is not allowed. "
            "Please keep all communication within GlobalDesignerHub."
        )

    return False, None


def user_can_use_messenger(user) -> Tuple[bool, str | None, str | None]:
    """
    Check if user can access designer-to-designer messenger.
    Returns (True, None, None) if allowed, else (False, reason_message, redirect_view_name).
    """
    if user is None or not getattr(user, "is_authenticated", False):
        return False, "You must be logged in to use the messenger.", None

    if not DesignerProfile.objects.filter(user=user).exists():
        return False, "Messenger is available to registered designers. Please complete your profile.", "designer_about_me"

    try:
        subscription = user.subscription
    except (UserSubscription.DoesNotExist, AttributeError):
        return False, (
            "Designer messaging requires a subscription ($4.99/month or higher). "
            "Please upgrade your account to connect with other designers."
        ), "subscription_dashboard"

    if subscription.is_frozen:
        return False, (
            "Your account has been frozen due to a policy violation. "
            "Please contact support if you believe this is an error."
        ), "subscription_dashboard"

    if not subscription.can_use_designer_messenger():
        return False, (
            "Designer messaging requires an active subscription ($4.99/month or higher). "
            "Please upgrade your account to connect with other designers."
        ), "subscription_dashboard"

    return True, None, None
