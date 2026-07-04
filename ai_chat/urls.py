from django.urls import path
from . import views

urlpatterns = [
    path("stream/", views.stream_chat, name="ai_chat_stream"),
]
