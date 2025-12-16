# designer_portfolio/apps.py
from django.apps import AppConfig


class DesignerPortfolioConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "designer_portfolio"

    def ready(self):
        # Register signal handlers (e.g., bootstrap legacy accounts on login)
        import designer_portfolio.signals  # noqa: F401
