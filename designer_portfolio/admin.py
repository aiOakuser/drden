from django.contrib import admin
from django.utils.html import format_html
from . import models as m


# ---------------- Brand ----------------
@admin.register(m.Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("name", "tagline", "primary_color", "updated_at")
    search_fields = ("name", "tagline")


# ---------------- Techpack (inline for Design) ----------------
class TechpackInline(admin.StackedInline):
    model = m.Techpack
    extra = 0
    min_num = 1
    max_num = 1  # Only one techpack per design


# ---------------- Design Images ----------------
class DesignImageInline(admin.TabularInline):
    model = m.DesignImage
    extra = 1
    fields = ("preview", "image", "caption", "order")
    readonly_fields = ("preview",)

    def preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width:80px; height:80px; object-fit:cover; border-radius:6px;" />',
                obj.image.url,
            )
        return "-"
    preview.short_description = "Preview"


# ---------------- Design ----------------
@admin.register(m.Design)
class DesignAdmin(admin.ModelAdmin):
    list_display = ("title", "year", "season", "published", "cover_preview", "created_at")
    list_filter = ("published", "year", "season")
    search_fields = ("title", "description", "season")
    prepopulated_fields = {"slug": ("title", "year")}
    inlines = [TechpackInline, DesignImageInline]

    def cover_preview(self, obj):
        if obj.cover_image:
            return format_html(
                '<img src="{}" style="width:80px; height:80px; object-fit:cover; border-radius:6px;" />',
                obj.cover_image.url,
            )
        return "-"
    cover_preview.short_description = "Cover"


# ---------------- Event Images ----------------
class EventImageInline(admin.TabularInline):
    model = m.EventImage
    extra = 1
    fields = ("preview", "image", "caption", "order")
    readonly_fields = ("preview",)

    def preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width:80px; height:80px; object-fit:cover; border-radius:6px;" />',
                obj.image.url,
            )
        return "-"
    preview.short_description = "Preview"


# ---------------- Event ----------------
@admin.register(m.Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "event_date", "is_popup", "popup_order", "cover_preview", "created_at")
    list_filter = ("is_popup", "event_date")
    search_fields = ("title", "description")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [EventImageInline]

    def cover_preview(self, obj):
        if obj.cover:
            return format_html(
                '<img src="{}" style="width:80px; height:80px; object-fit:cover; border-radius:6px;" />',
                obj.cover.url,
            )
        return "-"
    cover_preview.short_description = "Cover"


# ---------------- Designer Profile ----------------
@admin.register(m.DesignerProfile)
class DesignerProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "specialization",
        "location",
        "portfolio_template",
        "created_at",
    )
    list_filter = ("portfolio_template", "available_for_collaborations")
    search_fields = (
        "user__username",
        "user__email",
        "specialization",
        "location",
    )
    readonly_fields = ("created_at", "updated_at")
    fields = (
        "user",
        "bio",
        "profile_image",
        "portfolio_website",
        "instagram_handle",
        "linkedin_profile",
        "years_of_experience",
        "specialization",
        "education",
        "location",
        "available_for_collaborations",
        "contact_email",
        "portfolio_template",
        "created_at",
        "updated_at",
    )


# ---------------- Designer AI ----------------
@admin.register(m.DesignerAISession)
class DesignerAISessionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "language", "created_at", "message_count")
    list_filter = ("language", "created_at")
    search_fields = ("id", "user__username", "session_id")
    readonly_fields = ("created_at", "updated_at")
    
    def message_count(self, obj):
        return obj.messages.count()
    message_count.short_description = "Messages"


@admin.register(m.DesignerAIMessage)
class DesignerAIMessageAdmin(admin.ModelAdmin):
    list_display = ("session", "role", "short_content", "created_at")
    list_filter = ("role", "created_at")
    search_fields = ("content", "session__user__username")
    readonly_fields = ("created_at", "updated_at")
    
    def short_content(self, obj):
        return obj.content[:100] + "..." if len(obj.content) > 100 else obj.content
    short_content.short_description = "Content"


@admin.register(m.DocPage)
class DocPageAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "category", "language", "published", "order")
    list_filter = ("language", "category", "published")
    search_fields = ("title", "content", "slug", "tags")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("created_at", "updated_at")
