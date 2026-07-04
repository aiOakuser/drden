from django import forms

from .models import (
    BrandPartnershipLead,
    EmergingTalentSubmission,
    EventRegistration,
    FashionConsultLead,
    ForumInterestSignup,
    MentorshipApplication,
    NewsletterSubscription,
)


class FashionConsultLeadForm(forms.ModelForm):
    class Meta:
        model = FashionConsultLead
        fields = ["full_name", "country_code", "phone_number"]
        widgets = {
            "full_name": forms.TextInput(
                attrs={
                    "placeholder": "Enter your full name",
                    "class": "popup-input",
                }
            ),
            "country_code": forms.TextInput(
                attrs={
                    "value": "+1",
                    "class": "popup-country-code",
                }
            ),
            "phone_number": forms.TextInput(
                attrs={
                    "placeholder": "Phone number",
                    "class": "popup-phone-input",
                }
            ),
        }


_GROWTH_INPUT_ATTRS = {"class": "drden-input"}


class EventRegistrationForm(forms.ModelForm):
    class Meta:
        model = EventRegistration
        fields = ["full_name", "email", "notes"]
        widgets = {
            "full_name": forms.TextInput(
                attrs={**_GROWTH_INPUT_ATTRS, "placeholder": "Your full name"}
            ),
            "email": forms.EmailInput(
                attrs={
                    **_GROWTH_INPUT_ATTRS,
                    "placeholder": "you@example.com",
                    "autocomplete": "email",
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    **_GROWTH_INPUT_ATTRS,
                    "rows": 3,
                    "placeholder": "Anything you want the host to know? (optional)",
                }
            ),
        }

    def clean_email(self) -> str:
        return (self.cleaned_data["email"] or "").strip().lower()

    def save(self, *, event, commit: bool = True) -> EventRegistration:
        """
        Idempotent RSVP: if this email already has a registration for the
        event, refresh the in-place row instead of raising on the
        unique_together constraint.
        """
        email = self.cleaned_data["email"]
        full_name = (self.cleaned_data.get("full_name") or "").strip()
        notes = (self.cleaned_data.get("notes") or "").strip()

        existing = EventRegistration.objects.filter(event=event, email=email).first()
        if existing is not None:
            update_fields: list[str] = ["updated_at"]
            if full_name and existing.full_name != full_name:
                existing.full_name = full_name
                update_fields.append("full_name")
            if notes and existing.notes != notes:
                existing.notes = notes
                update_fields.append("notes")
            if existing.cancelled_at is not None:
                existing.cancelled_at = None
                update_fields.append("cancelled_at")
            existing.save(update_fields=update_fields)
            return existing

        registration = EventRegistration(
            event=event,
            email=email,
            full_name=full_name,
            notes=notes,
        )
        if commit:
            registration.save()
        return registration


class BrandPartnershipLeadForm(forms.ModelForm):
    class Meta:
        model = BrandPartnershipLead
        fields = [
            "brand_name",
            "contact_name",
            "email",
            "role",
            "website",
            "partnership_kind",
            "audience_reach",
            "message",
        ]
        widgets = {
            "brand_name": forms.TextInput(
                attrs={**_GROWTH_INPUT_ATTRS, "placeholder": "Brand name"}
            ),
            "contact_name": forms.TextInput(
                attrs={**_GROWTH_INPUT_ATTRS, "placeholder": "Your full name"}
            ),
            "email": forms.EmailInput(
                attrs={**_GROWTH_INPUT_ATTRS, "placeholder": "you@brand.com"}
            ),
            "role": forms.TextInput(
                attrs={
                    **_GROWTH_INPUT_ATTRS,
                    "placeholder": "Your role (e.g. Marketing Lead)",
                }
            ),
            "website": forms.URLInput(
                attrs={**_GROWTH_INPUT_ATTRS, "placeholder": "https://yourbrand.com"}
            ),
            "partnership_kind": forms.Select(attrs={**_GROWTH_INPUT_ATTRS}),
            "audience_reach": forms.TextInput(
                attrs={
                    **_GROWTH_INPUT_ATTRS,
                    "placeholder": "Audience you'd activate (e.g. '420K IG, 90K newsletter')",
                }
            ),
            "message": forms.Textarea(
                attrs={
                    **_GROWTH_INPUT_ATTRS,
                    "rows": 4,
                    "placeholder": "What would you like to run with the drden community?",
                }
            ),
        }


class MentorshipApplicationForm(forms.ModelForm):
    """
    One form, two roles. The view binds `role` (mentor or mentee) and
    swaps placeholder copy so applicants see role-specific prompts
    without giving them a way to pick a role that doesn't match the URL.
    """

    class Meta:
        model = MentorshipApplication
        fields = [
            "full_name",
            "email",
            "headline",
            "focus_areas",
            "portfolio_url",
            "availability",
            "message",
        ]

    def __init__(self, *args, role: str = MentorshipApplication.Role.MENTEE, **kwargs):
        super().__init__(*args, **kwargs)
        self.role = role
        is_mentor = role == MentorshipApplication.Role.MENTOR

        self.fields["full_name"].widget = forms.TextInput(
            attrs={**_GROWTH_INPUT_ATTRS, "placeholder": "Your full name"}
        )
        self.fields["email"].widget = forms.EmailInput(
            attrs={**_GROWTH_INPUT_ATTRS, "placeholder": "you@example.com"}
        )
        self.fields["headline"].widget = forms.TextInput(
            attrs={
                **_GROWTH_INPUT_ATTRS,
                "placeholder": (
                    "Title + company (e.g. Senior Designer · Acme Studio)"
                    if is_mentor
                    else "School + year (e.g. Parsons · BFA Senior)"
                ),
            }
        )
        self.fields["focus_areas"].widget = forms.TextInput(
            attrs={
                **_GROWTH_INPUT_ATTRS,
                "placeholder": "Comma-separated focus areas (tech packs, denim, womenswear…)",
            }
        )
        self.fields["portfolio_url"].widget = forms.URLInput(
            attrs={
                **_GROWTH_INPUT_ATTRS,
                "placeholder": (
                    "Public portfolio URL (LinkedIn, personal site, drden portfolio)"
                ),
            }
        )
        self.fields["availability"].widget = forms.TextInput(
            attrs={
                **_GROWTH_INPUT_ATTRS,
                "placeholder": "Hours / month + time-zone (e.g. '2 hrs/mo · PT')",
            }
        )
        self.fields["message"].widget = forms.Textarea(
            attrs={
                **_GROWTH_INPUT_ATTRS,
                "rows": 4,
                "placeholder": (
                    "Tell us why you want to mentor and the kind of mentee you'd love."
                    if is_mentor
                    else "What kind of guidance are you looking for? What do you want to learn?"
                ),
            }
        )

    def clean_email(self) -> str:
        return (self.cleaned_data["email"] or "").strip().lower()

    def save(self, commit: bool = True) -> MentorshipApplication:
        application = super().save(commit=False)
        application.role = self.role
        if commit:
            application.save()
        return application


class EmergingTalentSubmissionForm(forms.ModelForm):
    """
    Designer self-nomination for the Emerging Talent section.
    `consent_share` is required (so the form can't be submitted without
    explicit publish consent), and the success-story prompt nudges the
    designer toward the kind of copy our editors actually use.
    """

    consent_share = forms.BooleanField(
        required=True,
        label="I consent to Global Designer Hub publishing my work as part of the Emerging Talent feature.",
        help_text="We'll review and reach out before publishing anything.",
    )

    class Meta:
        model = EmergingTalentSubmission
        fields = [
            "full_name",
            "email",
            "portfolio_url",
            "school",
            "grad_year",
            "focus_areas",
            "story",
            "consent_share",
        ]
        widgets = {
            "full_name": forms.TextInput(
                attrs={**_GROWTH_INPUT_ATTRS, "placeholder": "Your full name"}
            ),
            "email": forms.EmailInput(
                attrs={
                    **_GROWTH_INPUT_ATTRS,
                    "placeholder": "you@example.com",
                    "autocomplete": "email",
                }
            ),
            "portfolio_url": forms.URLInput(
                attrs={
                    **_GROWTH_INPUT_ATTRS,
                    "placeholder": "https://yourportfolio.com",
                }
            ),
            "school": forms.TextInput(
                attrs={
                    **_GROWTH_INPUT_ATTRS,
                    "placeholder": "School + program (e.g. Parsons · BFA Fashion Design)",
                }
            ),
            "grad_year": forms.TextInput(
                attrs={
                    **_GROWTH_INPUT_ATTRS,
                    "placeholder": "e.g. 2026 final year",
                }
            ),
            "focus_areas": forms.TextInput(
                attrs={
                    **_GROWTH_INPUT_ATTRS,
                    "placeholder": "Comma-separated focus areas (tailoring, denim, womenswear…)",
                }
            ),
            "story": forms.Textarea(
                attrs={
                    **_GROWTH_INPUT_ATTRS,
                    "rows": 5,
                    "placeholder": (
                        "Tell us about your work, your aesthetic, and why you'd "
                        "be a fit for Emerging Talent."
                    ),
                }
            ),
        }

    def clean_email(self) -> str:
        return (self.cleaned_data["email"] or "").strip().lower()


class ForumInterestForm(forms.Form):
    """
    Plain `Form` (not `ModelForm`) so re-signing up with a known email
    takes the idempotent update path instead of failing the unique-email
    validator on `ForumInterestSignup.email`.
    """

    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={**_GROWTH_INPUT_ATTRS, "placeholder": "you@example.com"}
        )
    )
    full_name = forms.CharField(
        required=False,
        max_length=150,
        widget=forms.TextInput(
            attrs={**_GROWTH_INPUT_ATTRS, "placeholder": "Your name (optional)"}
        ),
    )
    notes = forms.CharField(
        required=False,
        max_length=240,
        widget=forms.Textarea(
            attrs={
                **_GROWTH_INPUT_ATTRS,
                "rows": 3,
                "placeholder": (
                    "What would you want forums to be — rooms, topics, "
                    "private studios? (optional)"
                ),
            }
        ),
    )

    def clean_email(self) -> str:
        return (self.cleaned_data["email"] or "").strip().lower()

    def save(self) -> ForumInterestSignup:
        email = self.cleaned_data["email"]
        full_name = (self.cleaned_data.get("full_name") or "").strip()
        notes = (self.cleaned_data.get("notes") or "").strip()

        existing = ForumInterestSignup.objects.filter(email__iexact=email).first()
        if existing is not None:
            update_fields: list[str] = []
            if full_name and existing.full_name != full_name:
                existing.full_name = full_name
                update_fields.append("full_name")
            if notes and existing.notes != notes:
                existing.notes = notes
                update_fields.append("notes")
            if update_fields:
                existing.save(update_fields=update_fields)
            return existing

        return ForumInterestSignup.objects.create(
            email=email, full_name=full_name, notes=notes
        )


class NewsletterSignupForm(forms.Form):
    """drden digest signup — idempotent on email like forum interest."""

    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                **_GROWTH_INPUT_ATTRS,
                "placeholder": "you@example.com",
                "autocomplete": "email",
            }
        )
    )
    full_name = forms.CharField(
        required=False,
        max_length=150,
        widget=forms.TextInput(
            attrs={**_GROWTH_INPUT_ATTRS, "placeholder": "Your name (optional)"}
        ),
    )
    interests = forms.CharField(
        required=False,
        max_length=240,
        widget=forms.TextInput(
            attrs={
                **_GROWTH_INPUT_ATTRS,
                "placeholder": "Topics you care about (events, emerging talent, tech packs…)",
            }
        ),
    )

    def __init__(self, *args, source: str = "", **kwargs):
        super().__init__(*args, **kwargs)
        self.source = (source or "").strip()[:64]

    def clean_email(self) -> str:
        return (self.cleaned_data["email"] or "").strip().lower()

    def save(self) -> NewsletterSubscription:
        email = self.cleaned_data["email"]
        full_name = (self.cleaned_data.get("full_name") or "").strip()
        interests = (self.cleaned_data.get("interests") or "").strip()

        existing = NewsletterSubscription.objects.filter(email__iexact=email).first()
        if existing is not None:
            update_fields: list[str] = ["updated_at"]
            if full_name and existing.full_name != full_name:
                existing.full_name = full_name
                update_fields.append("full_name")
            if interests and existing.interests != interests:
                existing.interests = interests
                update_fields.append("interests")
            if self.source and existing.source != self.source:
                existing.source = self.source
                update_fields.append("source")
            existing.save(update_fields=update_fields)
            return existing

        return NewsletterSubscription.objects.create(
            email=email,
            full_name=full_name,
            interests=interests,
            source=self.source,
        )
