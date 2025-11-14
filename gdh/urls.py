from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import TemplateView
from django.contrib.auth import views as auth_views
from django.views.generic.base import RedirectView
from designer_portfolio.views import signup_view, DesignerLoginView  # Import the signup_view and custom login

urlpatterns = [
    path("admin/", admin.site.urls),
    # Friendly alias: /login or /login/ -> accounts/login/ (preserve query string like ?next=)
    re_path(r"^login/?$", RedirectView.as_view(pattern_name="login", permanent=False, query_string=True)),
    path("accounts/login/", DesignerLoginView.as_view(), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(next_page="home"), name="logout"),
    path("accounts/password_reset/", auth_views.PasswordResetView.as_view(), name="password_reset"),
    path("accounts/", include("django.contrib.auth.urls")),  # includes reset/confirm/complete routes
    path("accounts/signup/", signup_view, name="signup"),
    # Social auth routes
    path("auth/", include("social_django.urls", namespace="social")),
    path("", include("designer_portfolio.urls")),  # your app
]