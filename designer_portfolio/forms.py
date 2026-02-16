from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordResetForm
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
from .models import (
    SubscriptionPlan,
    UserSubscription,
    ProblemReport,
    Project,
    Template,
    EventAttendee,
    EventCollaboration,
    StudentPortfolio,
    StudentPortfolioProject,
    StudentProjectFeedback,
)
from .project_templates import serialize_template_instance
from .auth_utils import ensure_designer_access
from .emails import notify_password_reset_request

class DesignerSignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)

    # Optional portfolio website URL
    website_url = forms.URLField(
        required=False,
        label="Portfolio website",
        help_text="Share a website or portfolio link for our private review (optional)",
    )

    # Subscription plan selection (by plan "name" string to match template radios)
    subscription_plan = forms.ChoiceField(
        choices=[("", "Free Trial (until you're ready)")] + SubscriptionPlan.PLAN_TYPES,
        required=False,
        widget=forms.RadioSelect,
        help_text="Feel free to upload designs and pick a subscription plan whenever you're satisfied."
    )

    # Payment method selection
    payment_method = forms.ChoiceField(
        choices=[("", "Choose payment method when you upgrade")] + UserSubscription.PAYMENT_METHODS,
        required=False,
        widget=forms.RadioSelect,
        help_text="Set up payment details only when you decide to upgrade from the free trial."
    )

    # Terms and conditions
    agree_to_terms = forms.BooleanField(
        required=True,
        label="I agree to the Terms of Service and Privacy Policy"
    )

    # Newsletter subscription
    subscribe_newsletter = forms.BooleanField(
        required=False,
        initial=True,
        label="Subscribe to our newsletter for updates and special offers"
    )

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "website_url",
            "password1",
            "password2",
            "subscription_plan",
            "payment_method",
            "agree_to_terms",
            "subscribe_newsletter",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add CSS classes and styling
        self.fields["username"].widget.attrs.update({
            "class": "form-control",
            "placeholder": "Enter username",
        })
        self.fields["email"].widget.attrs.update({
            "class": "form-control",
            "placeholder": "Enter email address",
        })
        self.fields["website_url"].widget.attrs.update({
            "class": "form-control",
            "placeholder": "https://your-portfolio.example (private, optional)",
            "autocomplete": "url",
        })
        self.fields["password1"].widget.attrs.update({
            "class": "form-control",
            "placeholder": "Enter password",
        })
        self.fields["password2"].widget.attrs.update({
            "class": "form-control",
            "placeholder": "Confirm password",
        })

    def clean(self):
        cleaned_data = super().clean()
        plan_name = cleaned_data.get("subscription_plan") or ""
        payment_method = cleaned_data.get("payment_method") or ""

        # If a paid plan is selected, payment method should be chosen
        if plan_name and payment_method == "":
            self.add_error(
                "payment_method",
                "Please select a payment method for your chosen subscription plan.",
            )

        return cleaned_data

    def save(self, commit: bool = True) -> User:
        user = super().save(commit=False)
        user.email = self.cleaned_data.get("email", "")
        # Activate designer accounts immediately
        user.is_active = True
        if commit:
            user.save()

        # Ensure dependent records exist for immediate dashboard access
        ensure_designer_access(user)
        profile = user.designer_profile

        # Persist optional website URL to profile
        website_url: str = self.cleaned_data.get("website_url") or ""
        if website_url:
            profile.portfolio_website = website_url
            profile.save()

        # Create a default trial subscription
        plan_name = self.cleaned_data.get("subscription_plan") or ""
        payment_method = self.cleaned_data.get("payment_method") or None

        trial_days = 30
        trial_end = timezone.now() + timedelta(days=trial_days)

        plan_instance = None
        if plan_name:
            plan_instance = SubscriptionPlan.objects.filter(name=plan_name, is_active=True).first()

        subscription = user.subscription
        update_fields = set()

        if plan_instance and subscription.plan != plan_instance:
            subscription.plan = plan_instance
            update_fields.add("plan")

        desired_payment_method = payment_method if payment_method else None
        if subscription.payment_method != desired_payment_method:
            subscription.payment_method = desired_payment_method
            update_fields.add("payment_method")

        for field_name in ["trial_end_date", "next_billing_date"]:
            current_value = getattr(subscription, field_name)
            if current_value != trial_end:
                setattr(subscription, field_name, trial_end)
                update_fields.add(field_name)

        if subscription.trial_start_date is None:
            subscription.trial_start_date = timezone.now()
            update_fields.add("trial_start_date")

        if subscription.status != "free_trial":
            subscription.status = "free_trial"
            update_fields.add("status")

        if update_fields:
            subscription.save(update_fields=list(update_fields))

        return user


class DesignerLoginForm(AuthenticationForm):
    """Custom login form that adds a Remember Me option.

    The view will read the remember_me field to control session expiry.
    """

    remember_me = forms.BooleanField(
        required=False,
        initial=True,
        label="Keep me signed in",
        help_text="Stay signed in on this device",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Improve field widgets and placeholders
        self.fields["username"].widget.attrs.update(
            {
                "class": "form-control",
                "placeholder": "Username or Email",
                "autocomplete": "username",
            }
        )
        self.fields["password"].widget.attrs.update(
            {
                "class": "form-control",
                "placeholder": "Password",
                "autocomplete": "current-password",
            }
        )
        # Lightweight styling hint for remember me checkbox
        self.fields["remember_me"].widget.attrs.update({"class": "form-check-input"})


class DesignerPasswordResetForm(PasswordResetForm):
    email = forms.CharField(
        label="Email or Username",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Email address or username",
                "autocomplete": "email",
            }
        ),
    )

    def clean_email(self):
        identifier = (self.cleaned_data.get("email") or "").strip()
        if not identifier:
            raise forms.ValidationError("Enter your email address or username.")
        return identifier

    def get_users(self, identifier):
        identifier = (identifier or "").strip()
        if not identifier:
            return []

        UserModel = get_user_model()
        # Support legacy/imported designers where the only reachable email lives
        # on the related DesignerProfile.contact_email field.
        candidates = (
            UserModel._default_manager.filter(
                Q(email__iexact=identifier)
                | Q(username__iexact=identifier)
                | Q(designer_profile__contact_email__iexact=identifier)
            )
            .distinct()
            .order_by("id")
        )

        # Avoid sending multiple emails when username/email map to the same
        # underlying account. Track via primary key.
        seen_user_ids = set()
        users = []
        for user in candidates:
            if user.pk in seen_user_ids:
                continue

            seen_user_ids.add(user.pk)

            if not user.is_active:
                user.is_active = True
                user.save(update_fields=["is_active"])

            ensure_designer_access(user)
            users.append(user)

        return users

    def save(
        self,
        domain_override=None,
        subject_template_name="registration/password_reset_subject.txt",
        email_template_name="registration/password_reset_email.html",
        use_https=False,
        token_generator=default_token_generator,
        from_email=None,
        request=None,
        html_email_template_name=None,
        extra_email_context=None,
    ):
        """Send reset links to the designer's reachable email address.

        Falls back to the profile contact email when the core ``User`` record
        does not have an address (common for imported legacy accounts).
        """

        identifier = self.cleaned_data["email"]
        if not domain_override:
            current_site = get_current_site(request)
            site_name = current_site.name
            domain = current_site.domain
        else:
            site_name = domain = domain_override

        UserModel = get_user_model()
        email_field_name = UserModel.get_email_field_name()

        for user in self.get_users(identifier):
            user_email = (getattr(user, email_field_name) or "").strip()

            if not user_email:
                profile = getattr(user, "designer_profile", None)
                if profile:
                    user_email = (getattr(profile, "contact_email", "") or "").strip()

            if not user_email:
                continue  # Still no valid destination

            user_pk_bytes = force_bytes(UserModel._meta.pk.value_to_string(user))
            context = {
                "email": user_email,
                "domain": domain,
                "site_name": site_name,
                "uid": urlsafe_base64_encode(user_pk_bytes),
                "user": user,
                "token": token_generator.make_token(user),
                "protocol": "https" if use_https else "http",
                **(extra_email_context or {}),
            }

            self.send_mail(
                subject_template_name,
                email_template_name,
                context,
                from_email,
                user_email,
                html_email_template_name=html_email_template_name,
            )
            notify_password_reset_request(user, request=request)


class ReportProblemForm(forms.ModelForm):
    """Public form for reporting website, technical, billing, or other issues."""

    class Meta:
        model = ProblemReport
        fields = ["name", "email", "category", "subject", "message", "page_url"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Your name (optional)",
                    "autocomplete": "name",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Email address we can reach",
                    "autocomplete": "email",
                    "required": True,
                }
            ),
            "category": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "subject": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Short summary (e.g., Billing page is down)",
                    "maxlength": 200,
                    "required": True,
                }
            ),
            "message": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": "Describe the issue or improvement in detail...",
                }
            ),
            "page_url": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "https://globaldesignerhub.com/pricing (optional)",
                    "autocomplete": "url",
                }
            ),
        }

    def clean_message(self):
        message = (self.cleaned_data.get("message") or "").strip()
        if len(message) < 20:
            raise forms.ValidationError("Please share at least 20 characters so we understand the issue.")
        return message

    def clean_subject(self):
        subject = (self.cleaned_data.get("subject") or "").strip()
        if len(subject) < 5:
            raise forms.ValidationError("Add a short subject (at least 5 characters).")
        return subject


class ContactForm(forms.Form):
    """Simple public contact form used at /contact."""

    name = forms.CharField(max_length=80, label="Name")
    email = forms.EmailField(label="Email address")
    subject = forms.CharField(max_length=150, label="Subject")
    message = forms.CharField(widget=forms.Textarea(attrs={"rows": 5}), label="Message")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        placeholders = {
            "name": "Your name",
            "email": "Email",
            "subject": "Subject",
            "message": "Message",
        }
        for field_name, field in self.fields.items():
            attrs = field.widget.attrs
            attrs.setdefault("class", "contact-field")
            attrs["placeholder"] = placeholders[field_name]
            if field_name != "message":
                attrs.setdefault("autocomplete", "on")

    def clean_message(self):
        message = (self.cleaned_data.get("message") or "").strip()
        if len(message) < 10:
            raise forms.ValidationError("Share at least 10 characters so we can assist you.")
        return message


class EventAttendeeForm(forms.ModelForm):
    class Meta:
        model = EventAttendee
        fields = ["full_name", "email", "company", "title", "ticket_count", "notes"]
        widgets = {
            "full_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Full name", "autocomplete": "name"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-control", "placeholder": "Email address", "autocomplete": "email"}
            ),
            "company": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Company or label (optional)"}
            ),
            "title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Role or title (optional)"}
            ),
            "ticket_count": forms.NumberInput(
                attrs={"class": "form-control", "min": 1, "max": 10}
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Any accessibility or guest notes (optional)",
                }
            ),
        }

    def clean_ticket_count(self):
        count = self.cleaned_data.get("ticket_count") or 1
        if count < 1:
            raise forms.ValidationError("Ticket quantity must be at least 1.")
        return count


class EventCollaborationForm(forms.ModelForm):
    class Meta:
        model = EventCollaboration
        fields = ["full_name", "email", "company", "role", "portfolio_url", "message"]
        widgets = {
            "full_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Full name", "autocomplete": "name"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-control", "placeholder": "Email address", "autocomplete": "email"}
            ),
            "company": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Company or label (optional)"}
            ),
            "role": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Collaboration focus (styling, PR, production)"}
            ),
            "portfolio_url": forms.URLInput(
                attrs={"class": "form-control", "placeholder": "Portfolio or reel link (optional)"}
            ),
            "message": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Tell us how you would like to collaborate",
                }
            ),
        }


class ProjectCreateForm(forms.Form):
    template_id = forms.CharField(max_length=120)
    title = forms.CharField(max_length=255)
    subtitle = forms.CharField(max_length=255, required=False)
    client_name = forms.CharField(max_length=255, required=False)
    season = forms.CharField(max_length=10, required=False)
    product_type = forms.CharField(max_length=40, required=False, initial=Project.ProductType.HOODIE)
    product_count = forms.IntegerField(min_value=1, max_value=50, initial=1)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._template_instance = None
        self._template_snapshot = None

    def clean_template_id(self):
        template_id = (self.cleaned_data.get("template_id") or "").strip()
        if not template_id:
            raise forms.ValidationError("Choose a template to continue.")
        try:
            self._template_instance = (
                Template.objects.prefetch_related("stages", "product_blocks")
                .get(id=template_id)
            )
        except Template.DoesNotExist:
            raise forms.ValidationError("Template not found.")
        return template_id

    def clean_season(self):
        season = (self.cleaned_data.get("season") or "").strip()
        if season and season not in dict(Project.SeasonChoices.choices):
            raise forms.ValidationError("Invalid season selection.")
        return season

    def clean_product_type(self):
        product_type = (self.cleaned_data.get("product_type") or Project.ProductType.HOODIE).strip()
        valid_values = [choice[0] for choice in Project.ProductType.choices]
        if product_type not in valid_values:
            raise forms.ValidationError("Invalid product type.")
        return product_type

    def clean_product_count(self):
        count = self.cleaned_data.get("product_count") or 1
        if count < 1:
            raise forms.ValidationError("Number of products must be at least 1.")
        return count

    @property
    def template_instance(self):
        return self._template_instance

    @property
    def template_data(self):
        if self._template_snapshot is None and self._template_instance is not None:
            self._template_snapshot = serialize_template_instance(self._template_instance)
        return self._template_snapshot or {}


class StudentPortfolioForm(forms.ModelForm):
    class Meta:
        model = StudentPortfolio
        fields = [
            "profile_photo",
            "bio",
            "skills",
            "design_interests",
            "template_style",
            "visibility",
        ]
        widgets = {
            "bio": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Share your design story and interests",
                }
            ),
            "skills": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Figma, Adobe XD, Blender, Illustrator",
                }
            ),
            "design_interests": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "UI/UX, Branding, Product systems",
                }
            ),
            "template_style": forms.Select(attrs={"class": "form-control"}),
            "visibility": forms.Select(attrs={"class": "form-control"}),
        }

    def clean_skills(self):
        return ", ".join([item.strip() for item in (self.cleaned_data.get("skills") or "").split(",") if item.strip()])

    def clean_design_interests(self):
        return ", ".join(
            [item.strip() for item in (self.cleaned_data.get("design_interests") or "").split(",") if item.strip()]
        )


class StudentPortfolioProjectForm(forms.ModelForm):
    class Meta:
        model = StudentPortfolioProject
        fields = [
            "title",
            "description",
            "category",
            "tools_used",
            "project_role",
            "process_steps",
            "cover_image",
            "process_video",
            "project_pdf",
            "featured",
        ]
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Project title",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Describe the objective, constraints, and outcome.",
                }
            ),
            "category": forms.Select(attrs={"class": "form-control"}),
            "tools_used": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Figma, Photoshop, Principle",
                }
            ),
            "project_role": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Lead Designer, UX Researcher, Visual Designer",
                }
            ),
            "process_steps": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Sketches\nWireframes\nHigh-fidelity mockups\nPrototype",
                }
            ),
            "featured": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean_tools_used(self):
        return ", ".join([item.strip() for item in (self.cleaned_data.get("tools_used") or "").split(",") if item.strip()])


class StudentProjectFeedbackForm(forms.ModelForm):
    class Meta:
        model = StudentProjectFeedback
        fields = ["reviewer_role", "comment"]
        widgets = {
            "reviewer_role": forms.Select(attrs={"class": "form-control"}),
            "comment": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Share specific and constructive feedback.",
                }
            ),
        }

    def clean_comment(self):
        comment = (self.cleaned_data.get("comment") or "").strip()
        if len(comment) < 10:
            raise forms.ValidationError("Please write at least 10 characters of feedback.")
        return comment
