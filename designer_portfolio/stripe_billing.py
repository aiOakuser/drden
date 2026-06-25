"""Stripe Checkout, SetupIntent, and webhook helpers for designer memberships."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone as dt_timezone
from typing import Any

import stripe
from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone

from .membership_plans import BillingInterval, get_membership_plan
from .models import UserSubscription

logger = logging.getLogger(__name__)


class StripeBillingError(Exception):
    """Raised when Stripe is misconfigured or an API call fails."""


def is_configured() -> bool:
    return bool(getattr(settings, "STRIPE_SECRET_KEY", ""))


def _configure_stripe() -> None:
    if not is_configured():
        raise StripeBillingError("Stripe is not configured.")
    stripe.api_key = settings.STRIPE_SECRET_KEY


def ensure_user_subscription(user: User) -> UserSubscription:
    subscription, _ = UserSubscription.objects.get_or_create(
        user=user,
        defaults={
            "status": "free_trial",
            "payment_method": None,
            "trial_end_date": timezone.now() + timedelta(days=30),
            "next_billing_date": timezone.now() + timedelta(days=30),
        },
    )
    return subscription


def ensure_stripe_customer(subscription: UserSubscription, user: User) -> str:
    _configure_stripe()
    if subscription.stripe_customer_id:
        return subscription.stripe_customer_id

    customer = stripe.Customer.create(
        email=(user.email or "").strip() or None,
        name=user.get_full_name() or user.username,
        metadata={"user_id": str(user.pk), "username": user.username},
    )
    subscription.stripe_customer_id = customer.id
    subscription.save(update_fields=["stripe_customer_id", "updated_at"])
    return customer.id


def create_membership_checkout_session(
    *,
    user: User,
    plan_slug: str,
    interval: BillingInterval,
    success_url: str,
    cancel_url: str,
) -> stripe.checkout.Session:
    plan = get_membership_plan(plan_slug)
    if plan is None:
        raise StripeBillingError("Unknown membership plan.")

    price_id = plan.stripe_price_id(interval)
    if not price_id:
        raise StripeBillingError(
            f"Stripe price is not configured for {plan.name} ({interval})."
        )

    subscription = ensure_user_subscription(user)
    customer_id = ensure_stripe_customer(subscription, user)
    _configure_stripe()

    return stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url + ("&" if "?" in success_url else "?") + "checkout=success",
        cancel_url=cancel_url,
        metadata={
            "user_id": str(user.pk),
            "plan_slug": plan_slug,
            "interval": interval,
        },
        subscription_data={
            "metadata": {
                "user_id": str(user.pk),
                "plan_slug": plan_slug,
                "interval": interval,
            }
        },
        allow_promotion_codes=True,
    )


def create_setup_intent(user: User) -> stripe.SetupIntent:
    subscription = ensure_user_subscription(user)
    customer_id = ensure_stripe_customer(subscription, user)
    _configure_stripe()
    return stripe.SetupIntent.create(
        customer=customer_id,
        automatic_payment_methods={"enabled": True},
        metadata={"user_id": str(user.pk)},
    )


def get_default_payment_method_summary(customer_id: str) -> dict[str, str] | None:
    if not customer_id or not is_configured():
        return None

    _configure_stripe()
    customer = stripe.Customer.retrieve(
        customer_id,
        expand=["invoice_settings.default_payment_method"],
    )
    default_pm = customer.get("invoice_settings", {}).get("default_payment_method")
    if not default_pm or isinstance(default_pm, str):
        payment_methods = stripe.PaymentMethod.list(customer=customer_id, type="card", limit=1)
        if not payment_methods.data:
            return None
        pm = payment_methods.data[0]
    else:
        pm = default_pm

    card = pm.get("card") or {}
    brand = (card.get("brand") or "card").replace("_", " ").title()
    last4 = card.get("last4") or "????"
    wallet = (pm.get("card") or {}).get("wallet") or {}
    wallet_type = wallet.get("type") if isinstance(wallet, dict) else None
    label = "Stripe Link" if wallet_type == "link" else f"{brand} ···· {last4}"
    return {"label": label, "brand": brand, "last4": last4}


def cancel_stripe_subscription(subscription: UserSubscription) -> None:
    if not subscription.stripe_subscription_id:
        return
    _configure_stripe()
    stripe.Subscription.modify(
        subscription.stripe_subscription_id,
        cancel_at_period_end=True,
    )


def _stripe_ts_to_datetime(value: int | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromtimestamp(value, tz=dt_timezone.utc)


def apply_checkout_session(session: dict[str, Any]) -> None:
    user_id = (session.get("metadata") or {}).get("user_id")
    if not user_id:
        return

    try:
        subscription = UserSubscription.objects.select_related("user").get(user_id=int(user_id))
    except (UserSubscription.DoesNotExist, ValueError, TypeError):
        logger.warning("Stripe checkout for unknown user_id=%s", user_id)
        return

    plan_slug = (session.get("metadata") or {}).get("plan_slug", "")
    interval = (session.get("metadata") or {}).get("interval", "monthly")
    stripe_subscription_id = session.get("subscription")
    customer_id = session.get("customer")

    update_fields = ["updated_at"]
    if customer_id and subscription.stripe_customer_id != customer_id:
        subscription.stripe_customer_id = customer_id
        update_fields.append("stripe_customer_id")
    if stripe_subscription_id:
        subscription.stripe_subscription_id = stripe_subscription_id
        update_fields.append("stripe_subscription_id")

    subscription.payment_method = "stripe"
    subscription.status = "active"
    subscription.membership_tier = plan_slug or subscription.membership_tier
    subscription.billing_interval = interval or subscription.billing_interval
    subscription.subscription_start_date = timezone.now()
    subscription.last_payment_date = timezone.now()
    subscription.auto_renewal = True
    update_fields.extend(
        [
            "payment_method",
            "status",
            "membership_tier",
            "billing_interval",
            "subscription_start_date",
            "last_payment_date",
            "auto_renewal",
        ]
    )
    subscription.save(update_fields=update_fields)

    if stripe_subscription_id:
        sync_stripe_subscription(stripe_subscription_id)

    try:
        from .emails import notify_membership_activated

        notify_membership_activated(subscription)
    except Exception:
        logger.exception("Failed to send membership activation email for user_id=%s", user_id)


def sync_stripe_subscription(stripe_subscription_id: str) -> None:
    _configure_stripe()
    stripe_sub = stripe.Subscription.retrieve(stripe_subscription_id)
    user_id = (stripe_sub.get("metadata") or {}).get("user_id")
    if not user_id:
        customer_id = stripe_sub.get("customer")
        subscription = UserSubscription.objects.filter(stripe_customer_id=customer_id).first()
    else:
        subscription = UserSubscription.objects.filter(user_id=int(user_id)).first()

    if subscription is None:
        logger.warning("No local subscription for Stripe sub %s", stripe_subscription_id)
        return

    plan_slug = (stripe_sub.get("metadata") or {}).get("plan_slug")
    interval = (stripe_sub.get("metadata") or {}).get("interval")
    status = stripe_sub.get("status", "")
    period_end = _stripe_ts_to_datetime(stripe_sub.get("current_period_end"))

    subscription.stripe_subscription_id = stripe_sub.id
    subscription.payment_method = "stripe"
    if plan_slug:
        subscription.membership_tier = plan_slug
    if interval:
        subscription.billing_interval = interval
    if period_end:
        subscription.subscription_end_date = period_end
        subscription.next_billing_date = period_end

    if status in {"active", "trialing"}:
        subscription.status = "active"
        subscription.auto_renewal = not stripe_sub.get("cancel_at_period_end", False)
    elif status == "past_due":
        subscription.status = "past_due"
    elif status in {"canceled", "unpaid"}:
        subscription.status = "canceled" if status == "canceled" else "expired"
        subscription.auto_renewal = False

    subscription.save()


def handle_webhook_event(payload: bytes, signature: str) -> None:
    webhook_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", "")
    if not webhook_secret:
        raise StripeBillingError("Stripe webhook secret is not configured.")

    _configure_stripe()
    event = stripe.Webhook.construct_event(payload, signature, webhook_secret)
    event_type = event["type"]
    data_object = event["data"]["object"]

    if event_type == "checkout.session.completed":
        apply_checkout_session(data_object)
    elif event_type in {
        "customer.subscription.updated",
        "customer.subscription.deleted",
    }:
        sync_stripe_subscription(data_object["id"])
    elif event_type == "invoice.payment_succeeded":
        customer_id = data_object.get("customer")
        subscription = UserSubscription.objects.filter(stripe_customer_id=customer_id).first()
        if subscription:
            subscription.last_payment_date = timezone.now()
            subscription.save(update_fields=["last_payment_date", "updated_at"])
    elif event_type == "setup_intent.succeeded":
        customer_id = data_object.get("customer")
        payment_method_id = data_object.get("payment_method")
        subscription = UserSubscription.objects.filter(stripe_customer_id=customer_id).first()
        if subscription:
            subscription.payment_method = "stripe"
            subscription.save(update_fields=["payment_method", "updated_at"])
        if customer_id and payment_method_id:
            _configure_stripe()
            stripe.Customer.modify(
                customer_id,
                invoice_settings={"default_payment_method": payment_method_id},
            )
