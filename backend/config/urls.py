from django.urls import include, path, re_path

from apps.accounts import sso_views
from apps.feeds.views import FeedView
from config.spa import spa

handler404 = "config.errors.not_found"
handler500 = "config.errors.server_error"

urlpatterns = [
    path("api/v1/", include("apps.api.urls")),
    path("feeds/<str:token>.ics", FeedView.as_view(), name="feed"),
    path("sso/<str:provider>/start/", sso_views.start, name="sso-start"),
    path("sso/<str:provider>/callback/", sso_views.callback, name="sso-callback"),
    path("", include("apps.public.urls")),
    # The web app's client-side routes (see frontend/src/main.tsx).
    re_path(
        r"^(?:playground|login|signup|forgot-password|invite|unsubscribe|app(?:/.*)?)$",
        spa,
        name="spa",
    ),
]
