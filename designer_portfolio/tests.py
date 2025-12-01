import json
from unittest.mock import patch

from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from django.contrib.auth.models import User
from django.core import mail
from django.utils import timezone
from social_core.exceptions import AuthForbidden

from .models import DesignerProfile, UserSubscription, ProblemReport, Project
from .social_pipeline import generate_username, ensure_verified_email, sync_user_details
from .project_templates import load_project_templates


TEST_STORAGE_BACKENDS = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


@override_settings(
    SECURE_SSL_REDIRECT=False,
    SESSION_COOKIE_SECURE=False,
    CSRF_COOKIE_SECURE=False,
    STORAGES=TEST_STORAGE_BACKENDS,
)
class LoginFlowTests(TestCase):
    def setUp(self) -> None:
        self.password = "TestPass123!"
        self.user = User.objects.create_user(
            username="designer1",
            email="designer1@example.com",
            password=self.password,
            is_active=True,
        )

    def test_login_with_username_redirects_to_dashboard(self):
        response = self.client.post(
            reverse("login"),
            {"username": self.user.username, "password": self.password},
            follow=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers.get("Location"), reverse("designer_dashboard"))

    def test_login_with_email_redirects_to_dashboard(self):
        response = self.client.post(
            reverse("login"),
            {"username": self.user.email, "password": self.password},
            follow=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers.get("Location"), reverse("designer_dashboard"))

    @override_settings(REMEMBER_ME_SESSION_AGE=3600)
    def test_remember_me_sets_persistent_session(self):
        response = self.client.post(
            reverse("login"),
            {
                "username": self.user.username,
                "password": self.password,
                "remember_me": "on",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        session = self.client.session
        # Should NOT expire at browser close when remember me is set
        self.assertFalse(session.get_expire_at_browser_close())
        # Should be close to configured REMEMBER_ME_SESSION_AGE (>= 1 hour)
        self.assertGreaterEqual(session.get_expiry_age(), 3590)

    def test_without_remember_me_expires_on_browser_close(self):
        response = self.client.post(
            reverse("login"),
            {"username": self.user.username, "password": self.password},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        session = self.client.session
        # Should expire at browser close when remember me is not set
        self.assertTrue(session.get_expire_at_browser_close())

    def test_login_creates_required_related_records(self):
        self.assertFalse(DesignerProfile.objects.filter(user=self.user).exists())
        self.assertFalse(UserSubscription.objects.filter(user=self.user).exists())

        response = self.client.post(
            reverse("login"),
            {"username": self.user.username, "password": self.password, "remember_me": "on"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)

        self.assertTrue(DesignerProfile.objects.filter(user=self.user).exists())
        self.assertTrue(UserSubscription.objects.filter(user=self.user).exists())


@override_settings(
    SECURE_SSL_REDIRECT=False,
    SESSION_COOKIE_SECURE=False,
    CSRF_COOKIE_SECURE=False,
    STORAGES=TEST_STORAGE_BACKENDS,
)
class PasswordResetFlowTests(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(
            username="sleepy-designer",
            email="sleepy@example.com",
            password="unused",
            is_active=False,
        )
        # Simulate legacy account without required relations
        DesignerProfile.objects.filter(user=self.user).delete()
        UserSubscription.objects.filter(user=self.user).delete()
        self.user.set_unusable_password()
        self.user.is_active = False
        self.user.save(update_fields=["password", "is_active"])

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_password_reset_by_username_reactivates_and_bootstraps(self):
        mail.outbox.clear()

        response = self.client.post(
            reverse("password_reset"),
            {"email": self.user.username},
            follow=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("password_reset_done"))

        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
        self.assertTrue(DesignerProfile.objects.filter(user=self.user).exists())
        self.assertTrue(UserSubscription.objects.filter(user=self.user).exists())

        # At least one email should have been queued and one must be the reset email
        self.assertGreaterEqual(len(mail.outbox), 1)
        self.assertTrue(
            any("reset" in (message.subject or "").lower() for message in mail.outbox),
            "Expected a password reset email to be sent",
        )
        self.assertTrue(
            any("sleepy@example.com" in (message.to or []) for message in mail.outbox),
            "Expected emails to include the designer's address",
        )

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_password_reset_falls_back_to_contact_email(self):
        mail.outbox.clear()
        fallback_email = "sleepy-contact@example.com"

        # Ensure the user record has no email but the profile exposes a contact address
        self.user.email = ""
        self.user.save(update_fields=["email"])
        DesignerProfile.objects.create(user=self.user, contact_email=fallback_email)

        response = self.client.post(
            reverse("password_reset"),
            {"email": self.user.username},
            follow=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("password_reset_done"))

        self.assertTrue(
            any(fallback_email in (message.to or []) for message in mail.outbox),
            "Expected the reset email to use the profile contact address when user.email is empty",
        )


@override_settings(
    SECURE_SSL_REDIRECT=False,
    SESSION_COOKIE_SECURE=False,
    CSRF_COOKIE_SECURE=False,
    STORAGES=TEST_STORAGE_BACKENDS,
)
class DesignerDirectoryFilterTests(TestCase):
    def setUp(self) -> None:
        self.us_user = User.objects.create_user(
            username="west-coast",
            email="west@example.com",
            password="unused",
            is_active=True,
        )
        self.fr_user = User.objects.create_user(
            username="parisian",
            email="paris@example.com",
            password="unused",
            is_active=True,
        )

        DesignerProfile.objects.create(
            user=self.us_user,
            region_area="West Coast",
            country="United States",
            state_province="California",
            county="Los Angeles County",
            city="Los Angeles",
            specialization="Streetwear",
            location="Los Angeles, CA, USA",
        )
        DesignerProfile.objects.create(
            user=self.fr_user,
            region_area="Europe",
            country="France",
            state_province="Île-de-France",
            city="Paris",
            specialization="Couture",
            location="Paris, France",
        )

    def test_filter_by_country_limits_results(self):
        response = self.client.get(reverse("designers_list"), {"country": "France"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Paris")
        self.assertNotContains(response, "Los Angeles")

    def test_filter_by_city_within_country(self):
        response = self.client.get(
            reverse("designers_list"),
            {
                "country": "United States",
                "city": "Los Angeles",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Los Angeles")
        self.assertNotContains(response, "Paris")


@override_settings(
    SECURE_SSL_REDIRECT=False,
    SESSION_COOKIE_SECURE=False,
    CSRF_COOKIE_SECURE=False,
    STORAGES=TEST_STORAGE_BACKENDS,
    CANONICAL_HOST="globaldesignerhub.com",
    CANONICAL_REDIRECT_HOSTS=["www.globaldesignerhub.com"],
    CANONICAL_DOMAIN_REDIRECT_ENABLED=True,
    CANONICAL_REDIRECT_SCHEME="https",
    ALLOWED_HOSTS=["testserver", "globaldesignerhub.com", "www.globaldesignerhub.com"],
)
class CanonicalDomainRedirectTests(TestCase):
    def test_www_redirects_to_canonical(self):
        response = self.client.get("/", HTTP_HOST="www.globaldesignerhub.com")
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response.headers.get("Location"), "https://globaldesignerhub.com/")

    def test_canonical_host_serves_homepage(self):
        response = self.client.get("/", HTTP_HOST="globaldesignerhub.com")
        self.assertEqual(response.status_code, 200)


@override_settings(
    SECURE_SSL_REDIRECT=False,
    SESSION_COOKIE_SECURE=False,
    CSRF_COOKIE_SECURE=False,
    STORAGES=TEST_STORAGE_BACKENDS,
)
class ReportProblemViewTests(TransactionTestCase):
    def test_get_report_page_renders(self):
        response = self.client.get(reverse("report_problem"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Report a problem")

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", ADMIN_EMAIL="ops@example.com")
    def test_anonymous_submission_creates_report_and_sends_email(self):
        mail.outbox.clear()
        payload = {
            "name": "Guest",
            "email": "guest@example.com",
            "category": ProblemReport.CATEGORY_TECHNICAL,
            "subject": "Uploader broken",
            "message": "When I try to upload a new design I get a 500 error every time.",
            "page_url": "https://globaldesignerhub.com/dashboard/",
        }
        response = self.client.post(reverse("report_problem"), payload)
        self.assertRedirects(response, reverse("report_problem_thanks"))

        report = ProblemReport.objects.get()
        self.assertEqual(report.category, ProblemReport.CATEGORY_TECHNICAL)
        self.assertEqual(report.email, payload["email"])
        self.assertIsNone(report.reporter)
        self.assertEqual(report.status, ProblemReport.STATUS_OPEN)

        self.assertGreaterEqual(len(mail.outbox), 1, "Expected admin notification email")
        self.assertEqual(mail.outbox[0].subject, "[GlobalDesignerHub] New problem report")
        self.assertIn(payload["subject"], mail.outbox[0].body)

    def test_authenticated_user_is_attached_to_report(self):
        user = User.objects.create_user(
            username="reporter",
            email="reporter@example.com",
            password="StrongPass123!",
        )
        self.client.login(username="reporter", password="StrongPass123!")

        payload = {
            "name": "Reporter",
            "email": "reporter@example.com",
            "category": ProblemReport.CATEGORY_BILLING,
            "subject": "Billing invoice issue",
            "message": "My invoice shows the wrong amount after upgrading the plan.",
            "page_url": "/billing/",
        }
        response = self.client.post(reverse("report_problem"), payload)
        self.assertRedirects(response, reverse("report_problem_thanks"))

        report = ProblemReport.objects.get()
        self.assertEqual(report.reporter, user)
        self.assertEqual(report.category, ProblemReport.CATEGORY_BILLING)


@override_settings(
    SECURE_SSL_REDIRECT=False,
    SESSION_COOKIE_SECURE=False,
    CSRF_COOKIE_SECURE=False,
    STORAGES=TEST_STORAGE_BACKENDS,
)
class ProjectCreationTests(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(
            username="project-maker",
            email="maker@example.com",
            password="StrongPass123!",
            is_active=True,
        )
        self.templates = load_project_templates()
        self.primary_template = self.templates[0]

    def test_create_project_from_template(self):
        self.client.login(username="project-maker", password="StrongPass123!")
        payload = {
            "template_id": self.primary_template["id"],
            "title": "Fuel Fortress Launch",
            "client_name": "Run Volume One",
            "season": "SS25",
            "product_type": "hoodie",
            "product_count": 2,
        }
        response = self.client.post(
            reverse("project_create_api"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        project = Project.objects.get()
        self.assertEqual(project.title, payload["title"])
        self.assertEqual(project.template_id, payload["template_id"])
        self.assertEqual(project.stages.count(), len(self.primary_template["stages"]))
        self.assertTrue(project.product_specs.exists())
        first_spec = project.product_specs.first()
        self.assertEqual(first_spec.fields.count(), len(self.primary_template["productSpec"]["fields"]))

    def test_invalid_template_returns_error(self):
        self.client.login(username="project-maker", password="StrongPass123!")
        payload = {
            "template_id": "missing-template",
            "title": "Invalid Project",
            "product_type": "hoodie",
            "product_count": 1,
        }
        response = self.client.post(
            reverse("project_create_api"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("errors", response.json())
        self.assertFalse(Project.objects.exists())


@override_settings(
    SECURE_SSL_REDIRECT=False,
    SESSION_COOKIE_SECURE=False,
    CSRF_COOKIE_SECURE=False,
    STORAGES=TEST_STORAGE_BACKENDS,
)
class TechpackBlueprintTests(TestCase):
    def test_desert_shadows_blueprint_renders(self):
        response = self.client.get(reverse("generate_techpack", args=["desert-shadows"]))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("DESERT SHADOWS", content)
        self.assertIn("ShadowFlex Jogger", content)

    def test_missing_blueprint_returns_404(self):
        response = self.client.get(reverse("generate_techpack", args=["missing-pack"]))
        self.assertEqual(response.status_code, 404)


@override_settings(
    SECURE_SSL_REDIRECT=False,
    SESSION_COOKIE_SECURE=False,
    CSRF_COOKIE_SECURE=False,
    STORAGES=TEST_STORAGE_BACKENDS,
)
class VolumeOneViewTests(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(
            username="volume",
            email="volume@example.com",
            password="StrongPass123!",
            is_active=True,
        )

    def test_volume_one_dashboard_renders_iframe_to_public_page(self):
        self.client.login(username="volume", password="StrongPass123!")
        response = self.client.get(reverse("volume_one"))
        self.assertEqual(response.status_code, 200)
        public_path = reverse("volume_one_public")
        expected_src = f'src="http://testserver{public_path}"'
        self.assertIn("iframe", response.content.decode())
        self.assertIn(expected_src, response.content.decode())

    @patch("designer_portfolio.views.get_volumeone_feed")
    def test_volume_one_public_page_uses_feed(self, mock_feed):
        feed = {
            "profile": {
                "handle": "runvolumeone",
                "name": "RUNWAY",
                "followers_display": "895",
                "posts_display": "22",
                "following_display": "6",
                "avatar_url": "https://example.com/avatar.jpg",
            },
            "slides": [
                {
                    "id": "abc",
                    "shortcode": "abc",
                    "caption": "See you soon Honolulu",
                    "caption_short": "See you soon Honolulu",
                    "image_url": "https://example.com/post.jpg",
                    "is_video": False,
                    "permalink": "https://instagram.com/p/abc/",
                    "taken_at": timezone.now(),
                    "tags": ["runvolumeone"],
                    "accessibility_caption": "",
                    "like_display": "12",
                    "comment_display": "3",
                }
            ],
            "source": "live",
            "fetched_at": timezone.now(),
        }
        mock_feed.return_value = feed

        response = self.client.get(reverse("volume_one_public"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "RunVolumeOne Collective")
        self.assertContains(response, feed["slides"][0]["caption"])
        self.assertContains(response, feed["slides"][0]["permalink"])
        mock_feed.assert_called_once()
