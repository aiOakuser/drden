from django.db import models
from django.utils.text import slugify
from django.contrib.auth.models import User


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
    portfolio_website = models.URLField(blank=True, help_text="Your personal website or portfolio")
    instagram_handle = models.CharField(max_length=100, blank=True, help_text="Instagram username (without @)")
    linkedin_profile = models.URLField(blank=True, help_text="LinkedIn profile URL")
    
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
    acquisition_landing_page = models.URLField(blank=True, null=True)
    acquisition_initial_referrer = models.URLField(blank=True, null=True)
    
    # Adobe package inclusion
    includes_adobe_access = models.BooleanField(default=True, help_text="Whether this subscription includes Adobe Creative Suite access")
    
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


# ---------------- Adobe Package Models ----------------
class AdobeProduct(models.Model):
    """Individual Adobe products available for packages"""
    name = models.CharField(max_length=100, unique=True)
    display_name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    product_icon = models.CharField(max_length=50, blank=True)  # For emoji/icon display
    adobe_product_id = models.CharField(max_length=100, blank=True)  # Adobe's internal ID
    is_popular = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order', 'display_name']
    
    def __str__(self):
        return self.display_name


class AdobePackage(models.Model):
    """Adobe product packages with different product counts and pricing"""
    PACKAGE_TYPES = [
        ('single', 'Single Product'),
        ('duo', '2 Products'),
        ('trio', '3 Products'),
        ('quad', '4 Products'),
        ('penta', '5 Products'),
        ('hexa', '6 Products'),
        ('full', 'Full Creative Suite'),
    ]
    
    package_type = models.CharField(max_length=20, choices=PACKAGE_TYPES, unique=True)
    display_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    product_count = models.PositiveIntegerField()
    monthly_price = models.DecimalField(max_digits=6, decimal_places=2)
    suggested_products = models.ManyToManyField(AdobeProduct, blank=True, help_text="Recommended products for this package")
    is_popular = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order', 'product_count']
    
    def __str__(self):
        return f"{self.display_name} - ${self.monthly_price}/month"


class UserAdobeSubscription(models.Model):
    """User's Adobe subscription and product selection"""
    STATUS_CHOICES = [
        ('pending', 'Pending Setup'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='adobe_subscription')
    package = models.ForeignKey(AdobePackage, on_delete=models.CASCADE)
    selected_products = models.ManyToManyField(AdobeProduct, help_text="Products selected by user")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Adobe account details
    adobe_account_email = models.EmailField(blank=True, null=True)
    adobe_account_status = models.CharField(max_length=50, blank=True, null=True)
    adobe_subscription_id = models.CharField(max_length=200, blank=True, null=True)
    
    # Billing information
    monthly_cost = models.DecimalField(max_digits=6, decimal_places=2)
    next_billing_date = models.DateTimeField(null=True, blank=True)
    last_payment_date = models.DateTimeField(null=True, blank=True)
    auto_renewal = models.BooleanField(default=True)
    
    # Subscription lifecycle
    subscription_start_date = models.DateTimeField(null=True, blank=True)
    subscription_end_date = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Adobe Subscription"
        verbose_name_plural = "Adobe Subscriptions"
    
    def __str__(self):
        return f"{self.user.username} - {self.package.display_name} ({self.status})"
    
    def get_product_names(self):
        """Return comma-separated list of selected product names"""
        return ", ".join([product.display_name for product in self.selected_products.all()])


class AdobeAccessLog(models.Model):
    """Log Adobe account access and usage"""
    user_subscription = models.ForeignKey(UserAdobeSubscription, on_delete=models.CASCADE, related_name='access_logs')
    product_accessed = models.ForeignKey(AdobeProduct, on_delete=models.CASCADE, null=True, blank=True)
    access_type = models.CharField(max_length=50, choices=[
        ('login', 'Account Login'),
        ('download', 'Product Download'),
        ('usage', 'Product Usage'),
        ('support', 'Support Access'),
    ], default='login')
    access_timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-access_timestamp']
        verbose_name = "Adobe Access Log"
        verbose_name_plural = "Adobe Access Logs"
    
    def __str__(self):
        return f"{self.user_subscription.user.username} - {self.access_type} - {self.access_timestamp.strftime('%Y-%m-%d %H:%M')}"


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
