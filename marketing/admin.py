from django.contrib import admin

from .models import (
    BrandPartnershipLead,
    EmergingTalentFeature,
    EmergingTalentSubmission,
    Event,
    EventRegistration,
    FashionConsultLead,
    ForumInterestSignup,
    MentorshipApplication,
    SocialContentBundle,
)


@admin.register(SocialContentBundle)
class SocialContentBundleAdmin(admin.ModelAdmin):
    list_display = ("created_at", "bundle_kind", "success", "model_used")
    list_filter = ("bundle_kind", "success", "model_used")
    readonly_fields = ("created_at", "updated_at", "source_context", "platforms", "model_used", "success", "error")
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False


@admin.register(FashionConsultLead)
class FashionConsultLeadAdmin(admin.ModelAdmin):
    list_display = ("full_name", "country_code", "phone_number", "created_at")
    search_fields = ("full_name", "phone_number")
    list_filter = ("country_code", "created_at")


class EventRegistrationInline(admin.TabularInline):
    model = EventRegistration
    extra = 0
    fields = ("email", "full_name", "cancelled_at", "attended_at", "created_at")
    readonly_fields = ("created_at",)
    show_change_link = True


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "status", "starts_at", "is_virtual", "created_at")
    list_filter = ("kind", "status", "is_virtual", "starts_at")
    search_fields = ("title", "summary", "host_name")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("created_at", "updated_at")
    inlines = [EventRegistrationInline]
    actions = ("mark_ended_action", "mark_cancelled_action")

    @admin.action(description="Mark selected events as ended")
    def mark_ended_action(self, request, queryset):
        updated = queryset.exclude(status=Event.Status.ENDED).update(
            status=Event.Status.ENDED
        )
        self.message_user(request, f"Marked {updated} event(s) as ended.")

    @admin.action(description="Mark selected events as cancelled")
    def mark_cancelled_action(self, request, queryset):
        updated = queryset.exclude(status=Event.Status.CANCELLED).update(
            status=Event.Status.CANCELLED
        )
        self.message_user(request, f"Cancelled {updated} event(s).")


@admin.register(EventRegistration)
class EventRegistrationAdmin(admin.ModelAdmin):
    list_display = ("event", "email", "full_name", "cancelled_at", "attended_at", "created_at")
    list_filter = ("event__kind", "cancelled_at", "attended_at")
    search_fields = ("email", "full_name", "event__title")
    readonly_fields = ("cancel_token", "created_at", "updated_at")


@admin.register(EmergingTalentFeature)
class EmergingTalentFeatureAdmin(admin.ModelAdmin):
    list_display = (
        "display_name",
        "title",
        "is_published",
        "ordering",
        "published_at",
        "created_at",
    )
    list_filter = ("is_published", "created_at")
    search_fields = ("display_name", "title", "designer_user__username")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("created_at", "updated_at")
    actions = ("publish_action",)

    @admin.action(description="Publish selected features")
    def publish_action(self, request, queryset):
        updated = 0
        for feature in queryset:
            if not feature.is_published:
                feature.mark_published()
                updated += 1
        self.message_user(request, f"Published {updated} feature(s).")


@admin.register(EmergingTalentSubmission)
class EmergingTalentSubmissionAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "email",
        "school",
        "grad_year",
        "status",
        "converted_feature",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("full_name", "email", "school", "focus_areas")
    readonly_fields = ("converted_feature", "created_at", "updated_at")
    actions = ("convert_to_feature_action", "decline_action")

    @admin.action(description="Convert to draft Emerging Talent feature")
    def convert_to_feature_action(self, request, queryset):
        converted = 0
        skipped = 0
        for submission in queryset:
            if submission.converted_feature is None:
                submission.convert_to_feature()
                converted += 1
            else:
                skipped += 1
        msg = f"Converted {converted} submission(s) to feature drafts."
        if skipped:
            msg += f" Skipped {skipped} already-converted submission(s)."
        self.message_user(request, msg)

    @admin.action(description="Decline")
    def decline_action(self, request, queryset):
        updated = queryset.exclude(status=EmergingTalentSubmission.Status.DECLINED).update(
            status=EmergingTalentSubmission.Status.DECLINED
        )
        self.message_user(request, f"Declined {updated} submission(s).")


@admin.register(BrandPartnershipLead)
class BrandPartnershipLeadAdmin(admin.ModelAdmin):
    list_display = (
        "brand_name",
        "contact_name",
        "partnership_kind",
        "email",
        "created_at",
    )
    list_filter = ("partnership_kind", "created_at")
    search_fields = ("brand_name", "contact_name", "email")
    readonly_fields = ("created_at",)


@admin.register(MentorshipApplication)
class MentorshipApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "role",
        "status",
        "email",
        "headline",
        "created_at",
    )
    list_filter = ("role", "status", "created_at")
    search_fields = ("full_name", "email", "headline", "focus_areas")
    readonly_fields = ("created_at", "updated_at")
    actions = ("activate_action", "match_action", "decline_action")

    @admin.action(description="Approve · waiting to match (set status=ACTIVE)")
    def activate_action(self, request, queryset):
        updated = queryset.exclude(status=MentorshipApplication.Status.ACTIVE).update(
            status=MentorshipApplication.Status.ACTIVE
        )
        self.message_user(request, f"Activated {updated} application(s).")

    @admin.action(description="Mark as matched")
    def match_action(self, request, queryset):
        updated = queryset.exclude(status=MentorshipApplication.Status.MATCHED).update(
            status=MentorshipApplication.Status.MATCHED
        )
        self.message_user(request, f"Matched {updated} application(s).")

    @admin.action(description="Decline")
    def decline_action(self, request, queryset):
        updated = queryset.exclude(status=MentorshipApplication.Status.DECLINED).update(
            status=MentorshipApplication.Status.DECLINED
        )
        self.message_user(request, f"Declined {updated} application(s).")


@admin.register(ForumInterestSignup)
class ForumInterestSignupAdmin(admin.ModelAdmin):
    list_display = ("email", "full_name", "created_at")
    search_fields = ("email", "full_name", "notes")
    readonly_fields = ("created_at",)
