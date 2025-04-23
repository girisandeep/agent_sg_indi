from django.urls import path
from .views import chat_stream_view
from django.urls import re_path

urlpatterns = [
    path("api/chat/stream/", chat_stream_view),
    # re_path(r"^.*$", ReactAppView.as_view()),  # Catch-all to serve React app
]

