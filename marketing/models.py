from django.db import models


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
