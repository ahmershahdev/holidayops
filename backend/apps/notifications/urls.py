from django.urls import path, re_path

from apps.notifications import views

urlpatterns = [
    re_path(
        r"^orgs/(?P<org_slug>[-a-zA-Z0-9_]+)/calendars/(?P<calendar_id>[0-9a-f-]{36})/digest/$",
        views.DigestView.as_view(),
        name="digest",
    ),
    path("digests/unsubscribe/", views.UnsubscribeView.as_view(), name="digest-unsubscribe"),
]
