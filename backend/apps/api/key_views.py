from typing import Any

from django.db.models import QuerySet
from django.utils import timezone
from django.utils.translation import gettext as _
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.models import ApiKey
from apps.api.usage import daily_counts, plan_limits, used_this_month
from apps.orgs.limits import within_limit
from apps.orgs.models import Role
from apps.orgs.scoping import OrgScopedMixin, audit

MAX_USAGE_DAYS = 90


class ApiKeySerializer(serializers.ModelSerializer[ApiKey]):
    created_by = serializers.EmailField(source="created_by.email", read_only=True, allow_null=True)

    class Meta:
        model = ApiKey
        fields = ["id", "name", "prefix", "created_by", "created_at", "last_used_at"]
        read_only_fields = ["prefix", "created_at", "last_used_at"]


class ApiKeyCreatedSerializer(ApiKeySerializer):
    key = serializers.CharField(read_only=True, help_text="Shown only once. Keep it secret.")

    class Meta(ApiKeySerializer.Meta):
        fields = [*ApiKeySerializer.Meta.fields, "key"]


class UsageDaySerializer(serializers.Serializer[Any]):
    date = serializers.DateField()
    requests = serializers.IntegerField()
    failed = serializers.IntegerField(help_text="Responses with status 400 or higher.")


class UsageSerializer(serializers.Serializer[Any]):
    plan = serializers.CharField()
    rate = serializers.CharField()
    monthly_quota = serializers.IntegerField()
    used_this_month = serializers.IntegerField()
    max_keys = serializers.IntegerField()
    days = UsageDaySerializer(many=True)


class ApiKeyViewSet(
    OrgScopedMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet[ApiKey],
):
    serializer_class = ApiKeySerializer
    pagination_class = None
    read_role = Role.ADMIN
    write_role = Role.OWNER

    def get_queryset(self) -> QuerySet[ApiKey]:
        if getattr(self, "swagger_fake_view", False):
            return ApiKey.objects.none()
        return ApiKey.objects.filter(org=self.org, revoked_at__isnull=True).select_related(
            "created_by"
        )

    @extend_schema(responses={201: ApiKeyCreatedSerializer})
    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        max_keys = int(plan_limits(self.org)["max_keys"])
        message = _("Your plan allows at most %(max)s active API keys.") % {"max": max_keys}
        with within_limit("api_keys", self.org.pk, self.get_queryset(), max_keys, message):
            api_key = ApiKey(
                org=self.org,
                name=serializer.validated_data["name"],
                created_by=self.membership.user,
            )
            key = api_key.set_new_key()
            api_key.save()
            audit(self.membership, "api_key.create", api_key)
        data = ApiKeyCreatedSerializer(api_key).data
        data["key"] = key
        return Response(data, status=status.HTTP_201_CREATED)

    def perform_destroy(self, instance: ApiKey) -> None:
        instance.revoked_at = timezone.now()
        instance.save(update_fields=["revoked_at"])
        audit(self.membership, "api_key.revoke", instance)


class UsageView(OrgScopedMixin, APIView):
    read_role = Role.ADMIN

    @extend_schema(
        parameters=[OpenApiParameter("days", OpenApiTypes.INT, description="1-90, default 30.")],
        responses=UsageSerializer,
    )
    def get(self, request: Request, **kwargs: Any) -> Response:
        raw = request.query_params.get("days", "30")
        days = min(max(int(raw), 1), MAX_USAGE_DAYS) if raw.isdigit() else 30
        now = timezone.now()
        limits = plan_limits(self.org)
        data = {
            "plan": self.org.plan,
            "rate": limits["rate"],
            "monthly_quota": limits["monthly_quota"],
            "used_this_month": used_this_month(self.org, now),
            "max_keys": limits["max_keys"],
            "days": daily_counts(self.org, now.date(), days),
        }
        return Response(UsageSerializer(data).data)
