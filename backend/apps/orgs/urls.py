from django.urls import path, re_path
from rest_framework.routers import SimpleRouter

from apps.api.key_views import ApiKeyViewSet, UsageView
from apps.calendars.views import CalendarViewSet, CustomDayViewSet
from apps.feeds.views import FeedTokenViewSet
from apps.orgs.invite_views import InviteAcceptView, InvitePreviewView, InviteViewSet
from apps.orgs.views import AuditLogViewSet, MemberViewSet, OrgViewSet
from apps.webhooks.views import WebhookViewSet

ORG = r"orgs/(?P<org_slug>[-a-zA-Z0-9_]+)"

router = SimpleRouter()
router.register("orgs", OrgViewSet, basename="org")
router.register(f"{ORG}/members", MemberViewSet, basename="member")
router.register(f"{ORG}/invites", InviteViewSet, basename="invite")
router.register(f"{ORG}/api-keys", ApiKeyViewSet, basename="api-key")
router.register(f"{ORG}/audit-log", AuditLogViewSet, basename="audit-log")
router.register(f"{ORG}/calendars", CalendarViewSet, basename="calendar")
router.register(f"{ORG}/webhooks", WebhookViewSet, basename="webhook")
router.register(
    f"{ORG}/calendars/(?P<calendar_id>[0-9a-f-]{{36}})/custom-days",
    CustomDayViewSet,
    basename="custom-day",
)
router.register(
    f"{ORG}/calendars/(?P<calendar_id>[0-9a-f-]{{36}})/feeds",
    FeedTokenViewSet,
    basename="feed-token",
)

urlpatterns = [
    *router.urls,
    re_path(rf"^{ORG}/usage/$", UsageView.as_view(), name="usage"),
    path("invites/<str:token>/", InvitePreviewView.as_view(), name="invite-preview"),
    path("invites/<str:token>/accept/", InviteAcceptView.as_view(), name="invite-accept"),
]
