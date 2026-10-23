from typing import Any

from django.contrib.auth import password_validation
from rest_framework import serializers

from apps.accounts.models import TwoFactor, User


class UserSerializer(serializers.ModelSerializer[User]):
    two_factor = serializers.SerializerMethodField()
    has_password = serializers.SerializerMethodField()
    email_verified = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "name", "language", "two_factor", "has_password", "email_verified"]
        read_only_fields = ["email"]

    def get_two_factor(self, user: User) -> bool:
        return TwoFactor.objects.filter(user=user, confirmed_at__isnull=False).exists()

    def get_has_password(self, user: User) -> bool:
        return user.has_usable_password()


class BotCheckSerializer(serializers.Serializer[Any]):
    """Read by apps/accounts/captcha.py; declared so the API schema and client know them."""

    captcha_v3 = serializers.CharField(
        required=False, allow_blank=True, write_only=True, max_length=4096
    )
    captcha_v2 = serializers.CharField(
        required=False, allow_blank=True, write_only=True, max_length=4096
    )
    website = serializers.CharField(
        required=False,
        allow_blank=True,
        write_only=True,
        max_length=200,
        help_text="Leave empty. A honeypot: forms filled by scripts fill it.",
    )


class SignupSerializer(BotCheckSerializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, max_length=128)
    name = serializers.CharField(required=False, allow_blank=True, max_length=150)

    def validate_email(self, value: str) -> str:
        return User.objects.normalize_email(value).lower()

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        candidate = User(email=attrs["email"], name=attrs.get("name", ""))
        password_validation.validate_password(attrs["password"], candidate)
        return attrs


class VerifyEmailSerializer(serializers.Serializer[Any]):
    email = serializers.EmailField()
    code = serializers.RegexField(r"^\d{6}$", max_length=6)


class CheckEmailSerializer(serializers.Serializer[Any]):
    """The answer to sign-up and to a code request: the same whether or not the address has an
    account."""

    detail = serializers.CharField()
    verification_required = serializers.BooleanField()


class CaptchaKeysSerializer(serializers.Serializer[Any]):
    v3 = serializers.CharField(allow_null=True)
    v2 = serializers.CharField(allow_null=True)


class LoginSerializer(serializers.Serializer[Any]):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, max_length=128)


class ForgotPasswordSerializer(BotCheckSerializer):
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


class SessionSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    created_at = serializers.DateTimeField()
    last_seen_at = serializers.DateTimeField()
    ip = serializers.CharField(allow_null=True)
    browser = serializers.CharField()
    system = serializers.CharField()
    current = serializers.BooleanField()


class DeleteAccountSerializer(serializers.Serializer[Any]):
    password = serializers.CharField(write_only=True, max_length=128, required=False, default="")
    confirm = serializers.CharField(max_length=254)
