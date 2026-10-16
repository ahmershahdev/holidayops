from typing import Any

from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import serializers, viewsets
from rest_framework.request import Request

from apps.calendars.models import Calendar, CustomDay
from apps.calendars.serializers import CalendarSerializer, CustomDaySerializer
from apps.orgs.models import Role
from apps.orgs.scoping import OrgScopedMixin, audit, unique_slug


class CalendarViewSet(OrgScopedMixin, viewsets.ModelViewSet[Calendar]):
    serializer_class = CalendarSerializer
    delete_role = Role.ADMIN
    http_method_names = ["get", "post", "patch", "delete"]

    def get_queryset(self) -> QuerySet[Calendar]:
        if getattr(self, "swagger_fake_view", False):
            return Calendar.objects.none()
        return Calendar.objects.filter(org=self.org).prefetch_related("sources")

    def perform_create(self, serializer: serializers.BaseSerializer[Calendar]) -> None:
        name = serializer.validated_data["name"]
        slug = unique_slug(name, Calendar.objects.filter(org=self.org))
        calendar = serializer.save(org=self.org, slug=slug)
        audit(self.membership, "calendar.create", calendar)

    def perform_destroy(self, instance: Calendar) -> None:
        audit(self.membership, "calendar.delete", instance)
        instance.delete()


@extend_schema_view(
    list=extend_schema(
        parameters=[OpenApiParameter("year", OpenApiTypes.INT, description="Only this year.")]
    )
)
class CustomDayViewSet(OrgScopedMixin, viewsets.ModelViewSet[CustomDay]):
    serializer_class = CustomDaySerializer
    http_method_names = ["get", "post", "patch", "delete"]

    def initial(self, request: Request, *args: Any, **kwargs: Any) -> None:
        super().initial(request, *args, **kwargs)
        self.calendar = get_object_or_404(Calendar, org=self.org, id=kwargs["calendar_id"])

    def get_queryset(self) -> QuerySet[CustomDay]:
        if getattr(self, "swagger_fake_view", False):
            return CustomDay.objects.none()
        days = CustomDay.objects.filter(calendar=self.calendar)
        year = self.request.query_params.get("year", "")
        return days.filter(date__year=int(year)) if year.isdigit() else days

    def get_serializer_context(self) -> dict[str, Any]:
        return {**super().get_serializer_context(), "calendar": self.calendar}

    def perform_create(self, serializer: serializers.BaseSerializer[CustomDay]) -> None:
        serializer.save(calendar=self.calendar)
