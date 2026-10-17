from rest_framework.routers import SimpleRouter

from apps.calendars.views import CalendarViewSet, CustomDayViewSet
from apps.feeds.views import FeedTokenViewSet
from apps.orgs.views import AuditLogViewSet, MemberViewSet, OrgViewSet

ORG = r"orgs/(?P<org_slug>[-a-zA-Z0-9_]+)"

router = SimpleRouter()
router.register("orgs", OrgViewSet, basename="org")
router.register(f"{ORG}/members", MemberViewSet, basename="member")
router.register(f"{ORG}/audit-log", AuditLogViewSet, basename="audit-log")
router.register(f"{ORG}/calendars", CalendarViewSet, basename="calendar")
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

urlpatterns = router.urls
