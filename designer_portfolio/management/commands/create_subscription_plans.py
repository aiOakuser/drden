from django.core.management.base import BaseCommand
from designer_portfolio.models import SubscriptionPlan


class Command(BaseCommand):
    help = 'Create default subscription plans'

    def handle(self, *args, **options):
        plans = [
            {
                'name': 'weekly',
                'display_name': 'Weekly Plan',
                'price': 2.99,
                'duration_days': 7,
            },
            {
                'name': 'biweekly',
                'display_name': 'Bi-Weekly Plan',
                'price': 3.99,
                'duration_days': 14,
            },
            {
                'name': 'monthly',
                'display_name': 'Monthly Plan',
                'price': 4.99,
                'duration_days': 30,
            },
            {
                'name': '6months',
                'display_name': '6 Months Plan',
                'price': 23.99,
                'duration_days': 180,
            },
            {
                'name': 'yearly',
                'display_name': 'Yearly Plan',
                'price': 49.99,
                'duration_days': 365,
            },
        ]

        for plan_data in plans:
            plan, created = SubscriptionPlan.objects.get_or_create(
                name=plan_data['name'],
                defaults=plan_data
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created subscription plan: {plan.display_name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Subscription plan already exists: {plan.display_name}')
                )

        self.stdout.write(
            self.style.SUCCESS('Successfully set up subscription plans!')
        )