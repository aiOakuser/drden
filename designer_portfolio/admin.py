from django.contrib import admin
from django.utils.html import format_html
from . import models as m


# ---------------- Brand ----------------
@admin.register(m.Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("name", "tagline", "primary_color", "updated_at")
    search_fields = ("name", "tagline")


# ---------------- Template Library ----------------
class TemplateStageInline(admin.TabularInline):
    model = m.TemplateStage
    extra = 0
    fields = ("stage_index", "title", "layout_hint")


class TemplateProductBlockInline(admin.TabularInline):
    model = m.TemplateProductBlock
    extra = 0
    fields = ("block_index", "label", "title_placeholder")


@admin.register(m.Template)
class TemplateAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "layout_key", "updated_at")
    search_fields = ("id", "name")
    list_filter = ("layout_key",)
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "id",
                    "name",
                    "layout_key",
                    "cover_title_placeholder",
                    "cover_subtitle_placeholder",
                    "summary",
                    "metadata",
                )
            },
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )
    inlines = [TemplateStageInline, TemplateProductBlockInline]


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


# ---------------- Project Breakdown ----------------
class ProjectStageInline(admin.TabularInline):
    model = m.ProjectStage
    extra = 0
    fields = ("stage_number", "title", "order", "template_stage")
    show_change_link = True


class ProjectProductSpecInline(admin.TabularInline):
    model = m.ProjectProductSpec
    extra = 0
    fields = ("block_index", "label", "title", "code", "layout_key")
    show_change_link = True


@admin.register(m.Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "template_name", "product_type", "product_count", "owner", "created_at")
    list_filter = ("template_name", "product_type", "season", "created_at")
    search_fields = ("title", "template_name", "client_name", "owner__username")
    readonly_fields = ("created_at", "updated_at", "template_snapshot")
    fieldsets = (
        (
            "Project Info",
            {
                "fields": (
                    "owner",
                    "title",
                    "subtitle",
                    "client_name",
                    "season",
                    "product_type",
                    "product_count",
                )
            },
        ),
        (
            "Template",
            {
                "fields": (
                    "template_id",
                    "template_name",
                    "template_category",
                    "template_layout_key",
                    "preview_copy",
                    "template_snapshot",
                )
            },
        ),
        (
            "Metadata",
            {
                "fields": ("metadata", "created_at", "updated_at"),
            },
        ),
    )
    inlines = [ProjectStageInline, ProjectProductSpecInline]


class ProjectStageBulletInline(admin.TabularInline):
    model = m.ProjectStageBullet
    extra = 0
    fields = ("order", "text")


@admin.register(m.ProjectStage)
class ProjectStageAdmin(admin.ModelAdmin):
    list_display = ("project", "stage_number", "title", "order", "template_stage")
    list_filter = ("project__template_name", "template_stage__template__name")
    search_fields = ("title", "project__title", "template_stage__title")
    inlines = [ProjectStageBulletInline]


class ProjectProductSpecFieldInline(admin.TabularInline):
    model = m.ProjectProductSpecField
    extra = 0
    fields = ("order", "field_key", "label", "value")


@admin.register(m.ProjectProductSpec)
class ProjectProductSpecAdmin(admin.ModelAdmin):
    list_display = ("project", "label", "title", "code", "layout_key")
    search_fields = ("title", "project__title", "label", "code")
    inlines = [ProjectProductSpecFieldInline]


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
        "structured_location",
        "portfolio_template",
        "created_at",
    )
    list_filter = (
        "portfolio_template",
        "available_for_collaborations",
        "region_area",
        "country",
        "state_province",
    )
    search_fields = (
        "user__username",
        "user__email",
        "specialization",
        "location",
        "region_area",
        "country",
        "state_province",
        "city",
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
        "region_area",
        "country",
        "state_province",
        "county",
        "city",
        "location",
        "available_for_collaborations",
        "contact_email",
        "portfolio_template",
        "created_at",
        "updated_at",
    )

    @admin.display(description="Location", ordering="city")
    def structured_location(self, obj):
        return obj.location_display or "—"


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


@admin.register(m.ProblemReport)
class ProblemReportAdmin(admin.ModelAdmin):
    list_display = (
        "subject",
        "category",
        "status",
        "email",
        "created_at",
    )
    list_filter = ("category", "status", "created_at")
    search_fields = ("subject", "message", "email", "name", "page_url")
    readonly_fields = (
        "created_at",
        "updated_at",
        "ip_address",
        "user_agent",
        "reporter",
    )
    fieldsets = (
        (
            "Report Details",
            {
                "fields": (
                    "subject",
                    "category",
                    "status",
                    "message",
                    "page_url",
                )
            },
        ),
        (
            "Reporter",
            {
                "fields": (
                    "name",
                    "email",
                    "reporter",
                )
            },
        ),
        (
            "Diagnostics",
            {
                "fields": (
                    "ip_address",
                    "user_agent",
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(m.DocPage)
class DocPageAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "category", "language", "published", "order")
    list_filter = ("language", "category", "published")
    search_fields = ("title", "content", "slug", "tags")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("created_at", "updated_at")


# ---------------- Adobe Package Admin ----------------
@admin.register(m.AdobeProduct)
class AdobeProductAdmin(admin.ModelAdmin):
    list_display = ("display_name", "name", "product_icon", "is_popular", "is_active", "order")
    list_filter = ("is_popular", "is_active")
    search_fields = ("name", "display_name", "description")
    ordering = ("order", "display_name")
    list_editable = ("order", "is_popular", "is_active")


@admin.register(m.AdobePackage)
class AdobePackageAdmin(admin.ModelAdmin):
    list_display = ("display_name", "package_type", "product_count", "monthly_price", "is_popular", "is_active")
    list_filter = ("package_type", "is_popular", "is_active")
    search_fields = ("display_name", "description")
    ordering = ("order", "product_count")
    list_editable = ("monthly_price", "is_popular", "is_active")
    filter_horizontal = ("suggested_products",)


@admin.register(m.UserAdobeSubscription)
class UserAdobeSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "package", "status", "monthly_cost", "subscription_start_date", "next_billing_date")
    list_filter = ("status", "package", "auto_renewal")
    search_fields = ("user__username", "user__email", "adobe_account_email")
    ordering = ("-created_at",)
    filter_horizontal = ("selected_products",)
    readonly_fields = ("created_at", "updated_at")
    
    fieldsets = (
        ("User & Package", {
            "fields": ("user", "package", "selected_products", "status")
        }),
        ("Adobe Account", {
            "fields": ("adobe_account_email", "adobe_account_status", "adobe_subscription_id")
        }),
        ("Billing Information", {
            "fields": ("monthly_cost", "next_billing_date", "last_payment_date", "auto_renewal")
        }),
        ("Subscription Lifecycle", {
            "fields": ("subscription_start_date", "subscription_end_date")
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        })
    )


@admin.register(m.AdobeAccessLog)
class AdobeAccessLogAdmin(admin.ModelAdmin):
    list_display = ("user_subscription", "product_accessed", "access_type", "access_timestamp", "ip_address")
    list_filter = ("access_type", "access_timestamp")
    search_fields = ("user_subscription__user__username", "ip_address")
    ordering = ("-access_timestamp",)
    readonly_fields = ("access_timestamp",)


# ---------------- Forum Admin ----------------
@admin.register(m.ForumCategory)
class ForumCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "get_topic_count", "get_post_count", "order", "is_active")
    list_editable = ("order", "is_active")
    list_filter = ("is_active", "created_at")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ("moderators",)
    
    def get_topic_count(self, obj):
        return obj.get_topic_count()
    get_topic_count.short_description = "Topics"
    
    def get_post_count(self, obj):
        return obj.get_post_count()
    get_post_count.short_description = "Posts"


class ForumPostInline(admin.TabularInline):
    model = m.ForumPost
    extra = 0
    fields = ("author", "content", "is_solution", "is_flagged", "created_at")
    readonly_fields = ("created_at",)


@admin.register(m.ForumTopic)
class ForumTopicAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "author", "get_post_count", "is_pinned", "is_locked", "is_featured", "view_count", "last_activity")
    list_editable = ("is_pinned", "is_locked", "is_featured")
    list_filter = ("category", "is_pinned", "is_locked", "is_featured", "is_active", "created_at")
    search_fields = ("title", "content", "tags")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [ForumPostInline]
    
    fieldsets = (
        ("Topic Information", {
            "fields": ("title", "slug", "content", "category", "author", "tags")
        }),
        ("Topic Status", {
            "fields": ("is_active", "is_pinned", "is_locked", "is_featured")
        }),
        ("Statistics", {
            "fields": ("view_count", "last_activity", "last_post"),
            "classes": ("collapse",)
        })
    )
    
    def get_post_count(self, obj):
        return obj.get_post_count()
    get_post_count.short_description = "Posts"


@admin.register(m.ForumPost)
class ForumPostAdmin(admin.ModelAdmin):
    list_display = ("topic", "author", "get_content_preview", "is_solution", "is_flagged", "get_reply_count", "created_at")
    list_filter = ("is_solution", "is_flagged", "is_active", "created_at")
    search_fields = ("content", "topic__title", "author__username")
    raw_id_fields = ("topic", "author", "parent")
    
    fieldsets = (
        ("Post Information", {
            "fields": ("topic", "author", "content", "parent")
        }),
        ("Post Status", {
            "fields": ("is_active", "is_solution", "is_flagged", "moderation_notes")
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at", "edited_at"),
            "classes": ("collapse",)
        })
    )
    
    readonly_fields = ("created_at", "updated_at")
    
    def get_content_preview(self, obj):
        return obj.content[:100] + "..." if len(obj.content) > 100 else obj.content
    get_content_preview.short_description = "Content Preview"
    
    def get_reply_count(self, obj):
        return obj.get_reply_count()
    get_reply_count.short_description = "Replies"


@admin.register(m.ForumUserProfile)
class ForumUserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "get_user_level", "post_count", "topic_count", "solution_count", "reputation_score", "is_banned")
    list_filter = ("is_banned", "warning_count", "created_at")
    search_fields = ("user__username", "user__email")
    readonly_fields = ("post_count", "topic_count", "solution_count", "created_at", "updated_at")
    
    fieldsets = (
        ("User Information", {
            "fields": ("user", "signature")
        }),
        ("Forum Settings", {
            "fields": ("show_online_status", "email_notifications")
        }),
        ("Statistics", {
            "fields": ("post_count", "topic_count", "solution_count", "reputation_score"),
            "classes": ("collapse",)
        }),
        ("Moderation", {
            "fields": ("warning_count", "is_banned", "ban_reason", "ban_until")
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        })
    )
    
    def get_user_level(self, obj):
        return obj.get_user_level()
    get_user_level.short_description = "Level"


@admin.register(m.ForumLike)
class ForumLikeAdmin(admin.ModelAdmin):
    list_display = ("user", "post", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__username", "post__topic__title")


@admin.register(m.ForumBookmark)
class ForumBookmarkAdmin(admin.ModelAdmin):
    list_display = ("user", "topic", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__username", "topic__title")


@admin.register(m.ForumNotification)
class ForumNotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "notification_type", "topic", "triggered_by", "is_read", "created_at")
    list_filter = ("notification_type", "is_read", "created_at")
    search_fields = ("user__username", "topic__title", "message")
    list_editable = ("is_read",)
