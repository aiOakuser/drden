from django.contrib import admin

from .models import FashionConsultLead, SocialContentBundle


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
