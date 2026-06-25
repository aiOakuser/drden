"""Designer membership tiers shown on the subscription dashboard."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from django.conf import settings

BillingInterval = Literal["monthly", "yearly"]


@dataclass(frozen=True)
class MembershipPlan:
    slug: str
    name: str
    monthly_price: Decimal
    yearly_price: Decimal
    tagline: str
    is_recommended: bool = False

    def stripe_price_id(self, interval: BillingInterval) -> str:
        mapping = getattr(settings, "STRIPE_MEMBERSHIP_PRICE_IDS", {})
        return (mapping.get(self.slug) or {}).get(interval, "")

    def price_for(self, interval: BillingInterval) -> Decimal:
        return self.yearly_price if interval == "yearly" else self.monthly_price

    def price_label(self, interval: BillingInterval) -> str:
        amount = self.price_for(interval)
        if interval == "yearly":
            return f"${amount:,.0f}/year"
        return f"${amount:,.0f}/month"


MEMBERSHIP_BENEFITS: tuple[str, ...] = (
    "Personalized Designer Profile",
    "Portfolio & Collections Showcase",
    "Tech Pack Storage",
    "Custom Designer URL",
    "Hosting & SSL",
    "SEO Optimization",
    "Lead Inquiry Forms",
    "Analytics Dashboard",
    "Ongoing Profile Maintenance",
)

MEMBERSHIP_PLANS: tuple[MembershipPlan, ...] = (
    MembershipPlan(
        slug="professional_portfolio",
        name="Professional Portfolio",
        monthly_price=Decimal("29"),
        yearly_price=Decimal("290"),
        tagline="Essential hub profile, portfolio showcase, and core tools.",
    ),
    MembershipPlan(
        slug="personal_designer_website",
        name="Personal Designer Website",
        monthly_price=Decimal("79"),
        yearly_price=Decimal("790"),
        tagline="Your own branded site with custom URL, hosting, SSL, SEO, and analytics.",
        is_recommended=True,
    ),
    MembershipPlan(
        slug="premium_fashion_studio",
        name="Premium Fashion Studio",
        monthly_price=Decimal("149"),
        yearly_price=Decimal("1490"),
        tagline="Studio-grade tools for larger collections and advanced workflows.",
    ),
)


def get_membership_plan(slug: str) -> MembershipPlan | None:
    for plan in MEMBERSHIP_PLANS:
        if plan.slug == slug:
            return plan
    return None


def list_membership_plans() -> list[MembershipPlan]:
    return list(MEMBERSHIP_PLANS)
