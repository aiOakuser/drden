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


class EventAttendeeInline(admin.TabularInline):
    model = m.EventAttendee
    extra = 0
    fields = ("full_name", "email", "company", "ticket_count", "checked_in", "created_at")
    readonly_fields = ("created_at",)


class EventCollaborationInline(admin.TabularInline):
    model = m.EventCollaboration
    extra = 0
    fields = ("full_name", "email", "company", "role", "status", "is_contacted", "created_at")
    readonly_fields = ("created_at",)


# ---------------- Event ----------------
@admin.register(m.Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "event_date",
        "end_date",
        "location",
        "venue",
        "attendee_capacity",
        "is_popup",
        "popup_order",
        "cover_preview",
        "created_at",
    )
    list_filter = ("is_popup", "event_date", "end_date")
    search_fields = ("title", "description")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [EventImageInline, EventAttendeeInline, EventCollaborationInline]

    def cover_preview(self, obj):
        if obj.cover:
            return format_html(
                '<img src="{}" style="width:80px; height:80px; object-fit:cover; border-radius:6px;" />',
                obj.cover.url,
            )
        return "-"
    cover_preview.short_description = "Cover"


@admin.register(m.EventAttendee)
class EventAttendeeAdmin(admin.ModelAdmin):
    list_display = ("full_name", "event", "email", "company", "ticket_count", "checked_in", "created_at")
    list_filter = ("checked_in", "created_at")
    search_fields = ("full_name", "email", "company", "event__title")
    readonly_fields = ("created_at", "updated_at")


@admin.register(m.EventCollaboration)
class EventCollaborationAdmin(admin.ModelAdmin):
    list_display = ("full_name", "event", "email", "company", "role", "status", "is_contacted", "created_at")
    list_filter = ("status", "is_contacted", "created_at")
    search_fields = ("full_name", "email", "company", "role", "event__title")
    readonly_fields = ("created_at", "updated_at")


# ---------------- Dress Order ----------------
class DressOrderUpdateInline(admin.TabularInline):
    model = m.DressOrderUpdate
    extra = 0
    readonly_fields = ("created_at",)


@admin.register(m.DressOrder)
class DressOrderAdmin(admin.ModelAdmin):
    list_display = ("id", "designer", "dress_label", "formal_subcategory", "status", "fabric_label", "customer_phone", "created_at")
    list_filter = ("created_at", "status", "dress_type", "fabric_type")
    search_fields = ("customer_phone", "customer_email", "dress_label", "fabric_label", "designer__user__username")
    readonly_fields = ("created_at", "updated_at", "access_token")
    raw_id_fields = ("designer", "design")
    inlines = (DressOrderUpdateInline,)
    ordering = ("-created_at",)


@admin.register(m.DressOrderUpdate)
class DressOrderUpdateAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "status", "created_at")
    list_filter = ("created_at", "status")
    readonly_fields = ("created_at", "updated_at")


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


# ---------------- Student Portfolio ----------------
class StudentPortfolioProjectInline(admin.TabularInline):
    model = m.StudentPortfolioProject
    extra = 0
    fields = (
        "title",
        "category",
        "featured",
        "display_order",
        "created_at",
    )
    readonly_fields = ("created_at",)
    show_change_link = True


@admin.register(m.StudentPortfolio)
class StudentPortfolioAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "visibility",
        "template_style",
        "project_count",
        "updated_at",
    )
    list_filter = ("visibility", "template_style", "updated_at")
    search_fields = ("user__username", "user__email", "skills", "design_interests")
    readonly_fields = ("created_at", "updated_at", "share_slug")
    inlines = [StudentPortfolioProjectInline]

    def project_count(self, obj):
        return obj.projects.count()
    project_count.short_description = "Projects"


@admin.register(m.StudentPortfolioProject)
class StudentPortfolioProjectAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "portfolio",
        "category",
        "featured",
        "display_order",
        "created_at",
    )
    list_filter = ("category", "featured", "created_at")
    search_fields = ("title", "portfolio__user__username", "tools_used", "project_role")
    readonly_fields = ("created_at", "updated_at")


@admin.register(m.StudentProjectFeedback)
class StudentProjectFeedbackAdmin(admin.ModelAdmin):
    list_display = ("project", "author", "reviewer_role", "created_at")
    list_filter = ("reviewer_role", "created_at")
    search_fields = ("project__title", "author__username", "comment")
    readonly_fields = ("created_at", "updated_at")


@admin.register(m.StudentProjectLike)
class StudentProjectLikeAdmin(admin.ModelAdmin):
    list_display = ("user", "project", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__username", "project__title")


@admin.register(m.StudentProjectBookmark)
class StudentProjectBookmarkAdmin(admin.ModelAdmin):
    list_display = ("user", "project", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__username", "project__title")


# ---------------- Referral System ----------------
@admin.register(m.ReferralTier)
class ReferralTierAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "min_referrals", "sort_order", "is_active")
    list_editable = ("min_referrals", "sort_order", "is_active")


@admin.register(m.UserReferralProfile)
class UserReferralProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "referral_code", "referral_count", "current_tier", "referred_by", "updated_at")
    list_filter = ("current_tier",)
    search_fields = ("user__username", "referral_code")
    readonly_fields = ("referral_code", "referral_count", "referral_joined_at", "updated_at")


@admin.register(m.ReferralEvent)
class ReferralEventAdmin(admin.ModelAdmin):
    list_display = ("referrer", "referred_user", "referral_code", "source", "created_at")
    list_filter = ("source", "created_at")
    search_fields = ("referrer__username", "referred_user__username", "referral_code")
    readonly_fields = ("created_at",)


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


# ---------------- User Messenger ----------------
class ChatMessageInline(admin.TabularInline):
    model = m.ChatMessage
    extra = 0
    readonly_fields = ("sender", "body", "created_at", "read_at")
    can_delete = True


@admin.register(m.ChatConversation)
class ChatConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "user1", "user2", "updated_at")
    list_filter = ("updated_at",)
    search_fields = ("user1__username", "user2__username")
    readonly_fields = ("created_at", "updated_at")
    inlines = (ChatMessageInline,)


@admin.register(m.ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation", "sender", "short_body", "created_at")
    list_filter = ("created_at",)
    search_fields = ("body", "sender__username")
    readonly_fields = ("created_at", "updated_at")
    raw_id_fields = ("conversation", "sender")

    def short_body(self, obj):
        return obj.body[:80] + "..." if len(obj.body) > 80 else obj.body
    short_body.short_description = "Body"


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
