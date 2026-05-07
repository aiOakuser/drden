import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone


def _generate_event_token() -> str:
    """URL-safe random token used to acknowledge / cancel a registration."""
    return secrets.token_urlsafe(24)


class SocialContentBundle(models.Model):
    """
    Latest regenerated social copy from site context + OpenAI.
    Staff review before posting; nothing is auto-published to networks here.
    """

    class Kind(models.TextChoices):
        HUB_SOCIAL = "hub_social", "Hub (IG / LinkedIn / X)"
        INSTAGRAM_APP = "instagram_app", "Instagram — designer iPhone app"

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    bundle_kind = models.CharField(
        max_length=32,
        choices=Kind.choices,
        default=Kind.HUB_SOCIAL,
        db_index=True,
    )
    source_context = models.TextField(
        blank=True,
        help_text="Plain-text snapshot fed to the model (site digest or iOS app facts).",
    )
    platforms = models.JSONField(
        default=dict,
        help_text="hub_social: instagram_caption, instagram_hashtags, linkedin_post, x_post, … "
        "instagram_app: caption, hashtags, carousel_slides, stories_bullets, ai_designer_image_prompt, …",
    )
    model_used = models.CharField(max_length=80, blank=True)
    success = models.BooleanField(default=True)
    error = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Social content bundle"
        verbose_name_plural = "Social content bundles"

    def __str__(self) -> str:
        status = "ok" if self.success else "error"
        return f"SocialContentBundle {self.bundle_kind} {self.created_at.isoformat()} ({status})"


class FashionConsultLead(models.Model):
    full_name = models.CharField(max_length=150)
    phone_number = models.CharField(max_length=20)
    country_code = models.CharField(max_length=5, default="+1")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.full_name} ({self.country_code}{self.phone_number})"


class Event(models.Model):
    """
    A unified container for the event-driven community surfaces:

    - Expert-led webinars
    - Workshops
    - Virtual meetups
    - Design jams

    All four share the same lifecycle (announce → register → run → recap),
    so a single model keeps the public listing simple and the staff CMS
    cheap. Sending reminder emails / running the live stream is left to
    downstream tooling — this model is the editorial source of truth.
    """

    class Kind(models.TextChoices):
        WEBINAR = "webinar", "Webinar"
        WORKSHOP = "workshop", "Workshop"
        MEETUP = "meetup", "Virtual meetup"
        DESIGN_JAM = "design_jam", "Design jam"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SCHEDULED = "scheduled", "Scheduled"
        LIVE = "live", "Live now"
        ENDED = "ended", "Ended"
        CANCELLED = "cancelled", "Cancelled"

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    kind = models.CharField(
        max_length=16,
        choices=Kind.choices,
        default=Kind.WEBINAR,
        db_index=True,
    )
    summary = models.CharField(
        max_length=240,
        blank=True,
        help_text="One-line elevator description shown on the events list.",
    )
    description_html = models.TextField(
        blank=True,
        help_text="Long-form description shown on the event detail page (HTML allowed).",
    )
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True, blank=True)
    timezone_label = models.CharField(
        max_length=64,
        blank=True,
        help_text="Display label, e.g. 'New York · EST'. Free text — no tz conversion.",
    )
    is_virtual = models.BooleanField(default=True)
    location = models.CharField(
        max_length=200,
        blank=True,
        help_text="Venue or platform (e.g. 'Zoom', 'Discord stage', 'NYC studio').",
    )
    join_url = models.URLField(
        blank=True,
        help_text="Public join URL surfaced on the detail page once status is LIVE.",
    )
    host_name = models.CharField(max_length=150, blank=True)
    host_bio = models.TextField(blank=True)
    capacity = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Optional cap. Registration is closed once this is hit.",
    )
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-starts_at"]
        verbose_name = "Event"
        verbose_name_plural = "Events"

    def __str__(self) -> str:
        return f"{self.get_kind_display()}: {self.title}"

    @property
    def is_public(self) -> bool:
        """Whether this event should appear on the public events list."""
        return self.status in {self.Status.SCHEDULED, self.Status.LIVE, self.Status.ENDED}

    @property
    def is_upcoming(self) -> bool:
        return (
            self.status in {self.Status.SCHEDULED, self.Status.LIVE}
            and self.starts_at >= timezone.now()
        )

    @property
    def is_full(self) -> bool:
        if self.capacity is None:
            return False
        return self.registrations.count() >= self.capacity

    @property
    def registrations_open(self) -> bool:
        return (
            self.status in {self.Status.SCHEDULED, self.Status.LIVE}
            and not self.is_full
        )


class EventRegistration(models.Model):
    """
    A single RSVP. `email + event` is unique so re-submitting the form with
    the same email idempotently updates the existing row instead of
    creating duplicates.
    """

    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name="registrations"
    )
    email = models.EmailField()
    full_name = models.CharField(max_length=150, blank=True)
    notes = models.TextField(
        blank=True,
        help_text="Optional context the attendee wants the host to know.",
    )
    cancel_token = models.CharField(
        max_length=64,
        unique=True,
        default=_generate_event_token,
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)
    attended_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = [("event", "email")]
        verbose_name = "Event registration"
        verbose_name_plural = "Event registrations"

    def __str__(self) -> str:
        state = "cancelled" if self.cancelled_at else "active"
        return f"{self.email} -> {self.event_id} ({state})"


class EmergingTalentFeature(models.Model):
    """
    A curated 'Emerging Talent' editorial slot. Each row features one
    designer's work and (optionally) the success story of how they got
    noticed by global brands.

    `designer_user` is a soft FK so a feature stays renderable if the
    user later deletes their account; we still have `display_name`,
    `bio_html`, and the success-story fields baked into the row.
    """

    title = models.CharField(
        max_length=200,
        help_text="Headline shown on the feature card, e.g. 'Capsule by Maya R.'",
    )
    slug = models.SlugField(max_length=220, unique=True)
    display_name = models.CharField(
        max_length=150,
        help_text="Designer name as it should appear publicly.",
    )
    designer_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="emerging_talent_features",
        help_text="Optional link to the designer's GDH account.",
    )
    designer_portfolio_url = models.URLField(
        blank=True,
        help_text="Public portfolio URL the feature card links to.",
    )
    hero_image_url = models.URLField(
        blank=True,
        help_text="Optional hero image (absolute URL).",
    )
    bio_html = models.TextField(
        blank=True,
        help_text="Short bio shown on the detail page (HTML allowed).",
    )
    success_story_html = models.TextField(
        blank=True,
        help_text=(
            "How they got noticed: brand they're now working with, contest "
            "win, capsule launch, etc. (HTML allowed)."
        ),
    )
    ordering = models.IntegerField(
        default=0,
        help_text="Lower numbers surface first on the list page.",
    )
    is_published = models.BooleanField(default=False, db_index=True)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["ordering", "-published_at", "-created_at"]
        verbose_name = "Emerging talent feature"
        verbose_name_plural = "Emerging talent features"

    def __str__(self) -> str:
        return f"{self.display_name} — {self.title}"

    def mark_published(self) -> None:
        if not self.is_published:
            self.is_published = True
            self.published_at = self.published_at or timezone.now()
            self.save(update_fields=["is_published", "published_at", "updated_at"])


class BrandPartnershipLead(models.Model):
    """
    Inbound interest from brands that want to partner on design
    competitions, capsule collaborations, mentorship sponsorships, or
    scholarships. Distinct from SchoolPartnerLead and InfluencerCollabLead
    so growth can route them to a different sales motion.
    """

    class PartnershipKind(models.TextChoices):
        COMPETITION = "competition", "Design competition"
        COLLABORATION = "collab", "Capsule / collaboration"
        SCHOLARSHIP = "scholarship", "Scholarship / grant"
        MENTORSHIP = "mentorship", "Mentorship sponsorship"
        OTHER = "other", "Something else"

    brand_name = models.CharField(max_length=200)
    contact_name = models.CharField(max_length=150)
    email = models.EmailField()
    role = models.CharField(
        max_length=120,
        blank=True,
        help_text="Your role at the brand (e.g. Marketing Lead).",
    )
    website = models.URLField(blank=True)
    partnership_kind = models.CharField(
        max_length=20,
        choices=PartnershipKind.choices,
        default=PartnershipKind.COMPETITION,
    )
    audience_reach = models.CharField(
        max_length=120,
        blank=True,
        help_text="Audience you'd activate (e.g. '420K IG, 90K newsletter').",
    )
    message = models.TextField(
        blank=True,
        help_text="Brief on what you'd like to run with us.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Brand partnership lead"
        verbose_name_plural = "Brand partnership leads"

    def __str__(self) -> str:
        return f"{self.brand_name} — {self.get_partnership_kind_display()}"


class MentorshipApplication(models.Model):
    """
    Single applications table for both sides of the mentorship program —
    pros applying to mentor, and students/junior designers applying to be
    matched. Storing both in one table lets staff see supply and demand on
    a single page and run matching queries without two parallel models.
    """

    class Role(models.TextChoices):
        MENTOR = "mentor", "Industry mentor"
        MENTEE = "mentee", "Student / mentee"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending review"
        ACTIVE = "active", "Approved · waiting to match"
        MATCHED = "matched", "Matched"
        DECLINED = "declined", "Declined"
        WITHDRAWN = "withdrawn", "Withdrew"

    role = models.CharField(
        max_length=10, choices=Role.choices, db_index=True
    )
    full_name = models.CharField(max_length=150)
    email = models.EmailField()
    headline = models.CharField(
        max_length=160,
        blank=True,
        help_text=(
            "Mentors: current job title + company. "
            "Mentees: school + year, or self-taught focus."
        ),
    )
    focus_areas = models.CharField(
        max_length=240,
        blank=True,
        help_text="Comma-separated focus areas (e.g. 'tech packs, womenswear, denim').",
    )
    portfolio_url = models.URLField(blank=True)
    availability = models.CharField(
        max_length=160,
        blank=True,
        help_text="Hours per month / time-zone (e.g. '2 hrs/mo · PT').",
    )
    message = models.TextField(
        blank=True,
        help_text=(
            "Mentors: why you want to mentor. Mentees: what kind of guidance "
            "you're looking for."
        ),
    )
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mentorship_applications",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Mentorship application"
        verbose_name_plural = "Mentorship applications"

    def __str__(self) -> str:
        return f"{self.get_role_display()}: {self.full_name} <{self.email}>"


class ForumInterestSignup(models.Model):
    """
    Email capture for the (not-yet-built) community forums. Lets us gauge
    demand and preview a launch without committing to threaded-forum
    infrastructure today.
    """

    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=150, blank=True)
    notes = models.CharField(
        max_length=240,
        blank=True,
        help_text="Optional: what they want forums to be (rooms, topics, etc.).",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Forum interest signup"
        verbose_name_plural = "Forum interest signups"

    def __str__(self) -> str:
        return self.email
