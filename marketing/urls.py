from django.urls import path

from . import views

app_name = "marketing"

urlpatterns = [
    path("lead-capture/", views.home, name="home"),
    path("lead-capture/thank-you/", views.popup_thank_you, name="popup_thank_you"),
    path("events/", views.events_list, name="events_list"),
    path("events/<slug:slug>/", views.event_detail, name="event_detail"),
    path(
        "events/<slug:slug>/registered/",
        views.event_registered,
        name="event_registered",
    ),
    path(
        "emerging-talent/",
        views.emerging_talent_list,
        name="emerging_talent_list",
    ),
    path(
        "emerging-talent/<slug:slug>/",
        views.emerging_talent_detail,
        name="emerging_talent_detail",
    ),
    path("partners/brands/", views.brand_partner, name="brand_partner"),
    path(
        "partners/brands/thank-you/",
        views.brand_partner_thanks,
        name="brand_partner_thanks",
    ),
    path("mentorship/", views.mentorship_landing, name="mentorship_landing"),
    path(
        "mentorship/apply/<slug:role_path>/",
        views.mentorship_apply,
        name="mentorship_apply",
    ),
    path(
        "mentorship/applied/<slug:role_path>/",
        views.mentorship_applied,
        name="mentorship_applied",
    ),
    path("community/", views.community_forum, name="community_forum"),
    path(
        "internal/community/",
        views.community_dashboard,
        name="community_dashboard",
    ),
    path(
        "internal/social-content/",
        views.social_content_dashboard,
        name="social_content_dashboard",
    ),
]
