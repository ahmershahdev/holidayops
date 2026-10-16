from typing import Any

from rest_framework import serializers

from apps.accounts.serializers import UserSerializer
from apps.orgs.models import AuditLog, Membership, Organization, Role


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
