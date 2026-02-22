from django.core.management.base import BaseCommand
from designer_portfolio.models import StudentPortfolioPlan


class Command(BaseCommand):
    help = "Create default Student Portfolio Pro plan ($19.99/mo)"

    def handle(self, *args, **options):
        plan, created = StudentPortfolioPlan.objects.get_or_create(
            name=StudentPortfolioPlan.PLAN_KEY,
            defaults={
                "display_name": "Student Portfolio Pro",
                "price": StudentPortfolioPlan.PRICE,
                "duration_days": 30,
                "includes_custom_domain": True,
                "domain_free_years": StudentPortfolioPlan.DOMAIN_FREE_YEARS,
                "is_active": True,
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created: {plan}"))
        else:
            self.stdout.write(self.style.WARNING(f"Plan already exists: {plan}"))
