from django.db import models


class SocialContentBundle(models.Model):
    """
    Latest regenerated social copy (Instagram, LinkedIn, X) from site context + OpenAI.
    Staff review before posting; nothing is auto-published to networks here.
    """

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    source_context = models.TextField(
        blank=True,
        help_text="Plain-text snapshot fed to the model (collections, designers, events).",
    )
    platforms = models.JSONField(
        default=dict,
        help_text="Keys: instagram_caption, instagram_hashtags, linkedin_post, x_post, suggested_cta, notes_for_designer",
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
        return f"SocialContentBundle {self.created_at.isoformat()} ({status})"


class FashionConsultLead(models.Model):
    full_name = models.CharField(max_length=150)
    phone_number = models.CharField(max_length=20)
    country_code = models.CharField(max_length=5, default="+1")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.full_name} ({self.country_code}{self.phone_number})"
