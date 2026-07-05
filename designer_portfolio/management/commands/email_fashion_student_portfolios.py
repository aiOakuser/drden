from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.mail import EmailMultiAlternatives
from django.urls import reverse
from django.utils.html import escape

from designer_portfolio.emails import _absolute_url, _coalesce_user_email
from designer_portfolio.models import StudentPortfolio, StudentPortfolioProject


class Command(BaseCommand):
    help = (
        "Email a summary list of public student portfolios that include a "
        "Fashion Design project (name, email, portfolio link, category)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--to",
            default="admin@aioak.net",
            help="Recipient email address (default: admin@aioak.net).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print the summary instead of sending an email.",
        )

    def handle(self, *args, **options):
        recipient = options["to"]
        dry_run = options["dry_run"]

        portfolios = (
            StudentPortfolio.objects.filter(
                visibility=StudentPortfolio.Visibility.PUBLIC,
                projects__category=StudentPortfolioProject.Category.FASHION_DESIGN,
            )
            .select_related("user")
            .distinct()
            .order_by("user__username")
        )

        rows = []
        for portfolio in portfolios:
            user = portfolio.user
            name = user.get_full_name() or user.username
            email = _coalesce_user_email(user)
            if not email:
                continue
            path = reverse("student_portfolio_public", args=[portfolio.share_slug])
            portfolio_url = _absolute_url(None, path)
            rows.append({"name": name, "email": email, "url": portfolio_url})

        if not rows:
            self.stdout.write(self.style.WARNING("No public fashion design student portfolios found."))
            return

        text_lines = [f"{r['name']} <{r['email']}> - {r['url']}" for r in rows]
        text_body = (
            f"{len(rows)} public student portfolio(s) featuring Fashion Design:\n\n"
            + "\n".join(text_lines)
        )
        html_rows = "".join(
            f"<tr><td>{escape(r['name'])}</td><td>{escape(r['email'])}</td>"
            f'<td><a href="{escape(r["url"])}">{escape(r["url"])}</a></td></tr>'
            for r in rows
        )
        html_body = (
            f"<p>{len(rows)} public student portfolio(s) featuring Fashion Design:</p>"
            f"<table border=1 cellpadding=6 cellspacing=0>"
            f"<tr><th>Name</th><th>Email</th><th>Portfolio</th></tr>{html_rows}</table>"
        )

        if dry_run:
            self.stdout.write(text_body)
            return

        message = EmailMultiAlternatives(
            subject=f"Fashion Design student portfolios ({len(rows)})",
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient],
        )
        message.attach_alternative(html_body, "text/html")
        message.send()

        self.stdout.write(self.style.SUCCESS(f"Sent {len(rows)} portfolio(s) to {recipient}."))
