"""Create Stripe Products and recurring Prices for GDH designer memberships."""

from __future__ import annotations

from decimal import Decimal

import stripe
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from designer_portfolio.membership_plans import MEMBERSHIP_PLANS, BillingInterval


class Command(BaseCommand):
    help = (
        "Create Stripe Products and recurring Prices for designer membership tiers. "
        "Prints .env lines to paste into your environment."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print planned prices without calling Stripe.",
        )

    def handle(self, *args, **options):
        secret_key = (getattr(settings, "STRIPE_SECRET_KEY", "") or "").strip()
        if not secret_key and not options["dry_run"]:
            raise CommandError(
                "Set STRIPE_SECRET_KEY in .env first, or pass --dry-run to preview."
            )

        if secret_key:
            stripe.api_key = secret_key

        env_lines: list[str] = []
        env_map = {
            "professional_portfolio": (
                "STRIPE_PRICE_PROFESSIONAL_MONTHLY",
                "STRIPE_PRICE_PROFESSIONAL_YEARLY",
            ),
            "personal_designer_website": (
                "STRIPE_PRICE_PERSONAL_WEBSITE_MONTHLY",
                "STRIPE_PRICE_PERSONAL_WEBSITE_YEARLY",
            ),
            "premium_fashion_studio": (
                "STRIPE_PRICE_PREMIUM_STUDIO_MONTHLY",
                "STRIPE_PRICE_PREMIUM_STUDIO_YEARLY",
            ),
        }

        for plan in MEMBERSHIP_PLANS:
            monthly_var, yearly_var = env_map[plan.slug]
            if options["dry_run"]:
                self.stdout.write(
                    f"[dry-run] {plan.name}: monthly ${plan.monthly_price}, yearly ${plan.yearly_price}"
                )
                env_lines.append(f"{monthly_var}=price_dry_run_monthly_{plan.slug}")
                env_lines.append(f"{yearly_var}=price_dry_run_yearly_{plan.slug}")
                continue

            product = stripe.Product.create(
                name=f"GDH — {plan.name}",
                description=plan.tagline,
                metadata={"plan_slug": plan.slug, "site": "globaldesignerhub.com"},
            )
            self.stdout.write(self.style.SUCCESS(f"Product: {product.id} ({plan.name})"))

            monthly_price = self._create_price(
                product_id=product.id,
                amount=plan.monthly_price,
                interval="month",
                plan_slug=plan.slug,
            )
            yearly_price = self._create_price(
                product_id=product.id,
                amount=plan.yearly_price,
                interval="year",
                plan_slug=plan.slug,
            )
            env_lines.append(f"{monthly_var}={monthly_price.id}")
            env_lines.append(f"{yearly_var}={yearly_price.id}")

        self.stdout.write("")
        self.stdout.write("Add these to your .env:")
        for line in env_lines:
            self.stdout.write(line)
        self.stdout.write("")
        self.stdout.write(
            "Then configure a webhook endpoint POST /payment/stripe/webhook/ "
            "with events: checkout.session.completed, customer.subscription.updated, "
            "customer.subscription.deleted, invoice.payment_succeeded, setup_intent.succeeded"
        )

    def _create_price(
        self,
        *,
        product_id: str,
        amount: Decimal,
        interval: BillingInterval | str,
        plan_slug: str,
    ):
        stripe_interval = "year" if interval in {"year", "yearly"} else "month"
        price = stripe.Price.create(
            product=product_id,
            unit_amount=int(amount * 100),
            currency="usd",
            recurring={"interval": stripe_interval},
            metadata={"plan_slug": plan_slug, "interval": interval},
        )
        label = f"${amount:,.0f}/{stripe_interval}"
        self.stdout.write(f"  Price {price.id} — {label}")
        return price
