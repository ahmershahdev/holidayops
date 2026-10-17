from django.urls import include, path, re_path

from apps.feeds.views import FeedView
from config.spa import spa

handler404 = "config.errors.not_found"
handler500 = "config.errors.server_error"

urlpatterns = [
    path("api/v1/", include("apps.api.urls")),
    path("feeds/<str:token>.ics", FeedView.as_view(), name="feed"),
    path("", include("apps.public.urls")),
    # The web app's client-side routes (see frontend/src/main.tsx).
    re_path(r"^(?:playground|login|signup|invite|unsubscribe|app(?:/.*)?)$", spa, name="spa"),
]
