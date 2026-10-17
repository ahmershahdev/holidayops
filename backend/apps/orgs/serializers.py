from typing import Any

from rest_framework import serializers

from apps.accounts.serializers import UserSerializer
from apps.orgs.models import AuditLog, Invite, Membership, Organization, Role


class OrgSerializer(serializers.ModelSerializer[Organization]):
    role = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = ["id", "name", "slug", "role", "created_at"]
        read_only_fields = ["slug", "created_at"]

    def get_role(self, org: Organization) -> str | None:
        role: str | None = self.context.get("role")
        return role


class MemberSerializer(serializers.ModelSerializer[Membership]):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Membership
        fields = ["id", "user", "role", "created_at"]
        read_only_fields = ["created_at"]


class MemberCreateSerializer(serializers.Serializer[Any]):
    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=Role.choices)


class AuditLogSerializer(serializers.ModelSerializer[AuditLog]):
    actor = serializers.EmailField(source="actor.email", read_only=True, allow_null=True)

    class Meta:
        model = AuditLog
        fields = ["id", "action", "target", "actor", "created_at"]


class InviteSerializer(serializers.ModelSerializer[Invite]):
    invited_by = serializers.EmailField(source="invited_by.email", read_only=True, allow_null=True)

    class Meta:
        model = Invite
        fields = ["id", "email", "role", "invited_by", "created_at", "expires_at"]
        read_only_fields = ["created_at", "expires_at"]


class InvitePreviewSerializer(serializers.ModelSerializer[Invite]):
    org_name = serializers.CharField(source="org.name")
    org_slug = serializers.CharField(source="org.slug")
    invited_by = serializers.SerializerMethodField()

    class Meta:
        model = Invite
        fields = ["org_name", "org_slug", "email", "role", "invited_by", "expires_at"]

    def get_invited_by(self, invite: Invite) -> str:
        inviter = invite.invited_by
        return (inviter.name or inviter.email) if inviter else ""
