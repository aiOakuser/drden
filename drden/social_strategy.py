from __future__ import annotations

from urllib.parse import urljoin

from django.conf import settings
from social_django.strategy import DjangoStrategy


class CanonicalDjangoStrategy(DjangoStrategy):
    """
    Build absolute OAuth callback URLs from BASE_URL_SERVER when available.

    This avoids proxy/internal host leakage (e.g. 127.0.0.1 or 172.x.x.x)
    into provider redirect_uri values.
    """

    @staticmethod
    def _is_local_host(host: str) -> bool:
        normalized = (host or "").split(":", 1)[0].strip().lower()
        return normalized in {"127.0.0.1", "localhost"}

    def build_absolute_uri(self, path=None):
        base_url = (getattr(settings, "BASE_URL_SERVER", "") or "").strip().rstrip("/")
        request_host = ""
        if getattr(self, "request", None) is not None:
            request_host = self.request.get_host() or ""

        # Keep local OAuth flows on localhost/127.0.0.1 so the session/state cookie
        # remains on the same origin during the full provider round-trip.
        if base_url and isinstance(path, str) and path.startswith("/") and not self._is_local_host(request_host):
            return urljoin(f"{base_url}/", path.lstrip("/"))

        return super().build_absolute_uri(path)
