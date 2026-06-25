from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand
from django.test import RequestFactory

from designer_portfolio.social_providers import _google_oauth_ready
from gdh.social_strategy import CanonicalDjangoStrategy


class Command(BaseCommand):
    help = (
        "Print Google OAuth redirect URIs to add in Google Cloud Console "
        "(fixes Error 400: redirect_uri_mismatch)."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--port",
            type=int,
            default=8004,
            help="Local dev server port (default: 8004).",
        )

    def handle(self, *args, **options) -> None:
        port = options["port"]
        key = (getattr(settings, "SOCIAL_AUTH_GOOGLE_OAUTH2_KEY", "") or "").strip()
        if not _google_oauth_ready():
            self.stdout.write(self.style.ERROR("GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET are not configured."))
            return

        self.stdout.write(self.style.SUCCESS("Google OAuth is configured."))
        self.stdout.write(f"Client ID: {key[:20]}...{key[-20:]}" if len(key) > 44 else f"Client ID: {key}")
        self.stdout.write(f"BASE_URL_SERVER: {(getattr(settings, 'BASE_URL_SERVER', '') or '(not set)')}")
        self.stdout.write("")
        self.stdout.write("Add these Authorized redirect URIs in Google Cloud Console:")
        self.stdout.write("https://console.cloud.google.com/apis/credentials")
        self.stdout.write("")

        factory = RequestFactory()
        strategy = CanonicalDjangoStrategy(None)
        hosts = []
        if getattr(settings, "BASE_URL_SERVER", ""):
            parsed_host = settings.BASE_URL_SERVER.replace("https://", "").replace("http://", "").rstrip("/")
            hosts.append((parsed_host, settings.BASE_URL_SERVER.startswith("https://")))
            if parsed_host.startswith("www."):
                hosts.append((parsed_host[4:], True))
            elif parsed_host and "." in parsed_host:
                hosts.append((f"www.{parsed_host}", True))

        hosts.extend(
            [
                (f"127.0.0.1:{port}", False),
                (f"localhost:{port}", False),
            ]
        )

        seen: set[str] = set()
        for host, secure in hosts:
            request = factory.get("/", HTTP_HOST=host, secure=secure)
            strategy.request = request
            uri = strategy.build_absolute_uri("/auth/complete/google-oauth2/")
            if uri in seen:
                continue
            seen.add(uri)
            self.stdout.write(f"  {uri}")

        self.stdout.write("")
        self.stdout.write(
            "The port must match your runserver port. "
            "Example: python manage.py runserver 8004"
        )
