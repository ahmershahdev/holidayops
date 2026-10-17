from smtplib import SMTPException
from typing import Any

from django.db import transaction
from django.db.models import QuerySet
from django.http import Http404
from django.utils.translation import gettext as _
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import BaseThrottle
from rest_framework.views import APIView

from apps.accounts.auth import current_user
from apps.orgs import invites
from apps.orgs.models import Invite, Role
from apps.orgs.scoping import OrgScopedMixin, audit
from apps.orgs.serializers import (
    InvitePreviewSerializer,
    InviteSerializer,
    MemberCreateSerializer,
    OrgSerializer,
)

MAX_PENDING_INVITES = 50


class EmailUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_code = "email_unavailable"


class InviteViewSet(
    OrgScopedMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet[Invite],
):
    serializer_class = InviteSerializer
    pagination_class = None
    read_role = Role.ADMIN
    write_role = Role.ADMIN

    def get_throttles(self) -> list[BaseThrottle]:
        if self.action in {"create", "resend"}:
            self.throttle_scope = "invite"
        return super().get_throttles()

    def get_queryset(self) -> QuerySet[Invite]:
        if getattr(self, "swagger_fake_view", False):
            return Invite.objects.none()
        return invites.pending(self.org).select_related("invited_by")

    @extend_schema(request=MemberCreateSerializer, responses={201: InviteSerializer})
    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = MemberCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].lower()
        role = serializer.validated_data["role"]
        if role == Role.OWNER and not self.membership.has_role(Role.OWNER):
            raise PermissionDenied(_("Only owners can grant the owner role."))
        if self.org.memberships.filter(user__email__iexact=email).exists():
            raise ValidationError({"email": [_("This person is already a member.")]})
        if self.get_queryset().exclude(email=email).count() >= MAX_PENDING_INVITES:
            raise ValidationError(
                _("An organization can have at most %(max)s pending invites.")
                % {"max": MAX_PENDING_INVITES}
            )
        with transaction.atomic():
            self.org.invites.filter(email=email, accepted_at__isnull=True).delete()
            invite = Invite(org=self.org, email=email, role=role, invited_by=self.membership.user)
            token = invites.issue(invite)
            invite.save()
            audit(self.membership, "invite.create", f"{email} as {role}")
            self._send(invite, token)
        return Response(InviteSerializer(invite).data, status=status.HTTP_201_CREATED)

    @extend_schema(request=None, responses=InviteSerializer)
    @action(detail=True, methods=["post"])
    def resend(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        invite = self.get_object()
        with transaction.atomic():
            token = invites.issue(invite)
            invite.save(update_fields=["token_hash", "expires_at"])
            audit(self.membership, "invite.resend", invite.email)
            self._send(invite, token)
        return Response(InviteSerializer(invite).data)

    def perform_destroy(self, instance: Invite) -> None:
        audit(self.membership, "invite.revoke", instance.email)
        instance.delete()

    def _send(self, invite: Invite, token: str) -> None:
        # Raising inside the atomic block rolls the invite back, so there is never a pending
        # invite whose email didn't go out.
        try:
            invites.send(invite, token, self.request.LANGUAGE_CODE)
        except (SMTPException, OSError) as exc:
            raise EmailUnavailable(_("The invite email could not be sent. Try again.")) from exc


def _pending_or_404(token: str) -> Invite:
    invite = invites.find_pending(token)
    if invite is None:
        raise Http404
    return invite


class InvitePreviewView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses=InvitePreviewSerializer)
    def get(self, request: Request, token: str) -> Response:
        return Response(InvitePreviewSerializer(_pending_or_404(token)).data)


class InviteAcceptView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses=OrgSerializer)
    def post(self, request: Request, token: str) -> Response:
        user = current_user(request)
        with transaction.atomic():
            invite = _pending_or_404(token)
            if invite.email.lower() != user.email.lower():
                raise PermissionDenied(
                    _("This invite is for %(email)s. Log in with that account to accept it.")
                    % {"email": invite.email}
                )
            membership = invites.accept(invite, user)
            audit(membership, "invite.accept", f"{user.email} as {membership.role}")
        return Response(OrgSerializer(invite.org, context={"role": membership.role}).data)
