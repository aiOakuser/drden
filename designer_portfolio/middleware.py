from __future__ import annotations

import logging
import re
from typing import Callable, Dict, Iterable, List, Set

from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse, HttpResponsePermanentRedirect

_DOMAIN_ALLOWED_HOSTS_INITIALIZED = False


def _ensure_custom_domains_in_allowed_hosts() -> None:
    """Add student portfolio custom domains to ALLOWED_HOSTS (lazy, on first request)."""
    global _DOMAIN_ALLOWED_HOSTS_INITIALIZED
    if _DOMAIN_ALLOWED_HOSTS_INITIALIZED:
        return
    if not getattr(settings, "STUDENT_PORTFOLIO_CUSTOM_DOMAIN_ENABLED", True):
        _DOMAIN_ALLOWED_HOSTS_INITIALIZED = True
        return
    try:
        from .models import StudentPortfolio

        for domain in StudentPortfolio.objects.filter(
            custom_domain__isnull=False
        ).exclude(custom_domain="").values_list("custom_domain", flat=True):
            if domain:
                for host in (domain, f"www.{domain}"):
                    if host and host not in settings.ALLOWED_HOSTS:
                        settings.ALLOWED_HOSTS.append(host)
    except Exception:
        pass  # Tables may not exist during migration
    _DOMAIN_ALLOWED_HOSTS_INITIALIZED = True


class CustomDomainAllowedHostsMiddleware:
    """
    Lazily populate ALLOWED_HOSTS with student portfolio custom domains on first request.
    Runs early so Django accepts requests to those hosts before host validation.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        _ensure_custom_domains_in_allowed_hosts()
        return self.get_response(request)


logger = logging.getLogger(__name__)


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


DEFAULT_SUSPICIOUS_PATH_PATTERNS: List[str] = [
    r"^/wp-admin(?:/|$)",
    r"^/wp-content(?:/|$)",
    r"^/wp-includes(?:/|$)",
    r"^/wordpress(?:/|$)",
    r"^/xmlrpc\.php(?:$|\?)",
    r"^/lander(?:/|$)",
    r"\.php(?:$|\?)",
]


def _compile_patterns(patterns: Iterable[str]) -> List[re.Pattern[str]]:
    compiled: List[re.Pattern[str]] = []
    for raw in patterns:
        value = (raw or "").strip()
        if not value:
            continue
        try:
            compiled.append(re.compile(value, re.IGNORECASE))
        except re.error:
            logger.warning("Ignoring invalid suspicious-path regex: %s", value)
    return compiled


def _get_configured_patterns() -> List[re.Pattern[str]]:
    configured = getattr(settings, "SUSPICIOUS_PATH_PATTERNS", None)

    if configured is None:
        source: Iterable[str] = DEFAULT_SUSPICIOUS_PATH_PATTERNS
    elif isinstance(configured, str):
        source = [configured]
    else:
        source = configured

    return _compile_patterns(source)


def _client_ip(request: HttpRequest) -> str:
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


class SuspiciousRequestThrottleMiddleware:
    """Drop obvious scanner traffic early and apply a simple IP throttle."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response
        self.enabled = getattr(settings, "SUSPICIOUS_REQUEST_FILTER_ENABLED", True)
        self.patterns = _get_configured_patterns()
        self.rate_limit = max(0, int(getattr(settings, "SUSPICIOUS_REQUEST_RATE_LIMIT", 60)))
        self.rate_window = max(1, int(getattr(settings, "SUSPICIOUS_REQUEST_RATE_WINDOW", 60)))

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if not self.enabled or not self.patterns:
            return self.get_response(request)

        path = request.path or ""
        if not path:
            return self.get_response(request)

        if not any(pattern.search(path) for pattern in self.patterns):
            return self.get_response(request)

        client_ip = _client_ip(request) or "unknown"
        if self._is_rate_limited(client_ip):
            logger.warning("Rate limited suspicious traffic from %s to %s", client_ip, path)
            response = HttpResponse(status=429)
            response["Retry-After"] = str(self.rate_window)
            response["X-Request-Filtered"] = "suspicious"
            return response

        logger.info("Filtered suspicious request from %s to %s", client_ip, path)
        response = HttpResponse(status=404)
        response["X-Request-Filtered"] = "suspicious"
        return response

    def _is_rate_limited(self, client_ip: str) -> bool:
        if self.rate_limit <= 0:
            return False

        cache_key = f"suspicious-rate:{client_ip}"
        hits = cache.get(cache_key, 0) + 1
        cache.set(cache_key, hits, self.rate_window)
        return hits > self.rate_limit


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


def _normalize_domain_for_lookup(host: str) -> str:
    """Normalize host for custom domain lookup: lowercase, strip port, strip www."""
    value = (host or "").strip().lower()
    if not value:
        return ""
    if ":" in value:
        value = value.split(":", 1)[0]
    if value.startswith("www."):
        value = value[4:]
    return value


class StudentPortfolioCustomDomainMiddleware:
    """
    When request Host matches a StudentPortfolio custom_domain (e.g. chpreddy.com),
    serve that portfolio as the response. Runs early so custom domains bypass normal routing.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response
        self.enabled = getattr(settings, "STUDENT_PORTFOLIO_CUSTOM_DOMAIN_ENABLED", True)

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if not self.enabled:
            return self.get_response(request)

        host = _normalize_domain_for_lookup(request.get_host())
        if not host:
            return self.get_response(request)

        try:
            from .models import StudentPortfolio

            portfolio = StudentPortfolio.objects.select_related("user").filter(
                custom_domain__iexact=host
            ).first()
            if not portfolio:
                return self.get_response(request)
        except Exception:
            return self.get_response(request)

        request.portfolio_from_custom_domain = portfolio
        from .student_portfolio_views import student_portfolio_public_view

        return student_portfolio_public_view(request, portfolio.share_slug)


class CanonicalDomainRedirectMiddleware:
    """
    Ensure every request lands on the configured canonical hostname (e.g., designrden.com).

    This keeps legacy hostnames such as www.designrden.com or HTTP variants from serving
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

        # Never redirect static/media assets. Redirects here can make CSS/JS/images
        # appear "not loading" when a site is deployed on a new hostname.
        path = request.path or ""
        if path.startswith("/static/") or path.startswith("/media/"):
            return self.get_response(request)

        host = self._normalize_host(request.get_host())
        if not host or host == self.canonical_host:
            return self.get_response(request)

        if host not in self.alias_hosts:
            return self.get_response(request)

        target_url = f"{self._target_scheme(request)}://{self.canonical_host}{request.get_full_path()}"
        # Important: for non-idempotent methods (POST/PUT/PATCH/DELETE), a 301 can
        # cause some clients to drop the request body or change the method to GET,
        # which breaks form submissions (e.g., login) and API calls.
        #
        # 308 is a permanent redirect that preserves method + body.
        if request.method in {"GET", "HEAD"}:
            return HttpResponsePermanentRedirect(target_url)

        response = HttpResponsePermanentRedirect(target_url)
        response.status_code = 308
        return response


class ForceHttpForLocalhostMiddleware:
    """
    When using runserver (127.0.0.1 / localhost), rewrite any redirect to https
    so it goes to http. Prevents ERR_SSL_PROTOCOL_ERROR when the browser or
    something upstream forces HTTPS.
    """
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        host = (request.get_host() or "").split(":")[0].lower()
        if host not in ("127.0.0.1", "localhost"):
            return response
        location = response.get("Location")
        if not location or not response.status_code in (301, 302, 307, 308):
            return response
        if location.strip().lower().startswith("https://"):
            new_location = "http://" + location[8:]
            response["Location"] = new_location
        return response
