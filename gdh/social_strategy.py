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

    def build_absolute_uri(self, path=None):
        base_url = (getattr(settings, "BASE_URL_SERVER", "") or "").strip().rstrip("/")

        if base_url and isinstance(path, str) and path.startswith("/"):
            return urljoin(f"{base_url}/", path.lstrip("/"))

        return super().build_absolute_uri(path)
