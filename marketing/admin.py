from django.contrib import admin

from .models import FashionConsultLead


@admin.register(FashionConsultLead)
class FashionConsultLeadAdmin(admin.ModelAdmin):
    list_display = ("full_name", "country_code", "phone_number", "created_at")
    search_fields = ("full_name", "phone_number")
    list_filter = ("country_code", "created_at")
