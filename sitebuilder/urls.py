from django.urls import path
from . import views

urlpatterns = [
    path("", views.builder_sites_list, name="builder_sites_list"),
    path("create/", views.builder_site_create, name="builder_site_create"),
    path("<slug:site_slug>/edit/", views.builder_editor, name="builder_editor"),
    path("<slug:site_slug>/edit/<int:page_id>/", views.builder_editor, name="builder_editor_page"),
    path("<slug:site_slug>/save/<int:page_id>/", views.builder_save_page, name="builder_save_page"),
    path("<slug:site_slug>/ai-generate/", views.builder_ai_generate, name="builder_ai_generate"),
    path("<slug:site_slug>/publish/", views.builder_publish, name="builder_publish"),
    path("p/<slug:site_slug>/<slug:page_slug>/", views.builder_public_page, name="builder_public_page"),
    path("p/<slug:site_slug>/", views.builder_public_page, name="builder_public_home", kwargs={"page_slug": "index"}),
]
