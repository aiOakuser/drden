"""Site Builder models — drag-and-drop pages, CMS, SEO, AI-generated layouts."""
from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify


class BuilderSite(models.Model):
    """A builder site (portfolio, landing page) owned by a designer or student."""
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="builder_sites",
    )
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    published = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.name} ({self.owner.username})"

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name or "site")[:100]
            slug = base
            n = 1
            while BuilderSite.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"[:180]
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)


class BuilderPage(models.Model):
    """A page in a builder site — stores blocks as JSON."""
    site = models.ForeignKey(
        BuilderSite,
        on_delete=models.CASCADE,
        related_name="pages",
    )
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, blank=True)
    is_home = models.BooleanField(default=False)

    # SEO
    meta_title = models.CharField(max_length=70, blank=True)
    meta_description = models.CharField(max_length=160, blank=True)
    meta_image = models.ImageField(upload_to="builder/meta/", blank=True, null=True)

    # Content — GrapesJS HTML + CSS + block config
    html_content = models.TextField(blank=True)
    css_content = models.TextField(blank=True)
    block_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Block structure for CMS; GrapesJS components JSON",
    )

    # Animations — per-block or global
    animation_config = models.JSONField(
        default=dict,
        blank=True,
        help_text='e.g. {"type":"fade-up","delay":100}',
    )
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "-is_home", "title"]
        unique_together = [("site", "slug")]

    def __str__(self):
        return f"{self.title} ({self.site.name})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = "index" if self.is_home else slugify(self.title or "page")[:200]
        super().save(*args, **kwargs)


class BuilderCollection(models.Model):
    """CMS collection for repeatable content (blog posts, projects, etc.)."""
    site = models.ForeignKey(
        BuilderSite,
        on_delete=models.CASCADE,
        related_name="collections",
    )
    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=100)
    schema = models.JSONField(
        default=dict,
        help_text="Field definitions for items",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("site", "slug")]

    def __str__(self):
        return f"{self.name} ({self.site.name})"


class BuilderCollectionItem(models.Model):
    """A single item in a CMS collection."""
    collection = models.ForeignKey(
        BuilderCollection,
        on_delete=models.CASCADE,
        related_name="items",
    )
    data = models.JSONField(default=dict)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "-created_at"]
