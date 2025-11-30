from django.urls import path

from . import views

app_name = "marketing"

urlpatterns = [
    path("lead-capture/", views.home, name="home"),
    path("lead-capture/thank-you/", views.popup_thank_you, name="popup_thank_you"),
]
