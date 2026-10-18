from typing import Any

from django.contrib.auth import password_validation
from django.utils.translation import gettext as _
from rest_framework import serializers

from apps.accounts.models import TwoFactor, User


class UserSerializer(serializers.ModelSerializer[User]):
    two_factor = serializers.SerializerMethodField()
    has_password = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "name", "language", "two_factor", "has_password"]
        read_only_fields = ["email"]

    def get_two_factor(self, user: User) -> bool:
        return TwoFactor.objects.filter(user=user, confirmed_at__isnull=False).exists()

    def get_has_password(self, user: User) -> bool:
        return user.has_usable_password()


class SignupSerializer(serializers.Serializer[Any]):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, max_length=128)
    name = serializers.CharField(required=False, allow_blank=True, max_length=150)

    def validate_email(self, value: str) -> str:
        email = User.objects.normalize_email(value).lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError(_("An account with this email already exists."))
        return email

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        candidate = User(email=attrs["email"], name=attrs.get("name", ""))
        password_validation.validate_password(attrs["password"], candidate)
        return attrs


class LoginSerializer(serializers.Serializer[Any]):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, max_length=128)


class ForgotPasswordSerializer(serializers.Serializer[Any]):
    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer[Any]):
    email = serializers.EmailField()
    code = serializers.RegexField(r"^\d{6}$", max_length=6)
    password = serializers.CharField(write_only=True, max_length=128)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        candidate = User(email=attrs["email"])
        password_validation.validate_password(attrs["password"], candidate)
        return attrs


class TwoFactorRequiredSerializer(serializers.Serializer[Any]):
    two_factor_required = serializers.BooleanField()


class CodeSerializer(serializers.Serializer[Any]):
    code = serializers.CharField(max_length=20, trim_whitespace=True)


class TwoFactorStatusSerializer(serializers.Serializer[Any]):
    enabled = serializers.BooleanField()
    recovery_codes_left = serializers.IntegerField()


class TwoFactorSetupSerializer(serializers.Serializer[Any]):
    secret = serializers.CharField()
    uri = serializers.CharField()
    qr = serializers.CharField()


class RecoveryCodesSerializer(serializers.Serializer[Any]):
    recovery_codes = serializers.ListField(child=serializers.CharField())


class DisableTwoFactorSerializer(CodeSerializer):
    password = serializers.CharField(write_only=True, max_length=128, required=False, default="")


class ProviderSerializer(serializers.Serializer[Any]):
    id = serializers.CharField()
    name = serializers.CharField()


class IdentitySerializer(serializers.Serializer[Any]):
    provider = serializers.CharField()
    email = serializers.EmailField()
    created_at = serializers.DateTimeField()


class DeleteAccountSerializer(serializers.Serializer[Any]):
    password = serializers.CharField(write_only=True, max_length=128, required=False, default="")
    confirm = serializers.CharField(max_length=254)
