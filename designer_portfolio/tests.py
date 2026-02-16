import json
from unittest.mock import patch

from django.test import RequestFactory, TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from django.contrib.auth.models import User
from django.core import mail
from django.utils import timezone
from social_core.exceptions import AuthForbidden

from .models import (
    DesignerProfile,
    UserSubscription,
    ProblemReport,
    Project,
    Template,
    TemplateStage,
    TemplateProductBlock,
    StudentPortfolio,
    StudentPortfolioProject,
    StudentProjectFeedback,
    StudentProjectLike,
    StudentProjectBookmark,
)
from .social_pipeline import generate_username, ensure_verified_email, sync_user_details
from .project_templates import load_project_templates, refresh_project_template_cache
from .views import _resolve_post_login_redirect
from .tekpak_blueprints import TEKPAK_BLUEPRINTS


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

    def test_login_with_profile_contact_email_redirects_to_dashboard(self):
        # Simulate a legacy/imported designer account where the email was stored
        # on the DesignerProfile rather than the User record.
        self.user.email = ""
        self.user.save(update_fields=["email"])
        DesignerProfile.objects.create(user=self.user, contact_email="legacy-contact@example.com")

        response = self.client.post(
            reverse("login"),
            {"username": "legacy-contact@example.com", "password": self.password},
            follow=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers.get("Location"), reverse("designer_dashboard"))

    def test_login_reactivates_designer_account_when_password_valid(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        DesignerProfile.objects.create(user=self.user, contact_email="reactivate@example.com")

        response = self.client.post(
            reverse("login"),
            {"username": "reactivate@example.com", "password": self.password},
            follow=False,
        )
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)

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


class PostLoginRedirectTests(TestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()

    def test_resolves_dashboard_path_when_next_missing(self):
        request = self.factory.get("/accounts/login/", HTTP_HOST="testserver")
        redirect_to = _resolve_post_login_redirect(request, "")
        self.assertEqual(redirect_to, reverse("designer_dashboard"))

    def test_accepts_relative_next_urls(self):
        request = self.factory.get("/accounts/login/", HTTP_HOST="testserver")
        candidate = "/dashboard/designs/"
        redirect_to = _resolve_post_login_redirect(request, candidate)
        self.assertEqual(redirect_to, candidate)

    def test_rejects_external_urls(self):
        request = self.factory.get("/accounts/login/", HTTP_HOST="testserver")
        redirect_to = _resolve_post_login_redirect(request, "https://malicious.example.com")
        self.assertEqual(redirect_to, reverse("designer_dashboard"))


@override_settings(
    # Deterministic canonical redirect settings for test hostnames
    CANONICAL_DOMAIN_REDIRECT_ENABLED=True,
    CANONICAL_HOST="globaldesignerhub.com",
    CANONICAL_REDIRECT_HOSTS=["www.globaldesignerhub.com"],
    CANONICAL_REDIRECT_SCHEME="https",
    SECURE_SSL_REDIRECT=False,
    SESSION_COOKIE_SECURE=False,
    CSRF_COOKIE_SECURE=False,
    STORAGES=TEST_STORAGE_BACKENDS,
)
class CanonicalDomainRedirectMiddlewareTests(TestCase):
    def test_get_request_redirects_with_301(self):
        response = self.client.get(
            reverse("login"),
            HTTP_HOST="www.globaldesignerhub.com",
            follow=False,
        )
        self.assertEqual(response.status_code, 301)
        self.assertEqual(
            response.headers.get("Location"),
            "https://globaldesignerhub.com" + reverse("login"),
        )

    def test_post_request_redirects_with_308_preserving_method(self):
        response = self.client.post(
            reverse("login"),
            {"username": "someone", "password": "secret"},
            HTTP_HOST="www.globaldesignerhub.com",
            follow=False,
        )
        self.assertEqual(response.status_code, 308)
        self.assertEqual(
            response.headers.get("Location"),
            "https://globaldesignerhub.com" + reverse("login"),
        )


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

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_password_reset_can_lookup_by_contact_email(self):
        mail.outbox.clear()
        fallback_email = "sleepy-contact-lookup@example.com"

        # Ensure the user record has no email but the profile exposes a contact address
        self.user.email = ""
        self.user.save(update_fields=["email"])
        DesignerProfile.objects.create(user=self.user, contact_email=fallback_email)

        response = self.client.post(
            reverse("password_reset"),
            {"email": fallback_email},
            follow=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("password_reset_done"))
        self.assertTrue(
            any(fallback_email in (message.to or []) for message in mail.outbox),
            "Expected a reset email to be sent when identifying by profile contact email",
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
    ADMIN_EMAIL="studio@example.com",
    DEFAULT_FROM_EMAIL="studio@example.com",
)
class ContactViewTests(TestCase):
    def test_get_contact_page_renders(self):
        response = self.client.get(reverse("contact"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Contact")

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_valid_submission_sends_email(self):
        mail.outbox.clear()
        payload = {
            "name": "Volume One",
            "email": "volume@example.com",
            "subject": "Workspace request",
            "message": "We would like to schedule a walkthrough of the dashboard.",
        }
        response = self.client.post(reverse("contact"), payload, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Thanks for reaching out.")
        self.assertGreaterEqual(len(mail.outbox), 1, "Expected a contact email to be generated")
        self.assertEqual(mail.outbox[0].to, ["studio@example.com"])
        self.assertIn(payload["message"], mail.outbox[0].body)

    def test_invalid_submission_shows_errors(self):
        response = self.client.post(
            reverse("contact"),
            {
                "name": "",
                "email": "invalid-email",
                "subject": "",
                "message": "short",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Share at least 10 characters")
        self.assertContains(response, "Enter a valid email address.")


@override_settings(
    SECURE_SSL_REDIRECT=False,
    SESSION_COOKIE_SECURE=False,
    CSRF_COOKIE_SECURE=False,
    STORAGES=TEST_STORAGE_BACKENDS,
)
class StudentPageViewTests(TestCase):
    def test_student_page_renders(self):
        response = self.client.get(reverse("student_page"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Build your design career before graduation")

    def test_student_page_supports_url_without_trailing_slash(self):
        response = self.client.get("/student")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "GlobalDesignerHub Student")


@override_settings(
    SECURE_SSL_REDIRECT=False,
    SESSION_COOKIE_SECURE=False,
    CSRF_COOKIE_SECURE=False,
    STORAGES=TEST_STORAGE_BACKENDS,
)
class TemplateLoaderTests(TestCase):
    def setUp(self) -> None:
        Template.objects.all().delete()
        TemplateStage.objects.all().delete()
        TemplateProductBlock.objects.all().delete()

    def test_load_project_templates_prefers_database(self):
        template = Template.objects.create(
            id="db_template",
            name="Database Template",
            layout_key="db-layout",
            cover_title_placeholder="DB TITLE",
            cover_subtitle_placeholder="DB SUBTITLE",
            summary=["Line 1"],
            metadata={"cover": {"titlePlaceholder": "DB TITLE", "subtitle": "DB SUBTITLE"}},
        )
        TemplateStage.objects.create(
            template=template,
            stage_index=1,
            title="Stage One",
            default_items=["Item A", "Item B"],
        )
        TemplateProductBlock.objects.create(
            template=template,
            block_index=1,
            label="RUN",
            title_placeholder="DB PRODUCT",
            code_placeholder="CODE-1",
            default_views=["FRONT"],
            details_schema={"fields": [{"key": "styleNumber", "label": "Style #"}]},
        )
        refresh_project_template_cache()

        templates = load_project_templates()
        self.assertEqual(len(templates), 1)
        payload = templates[0]
        self.assertEqual(payload["id"], template.id)
        self.assertEqual(payload["stages"][0]["defaultBullets"], ["Item A", "Item B"])
        self.assertTrue(payload["productBlocks"])
        block = payload["productBlocks"][0]
        self.assertEqual(block["detailsTemplate"]["fields"][0]["key"], "styleNumber")


@override_settings(
    SECURE_SSL_REDIRECT=False,
    SESSION_COOKIE_SECURE=False,
    CSRF_COOKIE_SECURE=False,
    STORAGES=TEST_STORAGE_BACKENDS,
)
class ProjectCreationTests(TestCase):
    def setUp(self) -> None:
        Template.objects.all().delete()
        TemplateStage.objects.all().delete()
        TemplateProductBlock.objects.all().delete()
        self.user = User.objects.create_user(
            username="project-maker",
            email="maker@example.com",
            password="StrongPass123!",
            is_active=True,
        )
        self.template = Template.objects.create(
            id="fuel_fortress",
            name="Fuel Fortress Project Breakdown",
            layout_key="fuel_fortress",
            cover_title_placeholder="FUEL FORTRESS",
            cover_subtitle_placeholder="RUN VOLUME ONE",
            summary=["Stage coverage", "Product block coverage"],
            metadata={
                "category": "Run Volume One",
                "thumbnail": {"background": "#000000"},
                "cover": {
                    "titlePlaceholder": "FUEL FORTRESS",
                    "subtitle": "RUN VOLUME ONE",
                },
            },
        )
        self.stage_items = [
            "Technical flats/line sheet",
            "Fabric & trim sourcing",
        ]
        TemplateStage.objects.create(
            template=self.template,
            stage_index=1,
            title="STAGE 01 / DESIGN & TECH DEV.",
            default_items=self.stage_items,
            layout_hint="two-column",
        )
        TemplateStage.objects.create(
            template=self.template,
            stage_index=2,
            title="STAGE 02 / PRE-PRODUCTION",
            default_items=["Lab dips", "Fit sample development"],
        )
        self.product_block = TemplateProductBlock.objects.create(
            template=self.template,
            block_index=1,
            label="RUNVOLUMEONE",
            title_placeholder="AERO HOODIE",
            code_placeholder="[CODE: HAR#-2621]",
            default_views=["FRONT", "BACK", "SIDE"],
            details_schema={
                "layoutHint": "single_column_specs",
                "fields": [
                    {"key": "styleNumber", "label": "Style #"},
                    {"key": "description", "label": "Description"},
                ],
            },
        )
        refresh_project_template_cache()
        self.templates = load_project_templates()
        self.primary_template = self.templates[0]

    def test_create_project_from_template(self):
        self.client.login(username="project-maker", password="StrongPass123!")
        payload = {
            "templateId": self.primary_template["id"],
            "title": "Fuel Fortress Launch",
            "subtitle": "MERCH DEVELOPMENT LINE PRESENTED BY RUN VOLUME ONE",
            "clientName": "Run Volume One",
            "season": "SS25",
            "productType": "hoodie",
            "productCount": 2,
        }
        response = self.client.post(
            reverse("project_create_api"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["subtitle"], payload["subtitle"])
        self.assertIn("createdAt", body)
        self.assertIn("redirectUrl", body)

        project = Project.objects.get()
        self.assertEqual(project.title, payload["title"])
        self.assertEqual(project.subtitle, payload["subtitle"])
        self.assertEqual(project.template_id, payload["templateId"])
        self.assertEqual(project.stages.count(), len(self.template.stages.all()))

        stage = project.stages.order_by("stage_number").first()
        self.assertIsNotNone(stage.template_stage)
        self.assertListEqual(stage.items, self.stage_items)

        first_spec = project.product_specs.first()
        self.assertIsNotNone(first_spec)
        self.assertEqual(first_spec.template_block, self.product_block)
        self.assertEqual(first_spec.fields.count(), len(self.product_block.details_schema["fields"]))

    def test_invalid_template_returns_error(self):
        self.client.login(username="project-maker", password="StrongPass123!")
        payload = {
            "templateId": "missing-template",
            "title": "Invalid Project",
            "productType": "hoodie",
            "productCount": 1,
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
    def test_all_blueprints_render(self):
        for slug in TEKPAK_BLUEPRINTS:
            response = self.client.get(reverse("generate_techpack", args=[slug]))
            self.assertEqual(response.status_code, 200, slug)
            content = response.content.decode()
            hero_title = TEKPAK_BLUEPRINTS[slug].get("hero", {}).get("title")
            breakdown_label = TEKPAK_BLUEPRINTS[slug].get("project_breakdown", {}).get("label")
            if hero_title:
                self.assertIn(hero_title, content)
            if breakdown_label:
                self.assertIn(breakdown_label, content)

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
        self.assertContains(response, "Open design pack")
        self.assertIn("design_packs", response.context)
        self.assertTrue(response.context["design_packs"])
        first_pack_title = TEKPAK_BLUEPRINTS["desert-shadows"]["hero"]["title"]
        self.assertContains(response, first_pack_title)
        self.assertContains(response, "Postgres schema powering VolumeOne")
        self.assertContains(response, "Street Circuit Project Breakdown")
        mock_feed.assert_called_once()


@override_settings(
    SECURE_SSL_REDIRECT=False,
    SESSION_COOKIE_SECURE=False,
    CSRF_COOKIE_SECURE=False,
    STORAGES=TEST_STORAGE_BACKENDS,
)
class StudentPortfolioFeatureTests(TestCase):
    def setUp(self) -> None:
        self.student = User.objects.create_user(
            username="student-designer",
            email="student@example.com",
            password="StrongPass123!",
            is_active=True,
        )
        self.reviewer = User.objects.create_user(
            username="studio-reviewer",
            email="reviewer@example.com",
            password="StrongPass123!",
            is_active=True,
        )

    def test_dashboard_creates_and_updates_student_portfolio(self):
        self.client.login(username="student-designer", password="StrongPass123!")

        response = self.client.get(reverse("student_portfolio_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(StudentPortfolio.objects.filter(user=self.student).exists())

        response = self.client.post(
            reverse("student_portfolio_dashboard"),
            {
                "action": "update_portfolio",
                "bio": "Focused on product and interface systems.",
                "skills": "Figma, Illustrator",
                "design_interests": "UI/UX, Product Design",
                "template_style": StudentPortfolio.TemplateStyle.MINIMAL,
                "visibility": StudentPortfolio.Visibility.PUBLIC,
            },
            follow=False,
        )
        self.assertEqual(response.status_code, 302)
        portfolio = StudentPortfolio.objects.get(user=self.student)
        self.assertEqual(portfolio.visibility, StudentPortfolio.Visibility.PUBLIC)
        self.assertEqual(portfolio.template_style, StudentPortfolio.TemplateStyle.MINIMAL)
        self.assertEqual(portfolio.skills, "Figma, Illustrator")

    def test_create_project_and_reorder_projects(self):
        self.client.login(username="student-designer", password="StrongPass123!")
        self.client.get(reverse("student_portfolio_dashboard"))

        first_payload = {
            "action": "create_project",
            "title": "Campus Mobile App",
            "description": "Improved navigation and onboarding for first-year students.",
            "category": StudentPortfolioProject.Category.UI_UX,
            "tools_used": "Figma, Maze",
            "project_role": "UX Designer",
            "process_steps": "Sketches\nWireframes\nInteractive prototype",
        }
        second_payload = {
            "action": "create_project",
            "title": "Event Poster Series",
            "description": "Visual identity and poster system for design week.",
            "category": StudentPortfolioProject.Category.GRAPHIC_DESIGN,
            "tools_used": "Illustrator, Photoshop",
            "project_role": "Graphic Designer",
            "process_steps": "Moodboard\nConcepts\nFinal poster set",
        }
        self.client.post(reverse("student_portfolio_dashboard"), first_payload, follow=False)
        self.client.post(reverse("student_portfolio_dashboard"), second_payload, follow=False)

        projects = list(
            StudentPortfolioProject.objects.filter(portfolio__user=self.student).order_by("display_order")
        )
        self.assertEqual(len(projects), 2)
        self.assertEqual(projects[0].title, "Campus Mobile App")
        self.assertEqual(projects[1].title, "Event Poster Series")

        response = self.client.post(
            reverse("student_portfolio_reorder_projects"),
            data=json.dumps({"project_ids": [projects[1].id, projects[0].id]}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

        reordered = list(
            StudentPortfolioProject.objects.filter(portfolio__user=self.student).order_by("display_order")
        )
        self.assertEqual(reordered[0].title, "Event Poster Series")
        self.assertEqual(reordered[1].title, "Campus Mobile App")

    def test_public_share_link_honors_visibility(self):
        portfolio = StudentPortfolio.objects.create(user=self.student)
        StudentPortfolioProject.objects.create(
            portfolio=portfolio,
            title="Responsive Design System",
            description="Tokens and components for internal tools.",
            category=StudentPortfolioProject.Category.UI_UX,
            display_order=0,
        )

        share_url = reverse("student_portfolio_public", args=[portfolio.share_slug])
        response = self.client.get(share_url, follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response["Location"])

        portfolio.visibility = StudentPortfolio.Visibility.PUBLIC
        portfolio.save(update_fields=["visibility"])

        response = self.client.get(share_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Responsive Design System")

    def test_feedback_like_and_bookmark_flow(self):
        portfolio = StudentPortfolio.objects.create(
            user=self.student,
            visibility=StudentPortfolio.Visibility.PUBLIC,
        )
        project = StudentPortfolioProject.objects.create(
            portfolio=portfolio,
            title="Brand Toolkit",
            description="Complete visual toolkit for student startup.",
            category=StudentPortfolioProject.Category.BRANDING,
            display_order=0,
        )

        self.client.login(username="studio-reviewer", password="StrongPass123!")
        share_path = reverse("student_portfolio_public", args=[portfolio.share_slug])

        feedback_response = self.client.post(
            reverse("student_portfolio_project_feedback", args=[project.id]),
            {
                "reviewer_role": StudentProjectFeedback.ReviewerRole.TEACHER,
                "comment": "Great visual hierarchy. Consider refining spacing on the icon grid.",
                "next": share_path,
            },
            follow=False,
        )
        self.assertEqual(feedback_response.status_code, 302)
        self.assertEqual(StudentProjectFeedback.objects.count(), 1)

        like_response = self.client.post(
            reverse("student_portfolio_project_like_toggle", args=[project.id]),
            {"next": share_path},
            follow=False,
        )
        self.assertEqual(like_response.status_code, 302)
        self.assertEqual(StudentProjectLike.objects.count(), 1)

        bookmark_response = self.client.post(
            reverse("student_portfolio_project_bookmark_toggle", args=[project.id]),
            {"next": share_path},
            follow=False,
        )
        self.assertEqual(bookmark_response.status_code, 302)
        self.assertEqual(StudentProjectBookmark.objects.count(), 1)

    def test_resume_pdf_download(self):
        StudentPortfolio.objects.create(
            user=self.student,
            bio="Student designer focused on accessibility and product systems.",
            skills="Figma, UX Writing",
            design_interests="UI/UX, Product Design",
            visibility=StudentPortfolio.Visibility.PUBLIC,
        )
        StudentPortfolioProject.objects.create(
            portfolio=self.student.student_portfolio,
            title="Onboarding Redesign",
            description="Reduced drop-off rates with simpler onboarding steps.",
            category=StudentPortfolioProject.Category.UI_UX,
            display_order=0,
        )

        self.client.login(username="student-designer", password="StrongPass123!")
        response = self.client.get(reverse("student_portfolio_resume_pdf"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertTrue(response.content.startswith(b"%PDF"))
