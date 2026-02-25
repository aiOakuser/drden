from django.db import models
from django.utils.text import slugify
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator


class HTTPSURLField(models.URLField):
    """URLField that assumes https for schemeless URLs (Django 6.0-ready)."""

    def formfield(self, **kwargs):
        kwargs.setdefault("assume_scheme", "https")
        return super().formfield(**kwargs)


# ---------------- Base Timestamp ----------------
class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# ---------------- Brand ----------------
class Brand(TimeStampedModel):
    name = models.CharField(max_length=100, default="designer")
    tagline = models.CharField(max_length=160, blank=True)
    logo = models.ImageField(upload_to="brand/", blank=True, null=True)
    primary_color = models.CharField(max_length=7, default="#0E0E0F")  # deep charcoal
    secondary_color = models.CharField(max_length=7, default="#2A2A2C")  # warm graphite
    accent_color = models.CharField(max_length=7, default="#D8B57A")  # soft gold
    primary_font = models.CharField(max_length=100, default="Playfair Display")
    secondary_font = models.CharField(max_length=100, default="Inter")

    def __str__(self):
        return self.name


# ---------------- Collection ----------------
class Collection(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    year = models.PositiveIntegerField(default=2024)
    season = models.CharField(max_length=100, blank=True, null=True)
    cover_image = models.ImageField(upload_to="collection_covers/", blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    designer = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        ordering = ["-year", "name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.name}-{self.year}")
            slug = base_slug
            counter = 1
            while Collection.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} – {self.year}"


class CollectionImage(models.Model):
    collection = models.ForeignKey(Collection, related_name="gallery", on_delete=models.CASCADE)
    image = models.ImageField(upload_to="collections/gallery/")
    caption = models.CharField(max_length=255, blank=True, null=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"Image for {self.collection.name} ({self.collection.year})"

class Look(models.Model):
    collection = models.ForeignKey(Collection, related_name="looks", on_delete=models.CASCADE)
    look_number = models.PositiveIntegerField(default=1)
    title = models.CharField(max_length=120, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="collections/looks/", blank=True, null=True)
    fabric = models.CharField(max_length=200, blank=True, null=True)
    measurements = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["look_number"]
        unique_together = [("collection", "look_number")]

    def __str__(self):
        return f"{self.collection.name} – Look {self.look_number}"


# ---------------- Design ----------------
class Design(TimeStampedModel):
    title = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    designer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="designs")
    season = models.CharField(max_length=50, blank=True)
    year = models.PositiveIntegerField(default=2025)
    cover_image = models.ImageField(upload_to="designs/covers/", blank=True, null=True)
    description = models.TextField(blank=True)
    published = models.BooleanField(default=True)

    # Classification & target audience
    category = models.CharField(max_length=100, blank=True)
    target_market = models.CharField(max_length=50, blank=True)
    featured = models.BooleanField(default=False)

    # Fabric & construction details
    fabric_type = models.CharField(max_length=200, blank=True)
    fabric_weight = models.CharField(max_length=100, blank=True)
    fabric_details = models.TextField(blank=True, help_text="Fabric specifications and requirements")

    # Commercial details
    color_palette = models.CharField(max_length=500, blank=True, help_text="Color codes and descriptions")
    size_range = models.CharField(
        max_length=100,
        blank=True,
        help_text="Available size range (e.g., XS-XL)",
    )
    target_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Target retail price",
    )

    # Notes & production details
    production_notes = models.TextField(blank=True, help_text="Special production requirements or notes")
    design_notes = models.TextField(blank=True, help_text="Internal notes for review before publishing")

    # Tech pack files
    techpack_pdf = models.FileField(
        upload_to="designs/techpacks/pdf/",
        blank=True,
        null=True,
        help_text="Upload tech pack as PDF file",
    )
    techpack_excel = models.FileField(
        upload_to="designs/techpacks/excel/",
        blank=True,
        null=True,
        help_text="Upload tech pack as Excel file",
    )

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.title}-{self.year}")
            slug = base_slug
            counter = 1
            while Design.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} ({self.year}) by {self.designer.username}"
    
    @property
    def has_techpack(self):
        return bool(self.techpack_pdf or self.techpack_excel)

    @property
    def is_public(self):
        return self.published

    @is_public.setter
    def is_public(self, value):
        self.published = bool(value)
    
    class Meta:
        ordering = ['-created_at']


# ---------------- Techpack ----------------
class Techpack(TimeStampedModel):
    design = models.OneToOneField(Design, related_name="techpack", on_delete=models.CASCADE)
    fabric = models.CharField(max_length=255, blank=True)
    trims = models.TextField(blank=True)
    measurements = models.TextField(blank=True)
    bom_file = models.FileField(upload_to="techpacks/bom/", blank=True, null=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Techpack for {self.design.title}"


# ---------------- Design Images ----------------
class DesignImage(TimeStampedModel):
    design = models.ForeignKey(Design, related_name="images", on_delete=models.CASCADE)
    image = models.ImageField(upload_to="designs/gallery/")
    caption = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "created_at"]

    def __str__(self):
        return f"Image for {self.design.title}"


# ---------------- Event ----------------
class Event(TimeStampedModel):
    title = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    description = models.TextField(blank=True)
    cover = models.ImageField(upload_to="events/covers/", blank=True, null=True)
    event_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    location = models.CharField(max_length=160, blank=True)
    venue = models.CharField(max_length=160, blank=True)
    attendee_capacity = models.PositiveIntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(1)],
        help_text="Optional headcount limit for attendee RSVPs.",
    )
    collaboration_deadline = models.DateField(
        blank=True,
        null=True,
        help_text="Optional cutoff for collaboration requests.",
    )
    is_popup = models.BooleanField(default=False)  # popup event toggle
    popup_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-event_date", "-created_at"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.title


# ---------------- Event Images ----------------
class EventImage(TimeStampedModel):
    event = models.ForeignKey(Event, related_name="images", on_delete=models.CASCADE)
    image = models.ImageField(upload_to="events/images/")
    caption = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "created_at"]

    def __str__(self):
        return f"Image for {self.event.title}"


class EventAttendee(TimeStampedModel):
    event = models.ForeignKey(Event, related_name="attendees", on_delete=models.CASCADE)
    full_name = models.CharField(max_length=120)
    email = models.EmailField()
    company = models.CharField(max_length=120, blank=True)
    title = models.CharField(max_length=120, blank=True)
    ticket_count = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    notes = models.TextField(blank=True)
    checked_in = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        unique_together = [("event", "email")]

    def __str__(self):
        return f"{self.full_name} – {self.event.title}"


class EventCollaboration(TimeStampedModel):
    STATUS_NEW = "new"
    STATUS_REVIEWED = "reviewed"
    STATUS_ACCEPTED = "accepted"
    STATUS_DECLINED = "declined"

    STATUS_CHOICES = [
        (STATUS_NEW, "New"),
        (STATUS_REVIEWED, "Reviewed"),
        (STATUS_ACCEPTED, "Accepted"),
        (STATUS_DECLINED, "Declined"),
    ]

    event = models.ForeignKey(Event, related_name="collaboration_requests", on_delete=models.CASCADE)
    full_name = models.CharField(max_length=120)
    email = models.EmailField()
    company = models.CharField(max_length=120, blank=True)
    role = models.CharField(max_length=120, blank=True)
    portfolio_url = HTTPSURLField(blank=True)
    message = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_NEW)
    is_contacted = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        unique_together = [("event", "email")]

    def __str__(self):
        return f"{self.full_name} – {self.event.title}"


class RejectedDesigner(models.Model):
    username = models.CharField(max_length=150)
    email = models.EmailField()
    reason = models.TextField(blank=True, null=True)
    rejected_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.username} (Rejected on {self.rejected_at:%Y-%m-%d})"


class DesignerQuestion(models.Model):
    category = models.CharField(max_length=200)
    question = models.TextField()

    def __str__(self):
        return self.question[:60]


class ProblemReport(TimeStampedModel):
    CATEGORY_WEBSITE = "website"
    CATEGORY_TECHNICAL = "technical"
    CATEGORY_BILLING = "billing"
    CATEGORY_OTHER = "other"

    CATEGORY_CHOICES = [
        (CATEGORY_WEBSITE, "Website improvement"),
        (CATEGORY_TECHNICAL, "Technical issue"),
        (CATEGORY_BILLING, "Billing or subscription"),
        (CATEGORY_OTHER, "Other"),
    ]

    STATUS_OPEN = "open"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_CLOSED = "closed"

    STATUS_CHOICES = [
        (STATUS_OPEN, "Open"),
        (STATUS_IN_PROGRESS, "In progress"),
        (STATUS_CLOSED, "Closed"),
    ]

    reporter = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="problem_reports",
        help_text="Authenticated user who filed the report (if available).",
    )
    name = models.CharField(max_length=120, blank=True)
    email = models.EmailField(help_text="Address we can reply to.")
    category = models.CharField(
        max_length=32, choices=CATEGORY_CHOICES, default=CATEGORY_OTHER
    )
    subject = models.CharField(max_length=200)
    message = models.TextField()
    page_url = models.CharField(
        max_length=500, blank=True, help_text="Optional page URL where the issue occurred."
    )
    status = models.CharField(
        max_length=32, choices=STATUS_CHOICES, default=STATUS_OPEN
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_category_display()} – {self.subject}"

    @property
    def reporter_display_name(self) -> str:
        if self.name:
            return self.name
        if self.reporter:
            return self.reporter.get_full_name() or self.reporter.get_username()
        return "Anonymous"


# ---------------- Designer Profile ----------------
class DesignerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='designer_profile')
    bio = models.TextField(max_length=1000, blank=True, default="", help_text="Tell us about yourself and your design philosophy")
    profile_image = models.ImageField(upload_to="designers/profiles/", blank=True, null=True)
    portfolio_website = HTTPSURLField(blank=True, help_text="Your personal website or portfolio")
    instagram_handle = models.CharField(max_length=100, blank=True, help_text="Instagram username (without @)")
    linkedin_profile = HTTPSURLField(blank=True, help_text="LinkedIn profile URL")
    
    # Professional details
    years_of_experience = models.PositiveIntegerField(default=0, help_text="Years of design experience")
    specialization = models.CharField(
        max_length=200, 
        blank=True, 
        help_text="e.g., Sustainable Fashion, Avant-garde, Streetwear"
    )
    education = models.CharField(max_length=300, blank=True, help_text="Educational background")
    location = models.CharField(max_length=100, blank=True, help_text="City, Country")
    region_area = models.CharField(
        max_length=120,
        blank=True,
        default="West Coast",
        help_text="Broader area or territory label (e.g., West Coast, EMEA).",
        db_index=True,
    )
    country = models.CharField(
        max_length=120,
        blank=True,
        help_text="Country",
        db_index=True,
    )
    state_province = models.CharField(
        max_length=120,
        blank=True,
        help_text="State or province",
        db_index=True,
    )
    county = models.CharField(
        max_length=120,
        blank=True,
        help_text="County or district",
        db_index=True,
    )
    city = models.CharField(
        max_length=120,
        blank=True,
        help_text="City or municipality",
        db_index=True,
    )
    
    # Contact preferences
    available_for_collaborations = models.BooleanField(default=True)
    contact_email = models.EmailField(blank=True, help_text="Public contact email (optional)")

    # Referral (synced from UserReferralProfile for backwards compatibility)
    referred_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="referred_profiles",
        help_text="User who referred this designer via invite link",
    )
    
    # Portfolio template selection (applies default for all designers)
    PORTFOLIO_TEMPLATES = [
        ("classic", "Classic"),
        ("modern", "Modern"),
        ("minimal", "Minimal"),
    ]
    portfolio_template = models.CharField(
        max_length=20,
        choices=PORTFOLIO_TEMPLATES,
        default="classic",
        help_text="Select the default portfolio template style",
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"
    
    class Meta:
        verbose_name = "Designer Profile"
        verbose_name_plural = "Designer Profiles"

    @property
    def public_contact_email(self) -> str:
        """Return the best contact email to expose publicly."""
        email = (self.contact_email or "").strip()
        if email:
            return email

        user_email = (getattr(self.user, "email", "") or "").strip()
        return user_email

    def _structured_location_parts(self) -> list[str]:
        return [
            part.strip()
            for part in [
                self.city or "",
                self.county or "",
                self.state_province or "",
                self.country or "",
            ]
            if part
        ]

    @property
    def location_display(self) -> str:
        parts = self._structured_location_parts()
        if parts:
            return ", ".join(parts)
        return self.location or ""

    def _hydrate_structured_location_fields(self) -> None:
        """
        Backfill structured location fields from the legacy free-form location field
        when designers have not populated the new inputs yet.
        """

        if self._structured_location_parts():
            return

        legacy_label = (self.location or "").strip()
        if not legacy_label:
            return

        tokens = [token.strip() for token in legacy_label.split(",") if token.strip()]
        if not tokens:
            return

        if not self.city:
            self.city = tokens[0]

        if len(tokens) >= 3:
            state_candidate = tokens[-2]
            country_candidate = tokens[-1]
        elif len(tokens) == 2:
            state_candidate = tokens[1]
            country_candidate = tokens[-1]
        else:
            state_candidate = ""
            country_candidate = ""

        if state_candidate and not self.state_province:
            self.state_province = state_candidate

        if country_candidate and not self.country:
            self.country = country_candidate

    def save(self, *args, **kwargs):
        self._hydrate_structured_location_fields()
        super().save(*args, **kwargs)


# ---------------- Subscription Models ----------------
class WebAuthnCredential(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="webauthn_credentials")
    credential_id = models.BinaryField(unique=True)
    public_key = models.BinaryField()
    sign_count = models.PositiveBigIntegerField(default=0)
    transports = models.JSONField(default=list, blank=True)
    nickname = models.CharField(max_length=150, blank=True)
    attestation_format = models.CharField(max_length=50, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "WebAuthn Credential"
        verbose_name_plural = "WebAuthn Credentials"

    def __str__(self):
        if self.nickname:
            return f"{self.nickname} ({self.user.username})"
        return f"{self.user.username} WebAuthn credential"


class SubscriptionPlan(models.Model):
    PLAN_TYPES = [
        ('weekly', 'Weekly'),
        ('biweekly', 'Bi-Weekly'),
        ('monthly', 'Monthly'),
        ('6months', '6 Months'),
        ('yearly', 'Yearly'),
    ]
    
    name = models.CharField(max_length=50, choices=PLAN_TYPES, unique=True)
    display_name = models.CharField(max_length=100, default="Standard Plan")
    price = models.DecimalField(max_digits=8, decimal_places=2)
    duration_days = models.IntegerField()  # Duration in days
    stripe_price_id = models.CharField(max_length=200, blank=True, null=True)
    paypal_plan_id = models.CharField(max_length=200, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.display_name} - ${self.price}"
    
    class Meta:
        ordering = ['price']


class UserSubscription(models.Model):
    PAYMENT_METHODS = [
        ('stripe', 'Stripe (Credit/Debit Card)'),
        ('paypal', 'PayPal'),
        ('applepay', 'Apple Pay'),
    ]
    
    STATUS_CHOICES = [
        ('free_trial', 'Free Trial'),
        ('active', 'Active'),
        ('frozen', 'Frozen'),  # Policy violation (e.g., contact sharing); blocks messenger
        ('canceled', 'Canceled'),
        ('expired', 'Expired'),
        ('past_due', 'Past Due'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='free_trial')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, blank=True, null=True)
    
    # Trial information
    trial_start_date = models.DateTimeField(null=True, blank=True)
    trial_end_date = models.DateTimeField(null=True, blank=True)
    
    # Subscription information
    subscription_start_date = models.DateTimeField(null=True, blank=True)
    subscription_end_date = models.DateTimeField(null=True, blank=True)
    
    # Payment provider IDs
    stripe_customer_id = models.CharField(max_length=200, blank=True, null=True)
    stripe_subscription_id = models.CharField(max_length=200, blank=True, null=True)
    paypal_subscription_id = models.CharField(max_length=200, blank=True, null=True)
    
    # Billing information
    next_billing_date = models.DateTimeField(null=True, blank=True)
    last_payment_date = models.DateTimeField(null=True, blank=True)
    auto_renewal = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Acquisition/Attribution (nullable, filled from UTM/session)
    acquisition_source = models.CharField(max_length=100, blank=True, null=True)
    acquisition_medium = models.CharField(max_length=100, blank=True, null=True)
    acquisition_campaign = models.CharField(max_length=150, blank=True, null=True)
    acquisition_content = models.CharField(max_length=150, blank=True, null=True)
    acquisition_term = models.CharField(max_length=150, blank=True, null=True)
    acquisition_landing_page = HTTPSURLField(blank=True, null=True)
    acquisition_initial_referrer = HTTPSURLField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.status}"
    
    @property
    def is_trial_active(self):
        from django.utils import timezone
        return self.status == 'free_trial' and self.trial_end_date > timezone.now()
    
    @property
    def is_subscription_active(self):
        from django.utils import timezone
        return self.status == 'active' and self.subscription_end_date and self.subscription_end_date > timezone.now()
    
    @property
    def days_left_in_trial(self):
        from django.utils import timezone
        if self.is_trial_active:
            return (self.trial_end_date - timezone.now()).days
        return 0

    @property
    def is_frozen(self):
        """True if account is frozen due to policy violation (e.g., contact sharing)."""
        return self.status == 'frozen'

    def can_use_designer_messenger(self):
        """
        Designer-to-designer messenger requires $4.99/month or higher subscription.
        Frozen accounts cannot use messenger.
        """
        from django.utils import timezone
        if self.status == 'frozen':
            return False
        if self.status == 'active' and self.plan and self.subscription_end_date and self.subscription_end_date > timezone.now():
            # Must have monthly ($4.99) or higher plan
            min_price = 4.99
            return float(self.plan.price) >= min_price
        return False


# ==================== Referral System ====================

class ReferralTier(models.Model):
    """Config table for referral tiers (starter, influencer, ambassador, legend)."""
    code = models.SlugField(unique=True)
    name = models.CharField(max_length=80)
    min_referrals = models.PositiveIntegerField()
    sort_order = models.PositiveIntegerField(default=0)
    benefits = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "min_referrals"]

    def __str__(self):
        return f"{self.name} ({self.min_referrals}+)"


class UserReferralProfile(models.Model):
    """Per-user referral profile: code, counters, tier. Created on first access."""
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="referral_profile"
    )
    referral_code = models.CharField(max_length=32, unique=True, db_index=True)

    referred_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="referrals_made",
        help_text="User who referred this user via invite link",
    )
    referral_joined_at = models.DateTimeField(null=True, blank=True)

    referral_count = models.PositiveIntegerField(
        default=0,
        help_text="Denormalized count for fast leaderboard",
    )
    referral_points = models.PositiveIntegerField(default=0)

    current_tier = models.ForeignKey(
        ReferralTier,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="users",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User Referral Profile"
        verbose_name_plural = "User Referral Profiles"

    def __str__(self):
        return f"{self.user} ({self.referral_code})"


class ReferralEvent(models.Model):
    """Audit trail: one event per referred user. Prevents double crediting."""
    referrer = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="referral_events"
    )
    referred_user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="referral_event"
    )
    referral_code = models.CharField(max_length=32)
    source = models.CharField(max_length=32, null=True, blank=True)
    ip_hash = models.CharField(max_length=128, null=True, blank=True)
    user_agent_hash = models.CharField(max_length=128, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["referrer", "-created_at"], name="refev_referrer_created_idx"),
            models.Index(fields=["-created_at"], name="refev_created_idx"),
        ]

    def __str__(self):
        return f"{self.referrer} -> {self.referred_user} ({self.referral_code})"


# ==================== Designer AI Chat ====================

class DesignerAISession(TimeStampedModel):
    """Stores chat sessions for Designer AI conversations."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ai_sessions", null=True, blank=True)
    session_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    language = models.CharField(max_length=10, default="en")
    metadata = models.JSONField(default=dict, blank=True)  # Store onboarding progress, preferences, etc.
    
    class Meta:
        ordering = ["-created_at"]
    
    def __str__(self):
        if self.user:
            return f"Session {self.id} - {self.user.username}"
        return f"Session {self.id}"


class DesignerAIMessage(TimeStampedModel):
    """Individual messages in a chat session."""
    session = models.ForeignKey(DesignerAISession, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=20, choices=[
        ("system", "System"),
        ("user", "User"),
        ("assistant", "Assistant"),
    ])
    content = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)  # Store RAG sources, etc.
    
    class Meta:
        ordering = ["created_at"]
    
    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."


# ==================== User-to-User Messenger ====================

class ChatConversation(TimeStampedModel):
    """One-to-one conversation between two registered users."""
    user1 = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="chat_conversations_as_user1"
    )
    user2 = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="chat_conversations_as_user2"
    )

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user1", "user2"],
                name="designer_portfolio_chatconversation_unique_pair",
            ),
        ]

    def __str__(self):
        return f"Chat {self.user1.username} & {self.user2.username}"

    def other_user(self, user):
        """Return the participant who is not the given user."""
        return self.user2 if user == self.user1 else self.user1

    def last_message(self):
        return self.messages.order_by("-created_at").first()


class ChatMessage(TimeStampedModel):
    """Single message in a user-to-user conversation."""
    conversation = models.ForeignKey(
        ChatConversation, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="chat_messages_sent"
    )
    body = models.TextField()
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.sender.username}: {self.body[:50]}..."


class DocPage(TimeStampedModel):
    """Documentation pages for RAG retrieval."""
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    content = models.TextField()
    language = models.CharField(max_length=10, default="en")
    category = models.CharField(max_length=100, blank=True)  # e.g., "designers", "api", "getting-started"
    tags = models.CharField(max_length=500, blank=True)  # Comma-separated tags
    order = models.IntegerField(default=0)
    published = models.BooleanField(default=True)
    
    class Meta:
        ordering = ["order", "title"]
    
    def __str__(self):
        return self.title


# ---------------- Community Forum Models ----------------
class ForumCategory(TimeStampedModel):
    """Forum categories to organize topics"""
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="FontAwesome icon class")
    color = models.CharField(max_length=7, default="#FF6B35", help_text="Hex color code")
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    moderators = models.ManyToManyField(User, related_name='moderated_categories', blank=True)
    
    class Meta:
        ordering = ['order', 'name']
        verbose_name_plural = "Forum Categories"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name
    
    def get_topic_count(self):
        return self.topics.filter(is_active=True).count()
    
    def get_post_count(self):
        return ForumPost.objects.filter(topic__category=self, is_active=True).count()


class ForumTopic(TimeStampedModel):
    """Forum topics/threads"""
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    content = models.TextField()
    category = models.ForeignKey(ForumCategory, on_delete=models.CASCADE, related_name='topics')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='forum_topics')
    
    # Topic status
    is_active = models.BooleanField(default=True)
    is_pinned = models.BooleanField(default=False)
    is_locked = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    
    # Topic metadata
    view_count = models.PositiveIntegerField(default=0)
    last_activity = models.DateTimeField(auto_now_add=True)
    last_post = models.ForeignKey('ForumPost', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    
    # Tags for better organization
    tags = models.CharField(max_length=200, blank=True, help_text="Comma-separated tags")
    
    class Meta:
        ordering = ['-is_pinned', '-last_activity']
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while ForumTopic.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.title
    
    def get_post_count(self):
        return self.posts.filter(is_active=True).count()
    
    def get_tag_list(self):
        return [tag.strip() for tag in self.tags.split(',') if tag.strip()]


class ForumPost(TimeStampedModel):
    """Forum posts/replies"""
    topic = models.ForeignKey(ForumTopic, on_delete=models.CASCADE, related_name='posts')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='forum_posts')
    content = models.TextField()
    
    # Post metadata
    is_active = models.BooleanField(default=True)
    is_solution = models.BooleanField(default=False, help_text="Mark as solution to the topic")
    edited_at = models.DateTimeField(null=True, blank=True)
    
    # Moderation
    is_flagged = models.BooleanField(default=False)
    moderation_notes = models.TextField(blank=True)
    
    # Parent for threaded replies
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Post by {self.author.username} in {self.topic.title}"
    
    def get_reply_count(self):
        return self.replies.filter(is_active=True).count()


class ForumLike(TimeStampedModel):
    """Likes for forum posts"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(ForumPost, on_delete=models.CASCADE, related_name='likes')
    
    class Meta:
        unique_together = ['user', 'post']
    
    def __str__(self):
        return f"{self.user.username} liked {self.post.id}"


class ForumBookmark(TimeStampedModel):
    """User bookmarks for topics"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    topic = models.ForeignKey(ForumTopic, on_delete=models.CASCADE, related_name='bookmarks')
    
    class Meta:
        unique_together = ['user', 'topic']
    
    def __str__(self):
        return f"{self.user.username} bookmarked {self.topic.title}"


class ForumNotification(TimeStampedModel):
    """Notifications for forum activity"""
    NOTIFICATION_TYPES = [
        ('reply', 'New Reply'),
        ('mention', 'Mentioned'),
        ('like', 'Post Liked'),
        ('solution', 'Solution Marked'),
        ('topic_created', 'New Topic in Category'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='forum_notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    topic = models.ForeignKey(ForumTopic, on_delete=models.CASCADE, null=True)
    post = models.ForeignKey(ForumPost, on_delete=models.CASCADE, null=True)
    triggered_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='triggered_notifications')
    
    is_read = models.BooleanField(default=False)
    message = models.CharField(max_length=200, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Notification for {self.user.username}: {self.notification_type}"


class ForumUserProfile(TimeStampedModel):
    """Extended forum profile for users"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='forum_profile')
    
    # Forum-specific settings
    signature = models.CharField(max_length=200, blank=True)
    show_online_status = models.BooleanField(default=True)
    email_notifications = models.BooleanField(default=True)
    
    # Forum statistics
    post_count = models.PositiveIntegerField(default=0)
    topic_count = models.PositiveIntegerField(default=0)
    solution_count = models.PositiveIntegerField(default=0)
    reputation_score = models.IntegerField(default=0)
    
    # Moderation
    warning_count = models.PositiveIntegerField(default=0)
    is_banned = models.BooleanField(default=False)
    ban_reason = models.TextField(blank=True)
    ban_until = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Forum User Profile"
        verbose_name_plural = "Forum User Profiles"
    
    def __str__(self):
        return f"Forum profile for {self.user.username}"
    
    def get_user_level(self):
        """Return user level based on post count"""
        if self.post_count >= 1000:
            return "Expert"
        elif self.post_count >= 500:
            return "Advanced"
        elif self.post_count >= 100:
            return "Regular"
        elif self.post_count >= 20:
            return "Member"
        else:
            return "Newcomer"


# ---------------- Template Library ----------------
class Template(TimeStampedModel):
    id = models.CharField(primary_key=True, max_length=120)
    name = models.CharField(max_length=255)
    layout_key = models.CharField(max_length=120)
    cover_title_placeholder = models.CharField(max_length=255)
    cover_subtitle_placeholder = models.CharField(max_length=255)
    summary = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "templates"
        ordering = ["name", "id"]

    def __str__(self):
        return self.name

    @property
    def cover(self) -> dict[str, str]:
        """Return cover settings as a dict with default fallbacks."""
        return {
            "titlePlaceholder": self.cover_title_placeholder,
            "subtitlePlaceholder": self.cover_subtitle_placeholder,
        }


class TemplateStage(TimeStampedModel):
    template = models.ForeignKey(Template, on_delete=models.CASCADE, related_name="stages")
    stage_index = models.PositiveIntegerField()
    title = models.CharField(max_length=200)
    default_items = models.JSONField(default=list, blank=True)
    layout_hint = models.CharField(max_length=120, blank=True)

    class Meta:
        db_table = "template_stages"
        ordering = ["stage_index", "id"]
        unique_together = [("template", "stage_index")]

    def __str__(self):
        return f"{self.template_id} – Stage {self.stage_index}"


class TemplateProductBlock(TimeStampedModel):
    template = models.ForeignKey(Template, on_delete=models.CASCADE, related_name="product_blocks")
    block_index = models.PositiveIntegerField()
    label = models.CharField(max_length=200)
    title_placeholder = models.CharField(max_length=200)
    code_placeholder = models.CharField(max_length=120, blank=True)
    default_views = models.JSONField(default=list, blank=True)
    details_schema = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "template_product_blocks"
        ordering = ["block_index", "id"]
        unique_together = [("template", "block_index")]

    def __str__(self):
        return f"{self.template_id} – Block {self.block_index}"


# ---------------- Project Templates & Breakdowns ----------------
class Project(TimeStampedModel):
    class SeasonChoices(models.TextChoices):
        SS25 = ("SS25", "Spring / Summer 2025")
        FW25 = ("FW25", "Fall / Winter 2025")
        SS26 = ("SS26", "Spring / Summer 2026")
        FW26 = ("FW26", "Fall / Winter 2026")

    class ProductType(models.TextChoices):
        HOODIE = ("hoodie", "Hoodie")
        SHELL = ("shell", "Shell / Outerwear")
        TEE = ("tee", "Tee")
        BOTTOM = ("bottom", "Bottom")
        ACCESSORY = ("accessory", "Accessory")

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="projects")
    template_id = models.CharField(max_length=120)
    template_name = models.CharField(max_length=200)
    template_category = models.CharField(max_length=120, blank=True)
    template_layout_key = models.CharField(max_length=120, blank=True)
    template_snapshot = models.JSONField(default=dict, blank=True, help_text="Frozen copy of template JSON used at creation time.")

    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, blank=True)
    client_name = models.CharField(max_length=255, blank=True)
    season = models.CharField(max_length=10, choices=SeasonChoices.choices, blank=True)
    product_type = models.CharField(
        max_length=40,
        choices=ProductType.choices,
        default=ProductType.HOODIE,
    )
    product_count = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    preview_copy = models.JSONField(default=list, blank=True, help_text="Short copy lines surfaced under the live preview.")
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} • {self.template_name}"

    @property
    def cover(self):
        cover = self.template_snapshot.get("cover", {})
        if not isinstance(cover, dict):
            cover = {}
        if self.subtitle:
            cover = dict(cover)
            cover["subtitle"] = self.subtitle
            cover.setdefault("subtitlePlaceholder", self.subtitle)
        return cover

    @property
    def summary_lines(self):
        return self.preview_copy or self.template_snapshot.get("summary", [])


class ProjectStage(TimeStampedModel):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="stages")
    template_stage = models.ForeignKey(
        TemplateStage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="project_stages",
    )
    stage_number = models.PositiveIntegerField(default=1)
    title = models.CharField(max_length=200)
    layout_hint = models.CharField(max_length=120, blank=True)
    order = models.PositiveIntegerField(default=1)
    items = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["order", "stage_number"]
        unique_together = [("project", "stage_number")]

    def __str__(self):
        return f"{self.project.title} – Stage {self.stage_number}"


class ProjectStageBullet(TimeStampedModel):
    stage = models.ForeignKey(ProjectStage, on_delete=models.CASCADE, related_name="bullets")
    order = models.PositiveIntegerField(default=1)
    text = models.CharField(max_length=300)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.stage} • {self.text[:40]}"


class ProjectProductSpec(TimeStampedModel):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="product_specs")
    template_block = models.ForeignKey(
        TemplateProductBlock,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="project_products",
    )
    block_index = models.PositiveIntegerField(default=1)
    label = models.CharField(max_length=200, blank=True)
    title = models.CharField(max_length=200)
    layout_key = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)
    code = models.CharField(max_length=120, blank=True)
    default_views = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.project.title} – {self.title}"


class ProjectProductSpecField(TimeStampedModel):
    product_spec = models.ForeignKey(ProjectProductSpec, on_delete=models.CASCADE, related_name="fields")
    field_key = models.CharField(max_length=120)
    label = models.CharField(max_length=200)
    value = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.product_spec} • {self.label}"


# ---------------- Student Portfolio ----------------
class StudentPortfolioPlan(TimeStampedModel):
    """Pro plan for student portfolios — $19.99/mo with free templates and 2-year custom domain."""

    PLAN_KEY = "student_pro_monthly"
    PRICE = 19.99
    DOMAIN_FREE_YEARS = 2

    name = models.CharField(max_length=80, unique=True)
    display_name = models.CharField(max_length=120)
    price = models.DecimalField(max_digits=8, decimal_places=2, default=19.99)
    duration_days = models.IntegerField(default=30)
    includes_custom_domain = models.BooleanField(default=True)
    domain_free_years = models.PositiveIntegerField(default=2)
    stripe_price_id = models.CharField(max_length=200, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["price"]

    def __str__(self):
        return f"{self.display_name} — ${self.price}/mo"


class StudentPortfolioSubscription(TimeStampedModel):
    """Tracks Pro subscription for student portfolio (custom domain, templates)."""

    STATUS_CHOICES = [
        ("active", "Active"),
        ("canceled", "Canceled"),
        ("expired", "Expired"),
        ("past_due", "Past Due"),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="student_portfolio_subscription",
    )
    plan = models.ForeignKey(
        StudentPortfolioPlan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subscriptions",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    subscription_start = models.DateTimeField(null=True, blank=True)
    subscription_end = models.DateTimeField(null=True, blank=True)
    stripe_subscription_id = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        verbose_name = "Student Portfolio Subscription"

    def __str__(self):
        return f"{self.user.username} — {self.get_status_display()}"

    @property
    def is_active(self):
        from django.utils import timezone

        if self.status != "active":
            return False
        if self.subscription_end and self.subscription_end < timezone.now():
            return False
        return True


class StudentPortfolio(TimeStampedModel):
    class Visibility(models.TextChoices):
        PUBLIC = ("public", "Public (for recruiters)")
        PRIVATE = ("private", "Private (classroom review only)")

    class TemplateStyle(models.TextChoices):
        CLEAN = ("clean", "Clean")
        MODERN = ("modern", "Modern")
        MINIMAL = ("minimal", "Minimal")

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="student_portfolio")
    profile_photo = models.ImageField(upload_to="students/profiles/", blank=True, null=True)
    bio = models.TextField(blank=True, default="")
    skills = models.CharField(max_length=500, blank=True, help_text="Comma-separated skills")
    design_interests = models.CharField(max_length=500, blank=True, help_text="Comma-separated interests")
    template_style = models.CharField(
        max_length=20,
        choices=TemplateStyle.choices,
        default=TemplateStyle.MODERN,
    )
    visibility = models.CharField(
        max_length=20,
        choices=Visibility.choices,
        default=Visibility.PRIVATE,
        db_index=True,
    )
    share_slug = models.SlugField(max_length=180, unique=True, blank=True)
    custom_domain = models.CharField(
        max_length=253,
        blank=True,
        null=True,
        unique=True,
        help_text="Custom domain (e.g. chpreddy.com). Requires Student Portfolio Pro.",
    )
    domain_free_until = models.DateField(
        null=True,
        blank=True,
        help_text="Custom domain included free until this date (first 2 years for Pro).",
    )

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"Student portfolio for {self.user.username}"

    def save(self, *args, **kwargs):
        if not self.share_slug:
            base_slug = slugify(f"{self.user.username}-portfolio")
            slug = base_slug
            suffix = 1
            while StudentPortfolio.objects.filter(share_slug=slug).exclude(pk=self.pk).exists():
                suffix += 1
                slug = f"{base_slug}-{suffix}"
            self.share_slug = slug
        if self.custom_domain:
            domain = (self.custom_domain or "").strip().lower()
            if domain.startswith("www."):
                domain = domain[4:]
            self.custom_domain = domain or None
        super().save(*args, **kwargs)

    @property
    def skills_list(self) -> list[str]:
        return [item.strip() for item in self.skills.split(",") if item.strip()]

    @property
    def interests_list(self) -> list[str]:
        return [item.strip() for item in self.design_interests.split(",") if item.strip()]


class StudentPortfolioProject(TimeStampedModel):
    class Category(models.TextChoices):
        FASHION_DESIGN = ("fashion-design", "Fashion Design")
        EDITORIAL = ("editorial", "Editorial & Lookbook")
        COLLECTION = ("collection", "Collection")
        UI_UX = ("ui-ux", "UI/UX")
        GRAPHIC_DESIGN = ("graphic-design", "Graphic Design")
        ANIMATION = ("animation", "Animation")
        PRODUCT_DESIGN = ("product-design", "Product Design")
        BRANDING = ("branding", "Branding")
        ILLUSTRATION = ("illustration", "Illustration")
        OTHER = ("other", "Other")

    portfolio = models.ForeignKey(
        StudentPortfolio,
        on_delete=models.CASCADE,
        related_name="projects",
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=40, choices=Category.choices, default=Category.UI_UX, db_index=True)
    tools_used = models.CharField(max_length=255, blank=True, help_text="Comma-separated tools")
    project_role = models.CharField(max_length=120, blank=True)
    process_steps = models.TextField(
        blank=True,
        help_text="One process step per line, for example: Sketch -> Wireframe -> Final design",
    )
    cover_image = models.ImageField(upload_to="students/projects/images/", blank=True, null=True)
    process_video = models.FileField(upload_to="students/projects/videos/", blank=True, null=True)
    project_pdf = models.FileField(upload_to="students/projects/pdfs/", blank=True, null=True)
    featured = models.BooleanField(default=False, db_index=True)
    display_order = models.PositiveIntegerField(default=0, db_index=True)

    class Meta:
        ordering = ["display_order", "-created_at", "id"]


    def __str__(self):
        return f"{self.title} ({self.portfolio.user.username})"

    @property
    def tools_list(self) -> list[str]:
        return [item.strip() for item in self.tools_used.split(",") if item.strip()]

    @property
    def process_steps_list(self) -> list[str]:
        return [item.strip() for item in (self.process_steps or "").splitlines() if item.strip()]


class StudentPortfolioProjectImage(TimeStampedModel):
    """Gallery image for a project — designs, editorials, collection photos."""
    project = models.ForeignKey(
        StudentPortfolioProject,
        on_delete=models.CASCADE,
        related_name="gallery_images",
    )
    image = models.ImageField(upload_to="students/projects/gallery/")
    caption = models.CharField(max_length=255, blank=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "-created_at", "id"]

    def __str__(self):
        return f"Image for {self.project.title}"


class StudentProjectFeedback(TimeStampedModel):
    class ReviewerRole(models.TextChoices):
        TEACHER = ("teacher", "Teacher")
        PEER = ("peer", "Peer")

    project = models.ForeignKey(
        StudentPortfolioProject,
        on_delete=models.CASCADE,
        related_name="feedback_entries",
    )
    author = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="student_project_feedback",
    )
    reviewer_role = models.CharField(max_length=20, choices=ReviewerRole.choices, default=ReviewerRole.PEER)
    comment = models.TextField()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        reviewer = self.author.username if self.author else "Anonymous"
        return f"{reviewer} feedback on {self.project.title}"


class StudentProjectLike(TimeStampedModel):
    project = models.ForeignKey(
        StudentPortfolioProject,
        on_delete=models.CASCADE,
        related_name="likes",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="student_project_likes",
    )

    class Meta:
        unique_together = [("project", "user")]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} liked {self.project.title}"


class StudentProjectBookmark(TimeStampedModel):
    project = models.ForeignKey(
        StudentPortfolioProject,
        on_delete=models.CASCADE,
        related_name="bookmarks",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="student_project_bookmarks",
    )

    class Meta:
        unique_together = [("project", "user")]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} bookmarked {self.project.title}"


class DressOrder(TimeStampedModel):
    """Dress order from the new orders page — sent to a designer with email notification."""

    STATUS_CHOICES = [
        ("new", "New"),
        ("in_progress", "In progress"),
        ("completed", "Completed"),
        ("canceled", "Canceled"),
    ]

    designer = models.ForeignKey(
        DesignerProfile,
        on_delete=models.CASCADE,
        related_name="dress_orders",
    )
    # Orderer contact (from gate)
    customer_phone = models.CharField(max_length=20, blank=True)
    customer_email = models.EmailField(blank=True, help_text="Viewer email for order confirmation and design access")

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="new")

    # Optional link to design (when designer attaches a design to this order)
    design = models.ForeignKey(
        Design,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dress_orders",
        help_text="Design linked to this order; only designer and order viewer can see it",
    )

    # Token for viewer to access order and linked design without logging in
    access_token = models.CharField(max_length=64, blank=True, unique=True, db_index=True)

    # Dress type
    dress_type = models.CharField(max_length=40, blank=True)
    dress_label = models.CharField(max_length=100, blank=True)
    formal_subcategory = models.CharField(max_length=60, blank=True, help_text="Sub-category when Formal: suits, shirts, coats, jackets, etc.")

    # Measurements (cm)
    shoulder_width = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    chest = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    sleeve_short = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    sleeve_wrist = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    # Fabric
    fabric_type = models.CharField(max_length=40, blank=True)
    fabric_label = models.CharField(max_length=100, blank=True)
    wool_type = models.CharField(max_length=40, blank=True)
    fabric_texture = models.CharField(max_length=60, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Dress order for {self.designer.user.get_username()} — {self.dress_label or 'Dress'} ({self.created_at.date()})"

    def save(self, *args, **kwargs):
        if not self.access_token:
            import secrets
            self.access_token = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)


class DressOrderUpdate(TimeStampedModel):
    """Designer update on a dress order: status change, notes, techpack info."""

    order = models.ForeignKey(
        DressOrder,
        on_delete=models.CASCADE,
        related_name="updates",
    )
    status = models.CharField(
        max_length=20,
        choices=DressOrder.STATUS_CHOICES,
        blank=True,
        help_text="Status at time of this update (optional)",
    )
    notes = models.TextField(blank=True, help_text="Designer notes (e.g. taking order, working on it)")
    techpack_notes = models.TextField(blank=True, help_text="Techpack information about the order")
    techpack_pdf = models.FileField(
        upload_to="orders/techpacks/",
        blank=True,
        null=True,
        help_text="Techpack PDF for this order",
    )

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Update on order #{self.order_id} — {self.created_at.date()}"
