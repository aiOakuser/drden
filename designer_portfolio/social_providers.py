"""Social login provider catalog and helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from django.conf import settings


@dataclass(frozen=True)
class SocialLoginProvider:
    backend: str
    label: str
    css_class: str
    button_label: str
    icon_type: str  # google_svg | fontawesome
    icon_class: str = ""


def _provider_ready(key_attr: str, secret_attr: str) -> bool:
    key = (getattr(settings, key_attr, "") or "").strip()
    secret = (getattr(settings, secret_attr, "") or "").strip()
    return bool(key and secret)


def _google_oauth_ready() -> bool:
    return _provider_ready("SOCIAL_AUTH_GOOGLE_OAUTH2_KEY", "SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET")


def _linkedin_provider() -> SocialLoginProvider | None:
    if _provider_ready(
        "SOCIAL_AUTH_LINKEDIN_OPENIDCONNECT_KEY",
        "SOCIAL_AUTH_LINKEDIN_OPENIDCONNECT_SECRET",
    ):
        return SocialLoginProvider(
            backend="linkedin-openidconnect",
            label="LinkedIn",
            css_class="linkedin",
            button_label="Continue with LinkedIn",
            icon_type="fontawesome",
            icon_class="fab fa-linkedin-in",
        )
    if _provider_ready("SOCIAL_AUTH_LINKEDIN_OAUTH2_KEY", "SOCIAL_AUTH_LINKEDIN_OAUTH2_SECRET"):
        return SocialLoginProvider(
            backend="linkedin-oauth2",
            label="LinkedIn",
            css_class="linkedin",
            button_label="Continue with LinkedIn",
            icon_type="fontawesome",
            icon_class="fab fa-linkedin-in",
        )
    return None


def _catalog_builders() -> list[Callable[[], SocialLoginProvider | None]]:
    return [
        lambda: (
            SocialLoginProvider(
                backend="google-oauth2",
                label="Google",
                css_class="google",
                button_label="Continue with Google",
                icon_type="google_svg",
            )
            if _google_oauth_ready()
            else None
        ),
        lambda: (
            SocialLoginProvider(
                backend="facebook",
                label="Facebook",
                css_class="facebook",
                button_label="Continue with Facebook",
                icon_type="fontawesome",
                icon_class="fab fa-facebook-f",
            )
            if _provider_ready("SOCIAL_AUTH_FACEBOOK_KEY", "SOCIAL_AUTH_FACEBOOK_SECRET")
            else None
        ),
        _linkedin_provider,
        lambda: (
            SocialLoginProvider(
                backend="instagram",
                label="Instagram",
                css_class="instagram",
                button_label="Continue with Instagram",
                icon_type="fontawesome",
                icon_class="fab fa-instagram",
            )
            if _provider_ready("SOCIAL_AUTH_INSTAGRAM_KEY", "SOCIAL_AUTH_INSTAGRAM_SECRET")
            else None
        ),
    ]


def get_social_login_providers() -> list[dict]:
    """Return enabled providers as template-friendly dicts."""
    providers: list[dict] = []
    for builder in _catalog_builders():
        provider = builder()
        if provider is None:
            continue
        providers.append(
            {
                "backend": provider.backend,
                "label": provider.label,
                "css_class": provider.css_class,
                "button_label": provider.button_label,
                "icon_type": provider.icon_type,
                "icon_class": provider.icon_class,
                # Legacy key used by older templates.
                "icon": provider.label[:2].upper()
                if provider.icon_type != "google_svg"
                else "G",
            }
        )
    return providers
