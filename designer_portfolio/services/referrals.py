"""
Referral system: invite links, crediting, tiers, leaderboard.
Credit is applied only on signup (inside one transaction).
"""
from __future__ import annotations

import hashlib
import secrets
import string
from typing import Optional

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

User = get_user_model()

# Advertised bonus per successful referral. There is no automated payout in
# this codebase yet — crediting only increments referral_count/points/tier.
# Actual disbursement is handled manually until a payout flow is built.
REFERRAL_BONUS_USD = 100


def generate_referral_code(prefix: str = "drden") -> str:
    alphabet = string.ascii_lowercase + string.digits
    return f"{prefix}-" + "".join(secrets.choice(alphabet) for _ in range(8))


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _unique_code_for_profile() -> str:
    from designer_portfolio.models import UserReferralProfile

    for _ in range(10):
        code = generate_referral_code("drden")
        if not UserReferralProfile.objects.filter(referral_code=code).exists():
            return code
    raise RuntimeError("Could not generate unique referral code")


def ensure_referral_profile(user) -> "UserReferralProfile":
    """Create or return UserReferralProfile for user. Assigns unique referral_code if missing."""
    from designer_portfolio.models import UserReferralProfile

    profile, created = UserReferralProfile.objects.get_or_create(
        user=user,
        defaults={"referral_code": _unique_code_for_profile()},
    )
    if not created and not profile.referral_code:
        profile.referral_code = _unique_code_for_profile()
        profile.save(update_fields=["referral_code"])
    return profile


def compute_tier(referral_count: int) -> Optional["ReferralTier"]:
    from designer_portfolio.models import ReferralTier

    return (
        ReferralTier.objects.filter(is_active=True, min_referrals__lte=referral_count)
        .order_by("-min_referrals")
        .first()
    )


@transaction.atomic
def credit_referral_on_signup(
    *,
    user: User,
    referral_code: Optional[str] = None,
    source: Optional[str] = None,
    ip: Optional[str] = None,
    ua: Optional[str] = None,
) -> "UserReferralProfile":
    """
    Call after user is created. Credits referrer if code valid.
    Ensures referral crediting happens only once and is race-safe.
    """
    from designer_portfolio.models import (
        UserReferralProfile,
        ReferralEvent,
        ReferralTier,
        DesignerProfile,
    )

    profile = ensure_referral_profile(user)

    if not referral_code:
        return profile

    referrer_profile = (
        UserReferralProfile.objects.select_for_update()
        .select_related("user")
        .filter(referral_code=referral_code)
        .first()
    )
    if not referrer_profile:
        return profile

    if referrer_profile.user_id == user.id:
        return profile  # self-referral

    if profile.referred_by_id is not None:
        return profile  # already referred

    try:
        ReferralEvent.objects.create(
            referrer=referrer_profile.user,
            referred_user=user,
            referral_code=referral_code,
            source=source,
            ip_hash=_hash(ip) if ip else None,
            user_agent_hash=_hash(ua) if ua else None,
        )
    except Exception:
        return profile

    profile.referred_by = referrer_profile.user
    profile.referral_joined_at = timezone.now()
    profile.save(update_fields=["referred_by", "referral_joined_at"])

    referrer_profile.referral_count = referrer_profile.referral_count + 1
    referrer_profile.referral_points = referrer_profile.referral_points + 1
    new_tier = compute_tier(referrer_profile.referral_count)
    referrer_profile.current_tier = new_tier
    referrer_profile.save(update_fields=["referral_count", "referral_points", "current_tier"])

    try:
        dp = DesignerProfile.objects.get(user=user)
        dp.referred_by = referrer_profile.user
        dp.save(update_fields=["referred_by"])
    except DesignerProfile.DoesNotExist:
        pass

    return profile


def next_tier_info(profile: "UserReferralProfile") -> dict:
    """Return next tier and progress for dashboard."""
    from designer_portfolio.models import ReferralTier, UserReferralProfile

    tiers = list(ReferralTier.objects.filter(is_active=True).order_by("min_referrals"))
    next_tier = next(
        (t for t in tiers if t.min_referrals > profile.referral_count),
        None,
    )
    if not next_tier:
        return {"next": None, "progress": None}
    return {
        "next": {
            "code": next_tier.code,
            "name": next_tier.name,
            "min_referrals": next_tier.min_referrals,
        },
        "progress": {
            "current": profile.referral_count,
            "target": next_tier.min_referrals,
        },
    }
