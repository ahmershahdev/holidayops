from django.db import transaction
from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.accounts.auth import current_user
from apps.accounts.models import User
from apps.orgs.models import AuditLog, Membership, Organization, Role
from apps.orgs.scoping import OrgScopedMixin, audit, get_membership, unique_slug
from apps.orgs.serializers import (
    AuditLogSerializer,
    MemberCreateSerializer,
    MemberSerializer,
    OrgSerializer,
)

# /app/<org> shares its URL space with the web app's own pages.
APP_PATHS = frozenset({"account"})


class OrgViewSet(viewsets.GenericViewSet[Organization]):
    permission_classes = [IsAuthenticated]
    serializer_class = OrgSerializer
    pagination_class = None
    lookup_field = "slug"
    lookup_url_kwarg = "org_slug"

    def get_queryset(self) -> QuerySet[Organization]:
        if getattr(self, "swagger_fake_view", False):
            return Organization.objects.none()
        return Organization.objects.filter(memberships__user=current_user(self.request))

    def _require(self, org_slug: str, role: Role) -> Membership:
        membership = get_membership(self.request.user, org_slug)
        if not membership.has_role(role):
            raise PermissionDenied(_("Your role does not allow this action."))
        return membership

    def list(self, request: Request) -> Response:
        memberships = Membership.objects.filter(user=current_user(request)).select_related("org")
        data = [OrgSerializer(m.org, context={"role": m.role}).data for m in memberships]
        return Response(data)

    def create(self, request: Request) -> Response:
        serializer = OrgSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        name = serializer.validated_data["name"]
        with transaction.atomic():
            org = Organization.objects.create(
                name=name, slug=unique_slug(name, Organization.objects.all(), reserved=APP_PATHS)
            )
            membership = Membership.objects.create(
                user=current_user(request), org=org, role=Role.OWNER
            )
            audit(membership, "org.create", org)
        return Response(
            OrgSerializer(org, context={"role": Role.OWNER}).data, status=status.HTTP_201_CREATED
        )

    def retrieve(self, request: Request, org_slug: str) -> Response:
        membership = self._require(org_slug, Role.VIEWER)
        return Response(OrgSerializer(membership.org, context={"role": membership.role}).data)

    def partial_update(self, request: Request, org_slug: str) -> Response:
        membership = self._require(org_slug, Role.ADMIN)
        serializer = OrgSerializer(membership.org, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        audit(membership, "org.update", membership.org)
        return Response(OrgSerializer(membership.org, context={"role": membership.role}).data)

    def destroy(self, request: Request, org_slug: str) -> Response:
        membership = self._require(org_slug, Role.OWNER)
        membership.org.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MemberViewSet(OrgScopedMixin, viewsets.GenericViewSet[Membership]):
    serializer_class = MemberSerializer
    pagination_class = None
    write_role = Role.ADMIN

    def get_queryset(self) -> QuerySet[Membership]:
        if getattr(self, "swagger_fake_view", False):
            return Membership.objects.none()
        return self.org.memberships.select_related("user")

    def _guard_owner_change(self, target: Membership, new_role: str | None) -> None:
        touches_owner = Role.OWNER in (target.role, new_role)
        if touches_owner and not self.membership.has_role(Role.OWNER):
            raise PermissionDenied(_("Only owners can grant or remove the owner role."))
        is_last_owner = (
            target.role == Role.OWNER
            and new_role != Role.OWNER
            and not self.org.memberships.filter(role=Role.OWNER).exclude(pk=target.pk).exists()
        )
        if is_last_owner:
            raise ValidationError({"role": [_("An organization needs at least one owner.")]})

    def list(self, request: Request, org_slug: str) -> Response:
        return Response(MemberSerializer(self.get_queryset(), many=True).data)

    @extend_schema(request=MemberCreateSerializer, responses={201: MemberSerializer})
    def create(self, request: Request, org_slug: str) -> Response:
        serializer = MemberCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role = serializer.validated_data["role"]
        if role == Role.OWNER and not self.membership.has_role(Role.OWNER):
            raise PermissionDenied(_("Only owners can grant the owner role."))
        user = User.objects.filter(email__iexact=serializer.validated_data["email"]).first()
        if user is None:
            raise ValidationError({"email": [_("No account uses this email yet.")]})
        if self.org.memberships.filter(user=user).exists():
            raise ValidationError({"email": [_("This person is already a member.")]})
        member = Membership.objects.create(user=user, org=self.org, role=role)
        audit(self.membership, "member.add", f"{user.email} as {role}")
        return Response(MemberSerializer(member).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request: Request, org_slug: str, pk: str) -> Response:
        target = get_object_or_404(self.get_queryset(), pk=pk)
        serializer = MemberSerializer(target, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        old_role = target.role
        new_role = serializer.validated_data.get("role", old_role)
        self._guard_owner_change(target, new_role)
        serializer.save()
        audit(
            self.membership, "member.role_change", f"{target.user.email}: {old_role} -> {new_role}"
        )
        return Response(serializer.data)

    def destroy(self, request: Request, org_slug: str, pk: str) -> Response:
        target = get_object_or_404(self.get_queryset(), pk=pk)
        self._guard_owner_change(target, None)
        target.delete()
        audit(self.membership, "member.remove", target.user.email)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AuditLogViewSet(OrgScopedMixin, mixins.ListModelMixin, viewsets.GenericViewSet[AuditLog]):
    serializer_class = AuditLogSerializer
    read_role = Role.ADMIN

    def get_queryset(self) -> QuerySet[AuditLog]:
        if getattr(self, "swagger_fake_view", False):
            return AuditLog.objects.none()
        return self.org.audit_logs.select_related("actor")
