from django.contrib import admin
from .models import BuilderSite, BuilderPage, BuilderCollection, BuilderCollectionItem


@admin.register(BuilderSite)
class BuilderSiteAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "published", "slug", "updated_at")
    list_filter = ("published",)
    search_fields = ("name", "owner__username")


@admin.register(BuilderPage)
class BuilderPageAdmin(admin.ModelAdmin):
    list_display = ("title", "site", "is_home", "meta_title", "updated_at")
    list_filter = ("is_home",)
    search_fields = ("title", "meta_title")


@admin.register(BuilderCollection)
class BuilderCollectionAdmin(admin.ModelAdmin):
    list_display = ("name", "site", "slug")


@admin.register(BuilderCollectionItem)
class BuilderCollectionItemAdmin(admin.ModelAdmin):
    list_display = ("collection", "display_order", "updated_at")
    list_filter = ("collection",)
