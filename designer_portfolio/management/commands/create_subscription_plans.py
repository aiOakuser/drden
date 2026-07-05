from django.core.management.base import BaseCommand
from designer_portfolio.models import SubscriptionPlan


class Command(BaseCommand):
    help = 'Create or update default subscription plans'

    def handle(self, *args, **options):
        plans = [
            {
                'name': 'monthly',
                'display_name': 'Monthly Plan',
                'price': 19.99,
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
                'price': 199.99,
                'duration_days': 365,
            },
        ]

        for plan_data in plans:
            plan, created = SubscriptionPlan.objects.update_or_create(
                name=plan_data['name'],
                defaults=plan_data,
            )
            action = 'Created' if created else 'Updated'
            self.stdout.write(
                self.style.SUCCESS(f'{action} subscription plan: {plan.display_name} (${plan.price})')
            )

        # Weekly/bi-weekly are discontinued. Deactivate rather than delete so any
        # existing UserSubscription rows pointing at them don't break with a
        # dangling foreign key.
        retired = SubscriptionPlan.objects.filter(name__in=['weekly', 'biweekly'], is_active=True)
        retired_count = retired.update(is_active=False)
        if retired_count:
            self.stdout.write(
                self.style.WARNING(f'Deactivated {retired_count} retired plan(s): weekly, biweekly')
            )

        self.stdout.write(
            self.style.SUCCESS('Successfully set up subscription plans!')
        )