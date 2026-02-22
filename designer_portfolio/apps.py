# designer_portfolio/apps.py
from django.apps import AppConfig


class DesignerPortfolioConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "designer_portfolio"

    def ready(self):
        # Register signal handlers (e.g., bootstrap legacy accounts on login)
        import designer_portfolio.signals  # noqa: F401
        self._add_custom_domains_to_allowed_hosts()

    def _add_custom_domains_to_allowed_hosts(self):
        """Add student portfolio custom domains to ALLOWED_HOSTS so Django accepts requests."""
        from django.conf import settings

        if not getattr(settings, "STUDENT_PORTFOLIO_CUSTOM_DOMAIN_ENABLED", True):
            return
        try:
            from django.apps import apps

            if not apps.models_ready:
                return
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
