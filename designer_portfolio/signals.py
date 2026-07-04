# designer_portfolio/signals.py
import logging

from django.db.models.signals import post_save, post_migrate
from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings

from .auth_utils import ensure_designer_access
from .core_designers import ensure_core_designers

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def notify_designer_on_approval(sender, instance, created, **kwargs):
    """
    When an admin activates a user account, send them an approval email.
    """
    if not created and instance.is_active:  # not a new signup, but updated
        send_mail(
            subject="Your designer Designer Account Has Been Approved 🎉",
            message=(
                f"Hello {instance.username},\n\n"
                "Good news! Your designer account has been approved. "
                "You can now log in and upload your designs + techpacks.\n\n"
                "Login here: https://designrden.com/login\n\n"
                "Best,\nTeam designer"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[instance.email],
            fail_silently=True,
        )


@receiver(user_logged_in)
def bootstrap_designer_after_login(sender, user, request, **kwargs):
    """Ensure legacy accounts gain the required related records on login."""
    ensure_designer_access(user)


@receiver(post_migrate)
def ensure_seed_designers(sender, **kwargs):
    """
    Automatically repopulate the canonical designer accounts after migrations,
    which is especially helpful on fresh production restores.
    """
    if sender.name != "designer_portfolio":
        return

    summary = ensure_core_designers()
    if any(summary.values()):
        logger.info(
            "Seeded designer users after migrate: created=%s activated=%s profiles_updated=%s",
            summary["created"],
            summary["activated"],
            summary["profiles_updated"],
        )
