"""Authentication helpers for keeping designer accounts healthy."""

from __future__ import annotations

from datetime import timedelta
from typing import Dict

from django.utils import timezone

from .models import DesignerProfile, UserSubscription


def ensure_designer_access(user) -> Dict[str, bool]:
    """Create dependent records so the designer dashboard always works.

    The legacy dataset contains users that were added manually without the
    expected ``DesignerProfile`` or ``UserSubscription`` rows. Missing records
    cause 500s across dashboard views and break the login experience. We invoke
    this helper after any successful authentication (and in recovery flows) to
    guarantee the prerequisites exist.

    Parameters
    ----------
    user:
        Any authenticated user instance.  ``None`` is tolerated to simplify
        signal usage.

    Returns
    -------
    dict
        Flags describing whether we created the profile and/or subscription.
    """

    created_profile = False
    created_subscription = False

    if user is None:
        return {"profile_created": created_profile, "subscription_created": created_subscription}

    profile, created_profile = DesignerProfile.objects.get_or_create(user=user)

    trial_end = timezone.now() + timedelta(days=30)
    subscription_defaults: Dict[str, object] = {
        "plan": None,
        "status": "free_trial",
        "payment_method": None,
        "trial_start_date": timezone.now(),
        "trial_end_date": trial_end,
        "next_billing_date": trial_end,
    }

    subscription, created_subscription = UserSubscription.objects.get_or_create(
        user=user,
        defaults=subscription_defaults,
    )

    # Legacy rows may exist but miss the updated trial/billing metadata. Patch
    # any critical gaps without overwriting intentional data.
    fields_to_update = []
    if subscription.trial_end_date is None:
        subscription.trial_end_date = trial_end
        fields_to_update.append("trial_end_date")
    if subscription.next_billing_date is None:
        subscription.next_billing_date = trial_end
        fields_to_update.append("next_billing_date")
    if subscription.status == "" or subscription.status is None:
        subscription.status = "free_trial"
        fields_to_update.append("status")

    if fields_to_update:
        subscription.save(update_fields=fields_to_update)

    try:
        from .services.referrals import ensure_referral_profile
        ensure_referral_profile(user)
    except Exception:
        pass  # Don't block login if referral system fails

    return {"profile_created": created_profile, "subscription_created": created_subscription}

