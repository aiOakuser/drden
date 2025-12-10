from django.test import TestCase
from django.urls import reverse

from .forms import FashionConsultLeadForm
from .models import FashionConsultLead


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
