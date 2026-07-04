from __future__ import annotations

from typing import Any, Iterable

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from designer_portfolio.models import DesignerProfile, UserSubscription


class Command(BaseCommand):
    help = (
        "Inspect a user's account details to troubleshoot authentication issues. "
        "Pass a username or email address to see matching users, whether they are "
        "active, have a usable password, and related profile/subscription metadata."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "identifier",
            help="Username or email to look up (case-insensitive).",
        )
        parser.add_argument(
            "--reactivate",
            action="store_true",
            help="If provided, set is_active=True on any matching inactive user records.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        identifier: str = (options.get("identifier") or "").strip()
        reactivate: bool = bool(options.get("reactivate"))

        if not identifier:
            raise CommandError("Provide a username or email address to inspect.")

        UserModel = get_user_model()
        matching_users = list(
            UserModel.objects.filter(
                Q(username__iexact=identifier) | Q(email__iexact=identifier)
            ).order_by("id")
        )

        if not matching_users:
            self.stdout.write(self.style.ERROR(f"No users match '{identifier}'."))
            # Offer a hint for near matches by username/email fragments
            suggestions = self._suggest_partial_matches(UserModel, identifier)
            if suggestions:
                self.stdout.write("Close matches (case-insensitive contains):")
                for suggestion in suggestions:
                    self.stdout.write(f"  - {suggestion}")
            return

        for user in matching_users:
            self._emit_user_summary(user)

            if reactivate and not user.is_active:
                user.is_active = True
                user.save(update_fields=["is_active"])
                self.stdout.write(self.style.SUCCESS("  -> Reactivated"))

    # ---- helpers -----------------------------------------------------

    def _emit_user_summary(self, user) -> None:
        header = f"User #{user.id} - username='{user.username}'"
        if user.email:
            header += f", email='{user.email}'"
        self.stdout.write(header)

        self.stdout.write(
            "  "
            + ", ".join(
                [
                    f"active={user.is_active}",
                    f"staff={user.is_staff}",
                    f"superuser={user.is_superuser}",
                    f"usable_password={user.has_usable_password()}",
                ]
            )
        )
        self.stdout.write(
            "  "
            + ", ".join(
                [
                    f"date_joined={self._format_dt(user.date_joined)}",
                    f"last_login={self._format_dt(user.last_login)}",
                ]
            )
        )

        profile = self._get_profile(user)
        if profile is None:
            self.stdout.write("  designer_profile: missing")
        else:
            self.stdout.write(
                "  designer_profile: present"
                + (f", template={profile.portfolio_template}" if profile.portfolio_template else "")
            )

        subscription = self._get_subscription(user)
        if subscription is None:
            self.stdout.write("  subscription: missing")
        else:
            self.stdout.write(
                "  subscription: "
                + ", ".join(
                    [
                        f"status={subscription.status}",
                        f"plan={subscription.plan.display_name if subscription.plan else 'None'}",
                        f"trial_end={self._format_dt(subscription.trial_end_date)}",
                        f"next_billing={self._format_dt(subscription.next_billing_date)}",
                    ]
                )
            )

        social_summary = self._describe_social_accounts(user)
        if social_summary:
            self.stdout.write("  social accounts: " + ", ".join(social_summary))

        self.stdout.write("")

    def _format_dt(self, value) -> str:
        if not value:
            return "None"
        return value.isoformat(timespec="seconds")

    def _get_profile(self, user) -> DesignerProfile | None:
        try:
            return user.designer_profile
        except DesignerProfile.DoesNotExist:
            return None

    def _get_subscription(self, user) -> UserSubscription | None:
        try:
            return user.subscription
        except UserSubscription.DoesNotExist:
            return None

    def _describe_social_accounts(self, user) -> Iterable[str]:
        if not hasattr(user, "social_auth"):
            return []
        return [f"{assoc.provider}:{assoc.uid}" for assoc in user.social_auth.all()]

    def _suggest_partial_matches(self, UserModel, identifier: str) -> list[str]:
        trimmed = identifier.strip()
        if len(trimmed) < 3:
            return []
        qs = UserModel.objects.filter(
            Q(username__icontains=trimmed) | Q(email__icontains=trimmed)
        ).order_by("username")[:5]
        return [f"username={user.username}, email={user.email}" for user in qs]
