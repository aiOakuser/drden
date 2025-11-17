from __future__ import annotations

import logging
import re
from typing import Callable, Dict, Iterable, List

from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse


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
