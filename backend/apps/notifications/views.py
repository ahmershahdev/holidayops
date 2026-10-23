from typing import Any

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.auth import verified_user
from apps.calendars.models import Calendar
from apps.notifications.digests import subscription_id_from
from apps.notifications.models import DigestSubscription
from apps.orgs.models import Role
from apps.orgs.scoping import OrgScopedMixin


class DigestSerializer(serializers.Serializer[Any]):
    subscribed = serializers.BooleanField()
    last_sent_on = serializers.DateField(allow_null=True)


class DigestView(OrgScopedMixin, APIView):
    """The current user's own monthly digest for a calendar; any member may opt in."""

    write_role = Role.VIEWER

    def initial(self, request: Request, *args: Any, **kwargs: Any) -> None:
        super().initial(request, *args, **kwargs)
        self.calendar = get_object_or_404(Calendar, org=self.org, id=kwargs["calendar_id"])

    def _state(self) -> Response:
        subscription = DigestSubscription.objects.filter(
            user=self.membership.user, calendar=self.calendar
        ).first()
        return Response(
            DigestSerializer(
                {
                    "subscribed": subscription is not None,
                    "last_sent_on": subscription.last_sent_on if subscription else None,
                }
            ).data
        )

    @extend_schema(responses=DigestSerializer)
    def get(self, request: Request, **kwargs: Any) -> Response:
        return self._state()

    @extend_schema(request=None, responses=DigestSerializer)
    def put(self, request: Request, **kwargs: Any) -> Response:
        verified_user(request)
        DigestSubscription.objects.get_or_create(
            user=self.membership.user, calendar=self.calendar, defaults={"org": self.org}
        )
        return self._state()

    @extend_schema(request=None, responses=DigestSerializer)
    def delete(self, request: Request, **kwargs: Any) -> Response:
        DigestSubscription.objects.filter(
            user=self.membership.user, calendar=self.calendar
        ).delete()
        return self._state()


class UnsubscribeView(APIView):
    """One-click unsubscribe (RFC 8058): mail clients POST here without a session."""

    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        request=inline_serializer("Unsubscribe", {"token": serializers.CharField()}),
        responses={204: None, 400: None},
    )
    def post(self, request: Request) -> Response:
        body = request.data if isinstance(request.data, dict) else {}
        token = request.query_params.get("token") or body.get("token") or ""
        subscription_id = subscription_id_from(str(token))
        if subscription_id is None:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        DigestSubscription.objects.filter(pk=subscription_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
