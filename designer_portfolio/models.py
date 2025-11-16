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
    primary_color = models.CharField(max_length=7, default="#000000")  # black
    secondary_color = models.CharField(max_length=7, default="#FFFFFF")  # white
    accent_color = models.CharField(max_length=7, default="#9CA3AF")  # neutral gray
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
