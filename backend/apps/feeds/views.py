import hashlib
from collections.abc import Iterable
from datetime import date, timedelta
from typing import Any

from django.core.cache import cache
from django.db import transaction
from django.db.models import QuerySet
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.negotiation import BaseContentNegotiation
from rest_framework.parsers import BaseParser
from rest_framework.permissions import AllowAny
from rest_framework.renderers import BaseRenderer
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.calendars.models import Calendar
from apps.calendars.services import build_merged
from apps.core import build_ical, feed_events
from apps.feeds.models import FeedToken, hash_token
from apps.feeds.serializers import FeedTokenCreatedSerializer, FeedTokenSerializer
from apps.orgs.scoping import OrgScopedMixin, audit

MAX_ACTIVE_FEEDS = 10
FEED_MAX_AGE = 3600
LAST_USED_PRECISION = timedelta(hours=1)


class FeedTokenViewSet(
    OrgScopedMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet[FeedToken],
):
    serializer_class = FeedTokenSerializer

    def initial(self, request: Request, *args: Any, **kwargs: Any) -> None:
        super().initial(request, *args, **kwargs)
        self.calendar = get_object_or_404(Calendar, org=self.org, id=kwargs["calendar_id"])

    def get_queryset(self) -> QuerySet[FeedToken]:
        if getattr(self, "swagger_fake_view", False):
            return FeedToken.objects.none()
        return FeedToken.objects.filter(
            calendar=self.calendar, revoked_at__isnull=True
        ).select_related("created_by")

    @extend_schema(responses={201: FeedTokenCreatedSerializer})
    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if self.get_queryset().count() >= MAX_ACTIVE_FEEDS:
            raise serializers.ValidationError(
                _("A calendar can have at most %(max)s active feed links.")
                % {"max": MAX_ACTIVE_FEEDS}
            )
        feed, token = self._issue(serializer.validated_data.get("label", ""))
        audit(self.membership, "feed.create", feed)
        return self._created(feed, token)

    @extend_schema(request=None, responses={201: FeedTokenCreatedSerializer})
    @action(detail=True, methods=["post"])
    def rotate(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        old = self.get_object()
        with transaction.atomic():
            old.revoked_at = timezone.now()
            old.save(update_fields=["revoked_at"])
            feed, token = self._issue(old.label)
        audit(self.membership, "feed.rotate", feed)
        return self._created(feed, token)

    def perform_destroy(self, instance: FeedToken) -> None:
        instance.revoked_at = timezone.now()
        instance.save(update_fields=["revoked_at"])
        audit(self.membership, "feed.revoke", instance)

    def _issue(self, label: str) -> tuple[FeedToken, str]:
        feed = FeedToken(
            org=self.org, calendar=self.calendar, label=label, created_by=self.membership.user
        )
        token = feed.set_new_token()
        feed.save()
        return feed, token

    def _created(self, feed: FeedToken, token: str) -> Response:
        data = FeedTokenCreatedSerializer(feed).data
        data["url"] = self.request.build_absolute_uri(reverse("feed", args=[token]))
        return Response(data, status=status.HTTP_201_CREATED)


class IgnoreAcceptHeader(BaseContentNegotiation):
    """Calendar apps send all kinds of Accept headers; the feed is always iCal, errors JSON."""

    def select_parser(self, request: Request, parsers: Iterable[BaseParser]) -> BaseParser | None:
        return next(iter(parsers), None)

    def select_renderer(
        self, request: Request, renderers: Iterable[BaseRenderer], format_suffix: str | None = None
    ) -> tuple[BaseRenderer, str]:
        renderer = next(iter(renderers))
        return renderer, renderer.media_type


class FeedView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    content_negotiation_class = IgnoreAcceptHeader

    @extend_schema(exclude=True)
    def get(self, request: Request, token: str) -> HttpResponse:
        feed = (
            FeedToken.objects.select_related("calendar")
            .filter(token_hash=hash_token(token), revoked_at__isnull=True)
            .first()
        )
        if feed is None:
            raise Http404
        body = _feed_body(feed.calendar, timezone.now().date())
        _mark_used(feed)
        etag = f'"{hashlib.sha256(body).hexdigest()[:32]}"'
        headers = {"ETag": etag, "Cache-Control": f"private, max-age={FEED_MAX_AGE}"}
        if request.headers.get("If-None-Match") == etag:
            return HttpResponse(status=304, headers=headers)
        headers["Content-Disposition"] = f'inline; filename="{feed.calendar.slug}.ics"'
        return HttpResponse(body, content_type="text/calendar; charset=utf-8", headers=headers)


def _feed_body(calendar: Calendar, today: date) -> bytes:
    start, end = date(today.year - 1, 1, 1), date(today.year + 1, 12, 31)
    key = f"feed:{calendar.pk}:{today.year}:{calendar.updated_at.isoformat()}"
    body: bytes | None = cache.get(key)
    if body is None:
        merged = build_merged(calendar, range(start.year, end.year + 1))
        events = feed_events(merged, start, end)
        text = build_ical(calendar.name, str(calendar.pk), events, calendar.updated_at.date())
        body = text.encode()
        cache.set(key, body, FEED_MAX_AGE)
    return body


def _mark_used(feed: FeedToken) -> None:
    now = timezone.now()
    if feed.last_used_at is None or now - feed.last_used_at > LAST_USED_PRECISION:
        FeedToken.objects.filter(pk=feed.pk).update(last_used_at=now)
