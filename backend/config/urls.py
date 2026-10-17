from django.urls import include, path

from apps.feeds.views import FeedView

urlpatterns = [
    path("api/v1/", include("apps.api.urls")),
    path("feeds/<str:token>.ics", FeedView.as_view(), name="feed"),
    path("", include("apps.public.urls")),
]
