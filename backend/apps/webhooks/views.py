from typing import Any

from django.db.models import QuerySet
from django.utils.translation import gettext as _
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.orgs.models import Role
from apps.orgs.scoping import OrgScopedMixin, audit
from apps.webhooks import events
from apps.webhooks.models import Webhook, new_secret
from apps.webhooks.serializers import (
    DeliverySerializer,
    WebhookSecretSerializer,
    WebhookSerializer,
)

MAX_WEBHOOKS = 10
RECENT_DELIVERIES = 50


class WebhookViewSet(OrgScopedMixin, viewsets.ModelViewSet[Webhook]):
    serializer_class = WebhookSerializer
    read_role = Role.ADMIN
    write_role = Role.ADMIN
    http_method_names = ["get", "post", "patch", "delete"]

    def get_queryset(self) -> QuerySet[Webhook]:
        if getattr(self, "swagger_fake_view", False):
            return Webhook.objects.none()
        return Webhook.objects.filter(org=self.org).select_related("created_by", "org")

    @extend_schema(responses={201: WebhookSecretSerializer})
    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if self.get_queryset().count() >= MAX_WEBHOOKS:
            raise serializers.ValidationError(
                _("An organization can have at most %(max)s webhooks.") % {"max": MAX_WEBHOOKS}
            )
        webhook = serializer.save(org=self.org, created_by=self.membership.user)
        audit(self.membership, "webhook.create", webhook)
        return Response(WebhookSecretSerializer(webhook).data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer: serializers.BaseSerializer[Webhook]) -> None:
        extra = {"failure_count": 0} if serializer.validated_data.get("is_active") else {}
        webhook = serializer.save(**extra)
        audit(self.membership, "webhook.update", webhook)

    def perform_destroy(self, instance: Webhook) -> None:
        audit(self.membership, "webhook.delete", instance)
        instance.delete()

    @extend_schema(request=None, responses=WebhookSecretSerializer)
    @action(detail=True, methods=["post"], url_path="rotate-secret")
    def rotate_secret(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        webhook = self.get_object()
        webhook.secret = new_secret()
        webhook.save(update_fields=["secret"])
        audit(self.membership, "webhook.rotate", webhook)
        return Response(WebhookSecretSerializer(webhook).data)

    @extend_schema(request=None, responses={202: DeliverySerializer})
    @action(detail=True, methods=["post"])
    def ping(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        delivery = events.ping(self.get_object())
        return Response(DeliverySerializer(delivery).data, status=status.HTTP_202_ACCEPTED)

    @extend_schema(responses=DeliverySerializer(many=True))
    @action(detail=True, methods=["get"], pagination_class=None)
    def deliveries(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        recent = self.get_object().deliveries.all()[:RECENT_DELIVERIES]
        return Response(DeliverySerializer(recent, many=True).data)
