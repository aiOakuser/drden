from __future__ import annotations

from typing import Callable, Dict, Iterable, Set

from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponsePermanentRedirect


UTM_PARAM_NAMES = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_content",
    "utm_term",
    # Common ad click identifiers
    "gclid",
    "fbclid",
    "ttclid",
    "msclkid",
}


def _should_capture(request: HttpRequest) -> bool:
    if request.method != "GET":
        return False
    path = request.path or ""
    if path.startswith("/admin"):
        return False
    if path.startswith("/static"):
        return False
    return True


class UTMTrackingMiddleware:
    """Persist first-touch UTM and attribution data into the session.

    - Captures standard UTM params and common click IDs on GET requests
    - Records initial landing page and initial referrer once
    - Exposes the dict on `request.utm` for convenient access
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        session_has_utm = isinstance(request.session.get("utm"), dict)
        utm_data: Dict[str, str] = request.session.get("utm", {}) if session_has_utm else {}

        if _should_capture(request):
            # Collect any UTM/click id params present on this request
            found_any_param = False
            for name in UTM_PARAM_NAMES:
                value = request.GET.get(name)
                if value and name not in utm_data:
                    utm_data[name] = value
                    found_any_param = True

            # Record first landing page only once (prefer when UTM present)
            if "landing_page" not in utm_data and (found_any_param or not session_has_utm):
                utm_data["landing_page"] = request.build_absolute_uri()

            # Record initial referrer once
            if "initial_referrer" not in utm_data:
                referrer = request.META.get("HTTP_REFERER", "")
                if referrer:
                    utm_data["initial_referrer"] = referrer

            if utm_data:
                request.session["utm"] = utm_data
                # Mark session as modified to ensure it is saved even if values are equal
                request.session.modified = True

        # Attach to request for templates/views
        request.utm = request.session.get("utm", {})

        response = self.get_response(request)
        return response


class CanonicalDomainRedirectMiddleware:
    """
    Ensure every request lands on the configured canonical hostname (e.g., globaldesignerhub.com).

    This keeps legacy hostnames such as www.globaldesignerhub.com or HTTP variants from serving
    stale content or bypassing the primary homepage experience.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response
        self.enabled: bool = bool(getattr(settings, "CANONICAL_DOMAIN_REDIRECT_ENABLED", False))
        self.canonical_host: str = (getattr(settings, "CANONICAL_HOST", "") or "").strip().lower()
        self.preferred_scheme: str = (getattr(settings, "CANONICAL_REDIRECT_SCHEME", "") or "").strip().lower()
        if self.preferred_scheme not in {"http", "https"}:
            self.preferred_scheme = ""
        self.alias_hosts: Set[str] = self._normalized_aliases(
            getattr(settings, "CANONICAL_REDIRECT_HOSTS", [])
        )

    @staticmethod
    def _normalized_aliases(hosts: Iterable[str]) -> Set[str]:
        normalized: Set[str] = set()
        for host in hosts or []:
            cleaned = CanonicalDomainRedirectMiddleware._normalize_host(host)
            if cleaned:
                normalized.add(cleaned)
        return normalized

    @staticmethod
    def _normalize_host(host: str) -> str:
        value = (host or "").strip().lower()
        if not value:
            return ""
        if value.startswith("["):
            closing = value.find("]")
            if closing != -1:
                return value[1:closing]
            return value.strip("[]")
        if ":" in value:
            value = value.split(":", 1)[0]
        return value

    def _target_scheme(self, request: HttpRequest) -> str:
        if self.preferred_scheme:
            return self.preferred_scheme
        return "https" if request.is_secure() else "http"

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if not self.enabled or not self.canonical_host:
            return self.get_response(request)

        host = self._normalize_host(request.get_host())
        if not host or host == self.canonical_host:
            return self.get_response(request)

        if host not in self.alias_hosts:
            return self.get_response(request)

        target_url = f"{self._target_scheme(request)}://{self.canonical_host}{request.get_full_path()}"
        return HttpResponsePermanentRedirect(target_url)
