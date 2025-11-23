"""Reusable email helpers for authentication events."""

from __future__ import annotations

from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse


def _coalesce_user_email(user) -> str:
    """Return the best email address we can find for a user."""

    email = (getattr(user, "email", "") or "").strip()
    if email:
        return email

    profile = getattr(user, "designer_profile", None)
    if profile:
        fallback = (getattr(profile, "contact_email", "") or "").strip()
        if fallback:
            return fallback

    return ""


def _absolute_url(request, path: str) -> str:
    """Build an absolute URL even when a request object is missing."""

    if path and path.startswith(("http://", "https://")):
        return path

    if request is not None:
        return request.build_absolute_uri(path)

    base_url = getattr(settings, "BASE_URL_SERVER", "") or ""
    base_url = base_url.rstrip("/")
    if not base_url:
        return path
    return f"{base_url}{path}"


def _site_name() -> str:
    return getattr(settings, "SITE_NAME", "GlobalDesignerHub")


def send_registration_notifications(user, *, request=None, source: str = "password"):
    """Send welcome/administrative emails after a successful registration."""

    login_url = _absolute_url(request, reverse("login"))
    dashboard_url = _absolute_url(request, reverse("designer_dashboard"))
    subject = f"Welcome to {_site_name()}!"

    recipient = _coalesce_user_email(user)
    if recipient:
        message = (
            f"Hi {user.get_full_name() or user.username},\n\n"
            f"Welcome to {_site_name()} — you're all set.\n"
            f"You can manage your portfolio from {dashboard_url} and update your account anytime.\n\n"
            f"Sign in again here: {login_url}\n\n"
            "If you weren't expecting this email, contact support immediately."
        )
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=True,
        )

    admin_email = (getattr(settings, "ADMIN_EMAIL", "") or "").strip()
    if admin_email:
        profile = getattr(user, "designer_profile", None)
        website = getattr(profile, "portfolio_website", "") if profile else ""
        message = (
            f"A new account was created on {_site_name()} via {source}.\n\n"
            f"Username: {user.username}\n"
            f"Email: {recipient or 'N/A'}\n"
            f"Website: {website or 'N/A'}\n"
            f"Dashboard: {dashboard_url}\n"
        )
        send_mail(
            subject=f"[{_site_name()}] New registration ({user.username})",
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[admin_email],
            fail_silently=True,
        )


def notify_password_reset_request(user, *, request=None):
    """Alert administrators that a password reset was requested."""

    admin_email = (getattr(settings, "ADMIN_EMAIL", "") or "").strip()
    if not admin_email:
        return

    recipient = _coalesce_user_email(user)
    request_meta = getattr(request, "META", {}) or {}
    ip_address = request_meta.get("REMOTE_ADDR", "unknown")
    message = (
        f"{user.get_username()} requested a password reset on {_site_name()}.\n\n"
        f"Primary email: {recipient or 'N/A'}\n"
        f"IP (if available): {ip_address}\n"
        f"Login page: {_absolute_url(request, reverse('login'))}\n"
    )
    send_mail(
        subject=f"[{_site_name()}] Password reset requested",
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[admin_email],
        fail_silently=True,
    )


def notify_user_password_reset_completion(user, *, request=None):
    """Let the account owner know their password has been updated."""

    recipient = _coalesce_user_email(user)
    if not recipient:
        return

    login_url = _absolute_url(request, reverse("login"))
    message = (
        f"Hi {user.get_full_name() or user.username},\n\n"
        "This is a confirmation that your password was successfully reset. "
        "If you did not perform this action, please reset your password again immediately "
        f"and contact support.\n\nSign back in: {login_url}"
    )
    send_mail(
        subject=f"Your {_site_name()} password was changed",
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[recipient],
        fail_silently=True,
    )


def notify_problem_report(report, *, request=None):
    """Alert admins whenever a new problem report is submitted."""

    admin_email = (getattr(settings, "ADMIN_EMAIL", "") or "").strip()
    if not admin_email:
        return

    issue_url = (report.page_url or "").strip()
    if issue_url and request is not None and issue_url.startswith("/"):
        issue_url = request.build_absolute_uri(issue_url)

    reporter_name = report.reporter_display_name
    message = (
        f"A new issue was reported on {_site_name()}.\n\n"
        f"Category: {report.get_category_display()}\n"
        f"Subject: {report.subject}\n"
        f"From: {reporter_name} <{report.email}>\n"
        f"Page: {issue_url or 'n/a'}\n"
        f"IP: {report.ip_address or 'n/a'}\n"
        f"User agent: {report.user_agent or 'n/a'}\n\n"
        f"Message:\n{report.message}\n"
    )

    send_mail(
        subject=f"[{_site_name()}] New problem report",
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[admin_email],
        fail_silently=True,
    )
