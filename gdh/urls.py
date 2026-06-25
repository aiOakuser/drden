from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import TemplateView
from django.contrib.auth import views as auth_views
from django.views.generic.base import RedirectView
from django.conf import settings
from django.conf.urls.static import static
from designer_portfolio.views import (
    signup_view,
    DesignerLoginView,
    DesignerPasswordResetView,
    DesignerPasswordResetConfirmView,
    health_check,
)  # Import the signup_view and custom login

urlpatterns = [
    path("health/", health_check, name="health_check"),
    path(
        "google1d2a084aaf123db7.html",
        TemplateView.as_view(template_name="google1d2a084aaf123db7.html", content_type="text/plain"),
        name="google_site_verification",
    ),
    path("admin/", admin.site.urls),
    path("", include("marketing.urls")),
    # Friendly alias: /login or /login/ -> accounts/login/ (preserve query string like ?next=)
    re_path(r"^login/?$", RedirectView.as_view(pattern_name="login", permanent=False, query_string=True)),
    re_path(r"^register/?$", RedirectView.as_view(pattern_name="signup", permanent=False, query_string=True)),
    path("accounts/login/", DesignerLoginView.as_view(), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(next_page="home"), name="logout"),
    path("accounts/password_reset/", DesignerPasswordResetView.as_view(), name="password_reset"),
    path(
        "accounts/reset/<uidb64>/<token>/",
        DesignerPasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path("accounts/", include("django.contrib.auth.urls")),  # includes reset/confirm/complete routes
    path("accounts/signup/", signup_view, name="signup"),
    # Social auth routes
    path("auth/", include("social_django.urls", namespace="social")),
    path("", include("designer_portfolio.urls")),  # your app
]

# Serve user-uploaded media when enabled (use S3 in production if possible).
if getattr(settings, "SERVE_MEDIA", False) and getattr(settings, "MEDIA_ROOT", None):
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)