import os

from django.conf import settings
from django.db.models import Q
from django.http import HttpRequest

from .models import Design, DesignerProfile, DressOrder


def messenger_inbox_count(request: HttpRequest) -> dict:
    """Expose conversation count for navbar 'Inbox (N)' when user is authenticated."""
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {"messenger_inbox_count": None}
    try:
        from .models import ChatConversation

        count = ChatConversation.objects.filter(
            Q(user1=user) | Q(user2=user)
        ).count()
        return {"messenger_inbox_count": count}
    except Exception:
        return {"messenger_inbox_count": None}


def _google_oauth_ready() -> bool:
    """Check if Google OAuth is configured (from settings or GOOGLE_* env fallback)."""
    key = getattr(settings, "SOCIAL_AUTH_GOOGLE_OAUTH2_KEY", "") or ""
    secret = getattr(settings, "SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET", "") or ""
    if key and secret:
        return True
    return bool((os.getenv("GOOGLE_CLIENT_ID") or "").strip() and (os.getenv("GOOGLE_CLIENT_SECRET") or "").strip())


def social_login_providers(request: HttpRequest) -> dict:
    """Expose enabled social login providers for auth modal and login page."""
    providers = []
    if _google_oauth_ready():
        providers.append({"backend": "google-oauth2", "label": "Google", "css_class": "google", "icon": "G"})
    return {"social_login_providers": providers}


def dashboard_counts(request: HttpRequest) -> dict:
    """Provide commonly used dashboard counts for the authenticated user.

    Returns zeros when the user is anonymous to keep templates simple.
    """
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {
            "total_designs": 0,
            "designs_with_techpack_count": 0,
            "published_designs_count": 0,
            "new_orders_count": 0,
        }

    user_designs = Design.objects.filter(designer=user)

    designs_with_techpack = user_designs.filter(
        Q(techpack_pdf__isnull=False) | Q(techpack_excel__isnull=False)
    )

    new_orders_count = 0
    try:
        profile = DesignerProfile.objects.get(user=user)
        new_orders_count = DressOrder.objects.filter(designer=profile, status="new").count()
    except DesignerProfile.DoesNotExist:
        pass

    return {
        "total_designs": user_designs.count(),
        "designs_with_techpack_count": designs_with_techpack.count(),
        "published_designs_count": user_designs.filter(published=True).count(),
        "new_orders_count": new_orders_count,
    }


def active_portfolio_template(request: HttpRequest) -> dict:
    """Expose the active portfolio template key and css path.

    Falls back to the global default (classic) if no authenticated user/profile.
    """
    default_key = "classic"
    user = getattr(request, "user", None)
    template_key = default_key

    if user is not None and user.is_authenticated:
        try:
            profile: DesignerProfile = DesignerProfile.objects.get(user=user)
            template_key = getattr(profile, "portfolio_template", default_key) or default_key
        except (DesignerProfile.DoesNotExist, AttributeError, Exception):
            template_key = default_key

    # Ensure template key maps to an existing file (classic, modern, minimal)
    if template_key not in ("classic", "modern", "minimal"):
        template_key = default_key
    css_path = f"css/templates/{template_key}.css"
    return {
        "portfolio_template_key": template_key,
        "portfolio_template_css": css_path,
    }


def referral_context(request: HttpRequest) -> dict:
    """Expose referral invite URL for authenticated designers (used in chat widget)."""
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {"referral_invite_url": None, "referral_code": None}

    try:
        from .services.referrals import ensure_referral_profile

        profile = ensure_referral_profile(user)
        base_url = getattr(settings, "BASE_URL_SERVER", "").strip()
        if not base_url:
            base_url = request.build_absolute_uri("/").rstrip("/")
        invite_url = f"{base_url}/invite/{profile.referral_code}/"
        return {"referral_invite_url": invite_url, "referral_code": profile.referral_code}
    except Exception:
        return {"referral_invite_url": None, "referral_code": None}


def google_review_url(request: HttpRequest) -> dict:
    """Expose the Google review URL so templates can link to it."""
    return {"google_review_url": getattr(settings, "GOOGLE_REVIEW_URL", "") or ""}


def utm_context(request: HttpRequest) -> dict:
    """Expose stored UTM and attribution values to templates.

    Values are primarily sourced from the session, populated by UTMTrackingMiddleware.
    """
    utm = getattr(request, "utm", None) or request.session.get("utm", {}) or {}
    return {
        "utm": utm,
        "utm_source": utm.get("utm_source", ""),
        "utm_medium": utm.get("utm_medium", ""),
        "utm_campaign": utm.get("utm_campaign", ""),
        "utm_content": utm.get("utm_content", ""),
        "utm_term": utm.get("utm_term", ""),
        "utm_landing_page": utm.get("landing_page", ""),
        "utm_initial_referrer": utm.get("initial_referrer", ""),
    }
