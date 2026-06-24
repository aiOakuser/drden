from datetime import timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .forms import (
    BrandPartnershipLeadForm,
    EmergingTalentSubmissionForm,
    EventRegistrationForm,
    FashionConsultLeadForm,
    ForumInterestForm,
    MentorshipApplicationForm,
)
from .models import (
    BrandPartnershipLead,
    EmergingTalentFeature,
    EmergingTalentSubmission,
    Event,
    EventRegistration,
    FashionConsultLead,
    ForumInterestSignup,
    MentorshipApplication,
    SocialContentBundle,
)
from .social_regenerator import (
    gather_ios_app_promo_context_text,
    gather_site_context_text,
)

User = get_user_model()


class FashionConsultLeadFormTests(TestCase):
    def test_form_requires_all_fields(self):
        form = FashionConsultLeadForm(data={})
        self.assertFalse(form.is_valid())
        self.assertSetEqual(set(form.errors.keys()), {"full_name", "country_code", "phone_number"})

    def test_form_saves_valid_payload(self):
        payload = {
            "full_name": "Studio QA",
            "country_code": "+44",
            "phone_number": "2071234567",
        }
        form = FashionConsultLeadForm(data=payload)
        self.assertTrue(form.is_valid(), form.errors)

        lead = form.save()
        self.assertEqual(lead.full_name, payload["full_name"])
        self.assertEqual(lead.country_code, payload["country_code"])
        self.assertEqual(lead.phone_number, payload["phone_number"])


class MarketingLeadViewTests(TestCase):
    def test_get_renders_hero_and_form(self):
        response = self.client.get(reverse("marketing:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Get up to 20% off")
        self.assertIn("form", response.context)
        self.assertIsInstance(response.context["form"], FashionConsultLeadForm)

    def test_invalid_submission_shows_errors(self):
        response = self.client.post(
            reverse("marketing:home"),
            {
                "full_name": "",
                "country_code": "",
                "phone_number": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This field is required.")
        self.assertEqual(FashionConsultLead.objects.count(), 0)

    def test_valid_submission_creates_lead_and_redirects(self):
        payload = {
            "full_name": "Capsule Client",
            "country_code": "+1",
            "phone_number": "5558675309",
        }
        response = self.client.post(reverse("marketing:home"), payload, follow=False)
        self.assertRedirects(response, reverse("marketing:popup_thank_you"))
        self.assertEqual(FashionConsultLead.objects.count(), 1)

        lead = FashionConsultLead.objects.get()
        self.assertEqual(lead.full_name, payload["full_name"])
        self.assertEqual(lead.country_code, payload["country_code"])
        self.assertEqual(lead.phone_number, payload["phone_number"])


class MarketingThankYouViewTests(TestCase):
    def test_static_page_loads(self):
        response = self.client.get(reverse("marketing:popup_thank_you"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Thank you!")


class SocialContentGatherTests(TestCase):
    def test_gather_site_context_returns_string(self):
        text = gather_site_context_text()
        self.assertIn("Global Designer Hub", text)
        self.assertIn("Facebook, Instagram, LinkedIn, X (Twitter), and YouTube", text)
        self.assertIn("build audience", text)

    def test_gather_ios_app_context_returns_string(self):
        text = gather_ios_app_promo_context_text()
        self.assertIn("iPhone", text)
        self.assertIn("Global Designer Hub", text)


class SocialContentDashboardViewTests(TestCase):
    def test_anonymous_redirects_to_login(self):
        url = reverse("marketing:social_content_dashboard")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_staff_can_load_dashboard(self):
        User.objects.create_user(username="staffer", password="x", is_staff=True)
        self.client.login(username="staffer", password="x")
        response = self.client.get(reverse("marketing:social_content_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Social content regeneration")
        self.assertContains(response, "Facebook / IG / LinkedIn / X / YouTube")

    def test_staff_dashboard_renders_expanded_hub_platforms(self):
        User.objects.create_user(username="staffer", password="x", is_staff=True)
        self.client.login(username="staffer", password="x")
        SocialContentBundle.objects.create(
            bundle_kind=SocialContentBundle.Kind.HUB_SOCIAL,
            platforms={
                "facebook_post": "Facebook audience prompt",
                "instagram_caption": "Instagram awareness caption",
                "instagram_hashtags": ["#GlobalDesignerHub"],
                "linkedin_post": "LinkedIn brand story",
                "x_post": "X direct engagement post",
                "youtube_post": "YouTube community post",
                "suggested_cta": "Explore the hub",
                "notes_for_designer": "Invite replies and questions.",
            },
        )

        response = self.client.get(reverse("marketing:social_content_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Facebook audience prompt")
        self.assertContains(response, "YouTube community post")

    def test_non_staff_forbidden(self):
        User.objects.create_user(username="regular", password="x", is_staff=False)
        self.client.login(username="regular", password="x")
        response = self.client.get(reverse("marketing:social_content_dashboard"))
        self.assertEqual(response.status_code, 403)


def _make_event(**overrides) -> Event:
    """Helper: build a default upcoming SCHEDULED event."""
    starts_at = overrides.pop("starts_at", timezone.now() + timedelta(days=7))
    defaults = {
        "title": "Default test event",
        "slug": "default-test-event",
        "kind": Event.Kind.WEBINAR,
        "summary": "A test event.",
        "starts_at": starts_at,
        "ends_at": starts_at + timedelta(hours=1),
        "is_virtual": True,
        "location": "Zoom",
        "host_name": "Test host",
        "status": Event.Status.SCHEDULED,
    }
    defaults.update(overrides)
    return Event.objects.create(**defaults)


class EventModelTests(TestCase):
    def test_is_public_only_for_scheduled_live_ended(self):
        for status in (Event.Status.SCHEDULED, Event.Status.LIVE, Event.Status.ENDED):
            event = _make_event(slug=f"e-{status}", status=status)
            self.assertTrue(event.is_public)
        for status in (Event.Status.DRAFT, Event.Status.CANCELLED):
            event = _make_event(slug=f"e-{status}", status=status)
            self.assertFalse(event.is_public)

    def test_is_full_respects_capacity(self):
        event = _make_event(slug="cap", capacity=2)
        self.assertFalse(event.is_full)
        EventRegistration.objects.create(event=event, email="a@example.com")
        self.assertFalse(event.is_full)
        EventRegistration.objects.create(event=event, email="b@example.com")
        self.assertTrue(event.is_full)
        self.assertFalse(event.registrations_open)

    def test_registrations_closed_for_non_scheduled_status(self):
        event = _make_event(slug="ended", status=Event.Status.ENDED)
        self.assertFalse(event.registrations_open)


class EventRegistrationFormTests(TestCase):
    def test_email_normalized_to_lowercase(self):
        event = _make_event(slug="lower")
        form = EventRegistrationForm(
            data={"full_name": "Test", "email": "  CASE@Example.COM ", "notes": ""}
        )
        self.assertTrue(form.is_valid(), form.errors)
        registration = form.save(event=event)
        self.assertEqual(registration.email, "case@example.com")

    def test_resubmit_with_same_email_updates_in_place(self):
        event = _make_event(slug="dup")
        form_a = EventRegistrationForm(
            data={"full_name": "Original", "email": "x@example.com", "notes": "a"}
        )
        self.assertTrue(form_a.is_valid())
        first = form_a.save(event=event)

        form_b = EventRegistrationForm(
            data={"full_name": "Updated", "email": "x@example.com", "notes": "b"}
        )
        self.assertTrue(form_b.is_valid())
        second = form_b.save(event=event)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(EventRegistration.objects.count(), 1)
        second.refresh_from_db()
        self.assertEqual(second.full_name, "Updated")
        self.assertEqual(second.notes, "b")


class EventViewTests(TestCase):
    def setUp(self):
        self.upcoming = _make_event(slug="upcoming-1", title="Upcoming One")
        self.past = _make_event(
            slug="past-1",
            title="Past One",
            starts_at=timezone.now() - timedelta(days=10),
            status=Event.Status.ENDED,
        )
        self.draft = _make_event(slug="draft-1", title="Draft One", status=Event.Status.DRAFT)

    def test_list_shows_upcoming_and_past_only(self):
        response = self.client.get(reverse("marketing:events_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Upcoming One")
        self.assertContains(response, "Past One")
        self.assertNotContains(response, "Draft One")

    def test_detail_404_for_draft(self):
        url = reverse("marketing:event_detail", args=[self.draft.slug])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_detail_renders_for_scheduled_event(self):
        url = reverse("marketing:event_detail", args=[self.upcoming.slug])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Upcoming One")
        self.assertContains(response, "Reserve my spot")

    def test_post_creates_registration_and_redirects(self):
        url = reverse("marketing:event_detail", args=[self.upcoming.slug])
        response = self.client.post(
            url,
            {"full_name": "Attendee", "email": "a@example.com", "notes": ""},
        )
        self.assertRedirects(
            response,
            reverse("marketing:event_registered", args=[self.upcoming.slug]),
        )
        self.assertTrue(
            EventRegistration.objects.filter(
                event=self.upcoming, email="a@example.com"
            ).exists()
        )

    def test_post_to_full_event_does_not_register(self):
        full_event = _make_event(slug="full", capacity=1)
        EventRegistration.objects.create(event=full_event, email="x@example.com")
        url = reverse("marketing:event_detail", args=[full_event.slug])
        response = self.client.post(
            url, {"full_name": "Late", "email": "late@example.com", "notes": ""}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "at capacity")
        self.assertEqual(
            EventRegistration.objects.filter(event=full_event).count(), 1
        )

    def test_post_to_ended_event_rejects(self):
        url = reverse("marketing:event_detail", args=[self.past.slug])
        response = self.client.post(
            url, {"full_name": "Ghost", "email": "g@example.com", "notes": ""}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(EventRegistration.objects.count(), 0)


class EmergingTalentViewTests(TestCase):
    def setUp(self):
        self.published = EmergingTalentFeature.objects.create(
            title="Capsule by Test",
            slug="capsule-by-test",
            display_name="Test Designer",
            bio_html="<p>Bio.</p>",
            success_story_html="<p>Success.</p>",
            is_published=True,
            published_at=timezone.now(),
        )
        self.draft = EmergingTalentFeature.objects.create(
            title="Draft Feature",
            slug="draft-feature",
            display_name="Hidden Designer",
            is_published=False,
        )

    def test_list_shows_published_only(self):
        response = self.client.get(reverse("marketing:emerging_talent_list"))
        self.assertContains(response, "Capsule by Test")
        self.assertNotContains(response, "Draft Feature")

    def test_detail_renders_for_published(self):
        url = reverse("marketing:emerging_talent_detail", args=[self.published.slug])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Designer")

    def test_detail_404_for_draft(self):
        url = reverse("marketing:emerging_talent_detail", args=[self.draft.slug])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_mark_published_stamps_timestamp(self):
        feature = EmergingTalentFeature.objects.create(
            title="Pending", slug="pending", display_name="P"
        )
        self.assertFalse(feature.is_published)
        feature.mark_published()
        feature.refresh_from_db()
        self.assertTrue(feature.is_published)
        self.assertIsNotNone(feature.published_at)


class BrandPartnershipViewTests(TestCase):
    def test_get_renders_form(self):
        response = self.client.get(reverse("marketing:brand_partner"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pitch a partnership")
        self.assertIsInstance(response.context["form"], BrandPartnershipLeadForm)

    def test_valid_post_creates_lead(self):
        response = self.client.post(
            reverse("marketing:brand_partner"),
            {
                "brand_name": "TestBrand",
                "contact_name": "Test Contact",
                "email": "biz@brand.com",
                "role": "Marketing Lead",
                "website": "https://brand.example.com",
                "partnership_kind": BrandPartnershipLead.PartnershipKind.COMPETITION,
                "audience_reach": "100K IG",
                "message": "Run a denim competition with us.",
            },
        )
        self.assertRedirects(response, reverse("marketing:brand_partner_thanks"))
        self.assertEqual(BrandPartnershipLead.objects.count(), 1)
        lead = BrandPartnershipLead.objects.get()
        self.assertEqual(lead.brand_name, "TestBrand")
        self.assertEqual(
            lead.partnership_kind, BrandPartnershipLead.PartnershipKind.COMPETITION
        )

    def test_invalid_post_creates_no_lead(self):
        response = self.client.post(reverse("marketing:brand_partner"), {})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(BrandPartnershipLead.objects.count(), 0)


class MentorshipFormAndViewTests(TestCase):
    def test_landing_renders_both_ctas(self):
        response = self.client.get(reverse("marketing:mentorship_landing"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Apply to mentor")
        self.assertContains(response, "Apply for a mentor")

    def test_apply_view_unknown_role_404s(self):
        response = self.client.get(
            reverse("marketing:mentorship_apply", args=["chaos-agent"])
        )
        self.assertEqual(response.status_code, 404)

    def test_form_save_locks_role_to_url(self):
        form = MentorshipApplicationForm(
            data={
                "full_name": "Mentor M.",
                "email": "  Mentor@Example.com ",
                "headline": "Senior · Acme",
                "focus_areas": "denim, tech packs",
                "portfolio_url": "https://example.com",
                "availability": "2 hrs/mo · PT",
                "message": "Happy to help.",
            },
            role=MentorshipApplication.Role.MENTOR,
        )
        self.assertTrue(form.is_valid(), form.errors)
        application = form.save()
        self.assertEqual(application.role, MentorshipApplication.Role.MENTOR)
        self.assertEqual(application.email, "mentor@example.com")
        self.assertEqual(application.status, MentorshipApplication.Status.PENDING)

    def test_post_creates_application_with_role_from_url(self):
        url = reverse("marketing:mentorship_apply", args=["become-a-mentor"])
        response = self.client.post(
            url,
            {
                "full_name": "Pro P.",
                "email": "pro@example.com",
                "headline": "Tech designer · Studio",
                "focus_areas": "womenswear",
                "portfolio_url": "https://example.com",
                "availability": "2 hrs/mo",
                "message": "Helpful intent.",
            },
        )
        self.assertRedirects(
            response,
            reverse("marketing:mentorship_applied", args=["become-a-mentor"]),
        )
        application = MentorshipApplication.objects.get()
        self.assertEqual(application.role, MentorshipApplication.Role.MENTOR)

    def test_post_for_mentee_path_sets_mentee_role(self):
        url = reverse("marketing:mentorship_apply", args=["find-a-mentor"])
        response = self.client.post(
            url,
            {
                "full_name": "Student S.",
                "email": "s@example.com",
                "headline": "Parsons BFA Senior",
                "focus_areas": "menswear",
                "portfolio_url": "",
                "availability": "evenings",
                "message": "Looking for guidance.",
            },
        )
        self.assertEqual(response.status_code, 302)
        application = MentorshipApplication.objects.get()
        self.assertEqual(application.role, MentorshipApplication.Role.MENTEE)

    def test_authenticated_user_is_attached_to_application(self):
        user = User.objects.create_user(
            username="alex", password="x", email="alex@example.com"
        )
        self.client.login(username="alex", password="x")
        url = reverse("marketing:mentorship_apply", args=["find-a-mentor"])
        self.client.post(
            url,
            {
                "full_name": "Alex",
                "email": "alex@example.com",
                "headline": "Self-taught",
                "focus_areas": "tech wear",
                "portfolio_url": "",
                "availability": "evenings",
                "message": "Interested.",
            },
        )
        application = MentorshipApplication.objects.get()
        self.assertEqual(application.user_id, user.id)

    def test_applied_thanks_unknown_role_404s(self):
        response = self.client.get(
            reverse("marketing:mentorship_applied", args=["chaos-agent"])
        )
        self.assertEqual(response.status_code, 404)


class CommunityForumViewTests(TestCase):
    def test_get_renders_form(self):
        response = self.client.get(reverse("marketing:community_forum"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Get early access")

    def test_post_creates_signup(self):
        response = self.client.post(
            reverse("marketing:community_forum"),
            {
                "email": "Forum@Example.com",
                "full_name": "Forum F.",
                "notes": "Want private studios.",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ForumInterestSignup.objects.count(), 1)
        signup = ForumInterestSignup.objects.get()
        self.assertEqual(signup.email, "forum@example.com")

    def test_resubmit_does_not_duplicate(self):
        ForumInterestSignup.objects.create(email="dup@example.com")
        self.client.post(
            reverse("marketing:community_forum"),
            {"email": "dup@example.com", "full_name": "Updated", "notes": ""},
        )
        self.assertEqual(ForumInterestSignup.objects.count(), 1)
        signup = ForumInterestSignup.objects.get()
        self.assertEqual(signup.full_name, "Updated")


class ForumInterestFormTests(TestCase):
    def test_email_required(self):
        form = ForumInterestForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_email_normalized_lowercase(self):
        form = ForumInterestForm(
            data={"email": "  Mixed@Case.COM ", "full_name": "", "notes": ""}
        )
        self.assertTrue(form.is_valid(), form.errors)
        signup = form.save()
        self.assertEqual(signup.email, "mixed@case.com")


class CommunityDashboardViewTests(TestCase):
    def test_anonymous_redirects_to_login(self):
        response = self.client.get(reverse("marketing:community_dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_non_staff_forbidden(self):
        User.objects.create_user(username="reg-com", password="x", is_staff=False)
        self.client.login(username="reg-com", password="x")
        response = self.client.get(reverse("marketing:community_dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_staff_dashboard_counts(self):
        _make_event(slug="dash-1", status=Event.Status.SCHEDULED)
        _make_event(slug="dash-2", status=Event.Status.DRAFT)
        _make_event(
            slug="dash-3",
            status=Event.Status.ENDED,
            starts_at=timezone.now() - timedelta(days=2),
        )
        MentorshipApplication.objects.create(
            role=MentorshipApplication.Role.MENTOR,
            full_name="Mentor",
            email="m@example.com",
            status=MentorshipApplication.Status.ACTIVE,
        )
        MentorshipApplication.objects.create(
            role=MentorshipApplication.Role.MENTEE,
            full_name="Mentee",
            email="me@example.com",
            status=MentorshipApplication.Status.PENDING,
        )
        MentorshipApplication.objects.create(
            role=MentorshipApplication.Role.MENTOR,
            full_name="Matched",
            email="matched@example.com",
            status=MentorshipApplication.Status.MATCHED,
        )
        User.objects.create_user(username="staff-com", password="x", is_staff=True)
        self.client.login(username="staff-com", password="x")
        response = self.client.get(reverse("marketing:community_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["event_counts"]["upcoming"], 1)
        self.assertEqual(response.context["event_counts"]["drafts"], 1)
        self.assertEqual(response.context["event_counts"]["past"], 1)
        self.assertEqual(response.context["mentorship_counts"]["mentors_active"], 1)
        self.assertEqual(response.context["mentorship_counts"]["mentees_active"], 1)
        self.assertEqual(response.context["mentorship_counts"]["matched"], 1)


class EmergingTalentSubmissionFormTests(TestCase):
    def _valid_payload(self, **overrides):
        data = {
            "full_name": "Grad Designer",
            "email": "GRAD@Example.COM",
            "portfolio_url": "https://example.com/grad",
            "school": "Parsons · BFA Fashion Design",
            "grad_year": "2026 final year",
            "focus_areas": "tailoring, womenswear",
            "story": "I work in tailored deadstock wools.",
            "consent_share": "on",
        }
        data.update(overrides)
        return data

    def test_form_requires_consent(self):
        form = EmergingTalentSubmissionForm(data=self._valid_payload(consent_share=""))
        self.assertFalse(form.is_valid())
        self.assertIn("consent_share", form.errors)

    def test_form_requires_core_fields(self):
        form = EmergingTalentSubmissionForm(data={})
        self.assertFalse(form.is_valid())
        for required in ("full_name", "email", "portfolio_url", "consent_share"):
            self.assertIn(required, form.errors)

    def test_email_normalized_lowercase(self):
        form = EmergingTalentSubmissionForm(data=self._valid_payload())
        self.assertTrue(form.is_valid(), form.errors)
        submission = form.save()
        self.assertEqual(submission.email, "grad@example.com")
        self.assertEqual(submission.status, EmergingTalentSubmission.Status.PENDING)


class EmergingTalentSubmissionViewTests(TestCase):
    def test_get_renders_form(self):
        response = self.client.get(reverse("marketing:emerging_talent_submit"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Get featured")
        self.assertIsInstance(
            response.context["form"], EmergingTalentSubmissionForm
        )

    def test_authenticated_user_prefills_and_attaches(self):
        user = User.objects.create_user(
            username="grad", password="x", email="grad-user@example.com"
        )
        self.client.login(username="grad", password="x")
        response = self.client.get(reverse("marketing:emerging_talent_submit"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["form"].initial.get("email"), "grad-user@example.com"
        )

        self.client.post(
            reverse("marketing:emerging_talent_submit"),
            {
                "full_name": "Grad User",
                "email": "grad-user@example.com",
                "portfolio_url": "https://example.com",
                "school": "Parsons",
                "grad_year": "2026",
                "focus_areas": "denim",
                "story": "Story.",
                "consent_share": "on",
            },
        )
        submission = EmergingTalentSubmission.objects.get()
        self.assertEqual(submission.user_id, user.id)

    def test_valid_post_persists_and_redirects(self):
        response = self.client.post(
            reverse("marketing:emerging_talent_submit"),
            {
                "full_name": "Anon Grad",
                "email": "anon@example.com",
                "portfolio_url": "https://example.com",
                "school": "Parsons",
                "grad_year": "2026",
                "focus_areas": "tailoring",
                "story": "About my work.",
                "consent_share": "on",
            },
        )
        self.assertRedirects(
            response, reverse("marketing:emerging_talent_submitted")
        )
        self.assertEqual(EmergingTalentSubmission.objects.count(), 1)
        submission = EmergingTalentSubmission.objects.get()
        self.assertEqual(submission.status, EmergingTalentSubmission.Status.PENDING)
        self.assertIsNone(submission.user)
        self.assertIsNone(submission.converted_feature)

    def test_post_without_consent_does_not_persist(self):
        response = self.client.post(
            reverse("marketing:emerging_talent_submit"),
            {
                "full_name": "No Consent",
                "email": "noconsent@example.com",
                "portfolio_url": "https://example.com",
                "consent_share": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(EmergingTalentSubmission.objects.count(), 0)

    def test_thanks_page_loads_and_links_back(self):
        response = self.client.get(reverse("marketing:emerging_talent_submitted"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("marketing:grads_landing"))


class EmergingTalentSubmissionConvertTests(TestCase):
    def _build(self, **overrides) -> EmergingTalentSubmission:
        defaults = dict(
            full_name="Convert Designer",
            email="convert@example.com",
            portfolio_url="https://example.com/portfolio",
            consent_share=True,
            story="Sample story.",
        )
        defaults.update(overrides)
        return EmergingTalentSubmission.objects.create(**defaults)

    def test_convert_creates_draft_feature_and_links_back(self):
        submission = self._build()
        feature = submission.convert_to_feature()
        self.assertIsInstance(feature, EmergingTalentFeature)
        self.assertFalse(feature.is_published)
        self.assertEqual(feature.display_name, "Convert Designer")
        self.assertEqual(feature.designer_portfolio_url, "https://example.com/portfolio")
        submission.refresh_from_db()
        self.assertEqual(submission.converted_feature_id, feature.id)
        self.assertEqual(submission.status, EmergingTalentSubmission.Status.APPROVED)

    def test_convert_is_idempotent(self):
        submission = self._build()
        feature = submission.convert_to_feature()
        again = submission.convert_to_feature()
        self.assertEqual(feature.id, again.id)
        self.assertEqual(EmergingTalentFeature.objects.count(), 1)

    def test_convert_preserves_user_link(self):
        user = User.objects.create_user(username="convertuser", password="x")
        submission = self._build(user=user)
        feature = submission.convert_to_feature()
        self.assertEqual(feature.designer_user_id, user.id)

    def test_convert_disambiguates_slug_collisions(self):
        EmergingTalentFeature.objects.create(
            title="Pre-existing", slug="convert-designer", display_name="Other"
        )
        submission = self._build()
        feature = submission.convert_to_feature()
        self.assertNotEqual(feature.slug, "convert-designer")
        self.assertTrue(feature.slug.startswith("convert-designer-"))


class GradsLandingViewTests(TestCase):
    def test_renders_three_section_structure(self):
        response = self.client.get(reverse("marketing:grads_landing"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Showcase your work")
        self.assertContains(response, "Stay ahead of the curve")
        self.assertContains(response, "Connect and collaborate")

    def test_renders_email_hero_copy(self):
        response = self.client.get(reverse("marketing:grads_landing"))
        self.assertContains(response, "Unleash your design potential")
        self.assertContains(response, "Launch your portfolio now")

    def test_links_to_relevant_funnels(self):
        response = self.client.get(reverse("marketing:grads_landing"))
        body = response.content.decode("utf-8")
        for url in (
            reverse("marketing:emerging_talent_submit"),
            reverse("marketing:emerging_talent_list"),
            reverse("marketing:events_list"),
            reverse("marketing:community_forum"),
            reverse("marketing:mentorship_apply", args=["find-a-mentor"]),
            "/accounts/signup/",
            "/newsletter/?source=student_hub",
        ):
            self.assertIn(url, body, f"Expected {url} on grads landing page")

    def test_surfaces_upcoming_events(self):
        future_event = _make_event(
            slug="future-grad-webinar",
            title="Portfolio teardown for grads",
            starts_at=timezone.now() + timedelta(days=10),
        )
        response = self.client.get(reverse("marketing:grads_landing"))
        self.assertContains(response, "Portfolio teardown for grads")
        self.assertContains(response, future_event.get_kind_display())

    def test_does_not_surface_draft_events(self):
        _make_event(
            slug="draft-grad-event",
            title="Hidden Draft Event",
            status=Event.Status.DRAFT,
            starts_at=timezone.now() + timedelta(days=10),
        )
        response = self.client.get(reverse("marketing:grads_landing"))
        self.assertNotContains(response, "Hidden Draft Event")

    def test_surfaces_published_emerging_talent(self):
        EmergingTalentFeature.objects.create(
            title="Public Feature",
            slug="public-feature",
            display_name="Public Designer",
            is_published=True,
            published_at=timezone.now(),
        )
        EmergingTalentFeature.objects.create(
            title="Hidden Draft",
            slug="hidden-draft",
            display_name="Draft Designer",
            is_published=False,
        )
        response = self.client.get(reverse("marketing:grads_landing"))
        self.assertContains(response, "Public Designer")
        self.assertNotContains(response, "Draft Designer")


class SeedCommunityStarterContentTests(TestCase):
    def test_command_creates_starter_content(self):
        out = StringIO()
        call_command("seed_community_starter_content", stdout=out)
        self.assertGreaterEqual(Event.objects.count(), 3)
        self.assertGreaterEqual(EmergingTalentFeature.objects.count(), 2)
        for event in Event.objects.all():
            self.assertEqual(event.status, Event.Status.SCHEDULED)
        for feature in EmergingTalentFeature.objects.all():
            self.assertTrue(feature.is_published)

    def test_command_is_idempotent(self):
        call_command("seed_community_starter_content")
        first_event_count = Event.objects.count()
        first_feature_count = EmergingTalentFeature.objects.count()
        call_command("seed_community_starter_content")
        self.assertEqual(Event.objects.count(), first_event_count)
        self.assertEqual(EmergingTalentFeature.objects.count(), first_feature_count)
