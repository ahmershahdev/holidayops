import logging

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.decorators.csrf import ensure_csrf_cookie
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts import data, sso, twofactor
from apps.accounts.auth import current_user
from apps.accounts.models import SocialIdentity, User
from apps.accounts.resets import request_reset, reset_password
from apps.accounts.serializers import (
    CodeSerializer,
    DeleteAccountSerializer,
    DisableTwoFactorSerializer,
    ForgotPasswordSerializer,
    IdentitySerializer,
    LoginSerializer,
    ProviderSerializer,
    RecoveryCodesSerializer,
    ResetPasswordSerializer,
    SignupSerializer,
    TwoFactorRequiredSerializer,
    TwoFactorSetupSerializer,
    TwoFactorStatusSerializer,
    UserSerializer,
)
from config.security_log import email_ref, security_event

MODEL_BACKEND = "django.contrib.auth.backends.ModelBackend"


def finish_login(request: Request, user: User, event: str) -> Response:
    """Log in, or, with two-factor on, hold the user at the code step."""
    if twofactor.enabled(user):
        twofactor.start_pending(request._request, user)
        security_event("auth.two_factor_challenge", request, logging.INFO, user=user.pk)
        return Response({"two_factor_required": True}, status=status.HTTP_202_ACCEPTED)
    login(request._request, user, backend=MODEL_BACKEND)
    security_event(event, request, logging.INFO, user=user.pk)
    return Response(UserSerializer(user).data)


class CsrfView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses=inline_serializer("Csrf", {"csrf_token": serializers.CharField()}))
    @method_decorator(ensure_csrf_cookie)
    def get(self, request: Request) -> Response:
        return Response({"csrf_token": get_token(request)})


class SignupView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "auth"

    @extend_schema(request=SignupSerializer, responses={201: UserSerializer})
    def post(self, request: Request) -> Response:
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        language = (
            request.LANGUAGE_CODE if request.LANGUAGE_CODE in dict(settings.LANGUAGES) else "en"
        )
        user = User.objects.create_user(
            data["email"], data["password"], name=data.get("name", ""), language=language
        )
        login(request._request, user, backend="django.contrib.auth.backends.ModelBackend")
        security_event("auth.signup", request, logging.INFO, user=user.pk)
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "auth"

    @extend_schema(
        request=LoginSerializer, responses={200: UserSerializer, 202: TwoFactorRequiredSerializer}
    )
    def post(self, request: Request) -> Response:
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].lower()
        user = authenticate(
            request._request, email=email, password=serializer.validated_data["password"]
        )
        if user is None:
            security_event("auth.login_failed", request, account=email_ref(email))
            return Response(
                {"non_field_errors": [_("Invalid email or password.")]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return finish_login(request, user, "auth.login")


class LogoutView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=None, responses={204: None})
    def post(self, request: Request) -> Response:
        logout(request._request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=UserSerializer)
    def get(self, request: Request) -> Response:
        return Response(UserSerializer(current_user(request)).data)

    @extend_schema(request=UserSerializer, responses=UserSerializer)
    def patch(self, request: Request) -> Response:
        serializer = UserSerializer(current_user(request), data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "password_reset"

    @extend_schema(
        request=ForgotPasswordSerializer,
        responses={202: inline_serializer("ForgotPassword", {"detail": serializers.CharField()})},
    )
    def post(self, request: Request) -> Response:
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].lower()
        sent = request_reset(email)
        security_event(
            "auth.reset_requested", request, logging.INFO, account=email_ref(email), sent=sent
        )
        return Response(
            {"detail": _("If an account uses this email, we sent it a code.")},
            status=status.HTTP_202_ACCEPTED,
        )


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "auth"

    @extend_schema(
        request=ResetPasswordSerializer,
        responses={200: UserSerializer, 202: TwoFactorRequiredSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        email = data["email"].lower()
        user = reset_password(email, data["code"], data["password"])
        if user is None:
            security_event("auth.reset_failed", request, account=email_ref(email))
            return Response(
                {"code": [_("That code is wrong or has expired. Ask for a new one.")]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return finish_login(request, user, "auth.reset")


class TwoFactorVerifyView(APIView):
    """The second step of a login that needs a code."""

    permission_classes = [AllowAny]
    throttle_scope = "auth"

    @extend_schema(request=CodeSerializer, responses=UserSerializer)
    def post(self, request: Request) -> Response:
        serializer = CodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = twofactor.verify_pending(request._request, serializer.validated_data["code"])
        if user is None:
            security_event("auth.two_factor_failed", request)
            return Response(
                {"code": [_("That code didn't work. Check your app's clock, or log in again.")]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        login(request._request, user, backend=MODEL_BACKEND)
        security_event("auth.login", request, logging.INFO, user=user.pk, two_factor=True)
        return Response(UserSerializer(user).data)


class TwoFactorView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=TwoFactorStatusSerializer)
    def get(self, request: Request) -> Response:
        user = current_user(request)
        return Response(
            {
                "enabled": twofactor.enabled(user),
                "recovery_codes_left": twofactor.recovery_codes_left(user),
            }
        )


class TwoFactorSetupView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "auth"

    @extend_schema(request=None, responses=TwoFactorSetupSerializer)
    def post(self, request: Request) -> Response:
        user = current_user(request)
        if twofactor.enabled(user):
            return Response(
                {"detail": _("Two-factor sign-in is already on.")}, status=status.HTTP_409_CONFLICT
            )
        setup = twofactor.start_setup(user)
        return Response({"secret": setup.secret, "uri": setup.uri, "qr": setup.qr})


class TwoFactorConfirmView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "auth"

    @extend_schema(request=CodeSerializer, responses=RecoveryCodesSerializer)
    def post(self, request: Request) -> Response:
        serializer = CodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = current_user(request)
        codes = twofactor.confirm(user, serializer.validated_data["code"])
        if codes is None:
            return Response(
                {"code": [_("That code didn't match. Wait for a new one and try again.")]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        security_event("auth.two_factor_on", request, logging.INFO, user=user.pk)
        return Response({"recovery_codes": codes})


class TwoFactorDisableView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "auth"

    @extend_schema(request=DisableTwoFactorSerializer, responses={204: None})
    def post(self, request: Request) -> Response:
        serializer = DisableTwoFactorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = current_user(request)
        values = serializer.validated_data
        if not twofactor.disable(user, values["password"], values["code"]):
            security_event("auth.two_factor_off_failed", request, user=user.pk)
            return Response(
                {"non_field_errors": [_("The password or the code is wrong.")]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        security_event("auth.two_factor_off", request, logging.WARNING, user=user.pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class RecoveryCodesView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "auth"

    @extend_schema(request=CodeSerializer, responses=RecoveryCodesSerializer)
    def post(self, request: Request) -> Response:
        serializer = CodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = current_user(request)
        if not twofactor.verify(user, serializer.validated_data["code"]):
            return Response(
                {"code": [_("That code didn't match. Wait for a new one and try again.")]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"recovery_codes": twofactor.new_recovery_codes(user)})


class SsoProvidersView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses=ProviderSerializer(many=True))
    def get(self, request: Request) -> Response:
        return Response([{"id": p.id, "name": p.name} for p in sso.enabled_providers()])


class IdentitiesView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=IdentitySerializer(many=True))
    def get(self, request: Request) -> Response:
        identities = SocialIdentity.objects.filter(user=current_user(request))
        return Response(IdentitySerializer(identities, many=True).data)


class IdentityView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={204: None})
    def delete(self, request: Request, provider: str) -> Response:
        user = current_user(request)
        identities = SocialIdentity.objects.filter(user=user)
        if not user.has_usable_password() and not identities.exclude(provider=provider).exists():
            return Response(
                {"detail": _("Set a password first, or this account would have no way to log in.")},
                status=status.HTTP_409_CONFLICT,
            )
        deleted, _rows = identities.filter(provider=provider).delete()
        if not deleted:
            return Response(status=status.HTTP_404_NOT_FOUND)
        security_event("auth.sso_unlinked", request, logging.INFO, user=user.pk, provider=provider)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ExportView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "account_data"

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request: Request) -> Response:
        user = current_user(request)
        security_event("account.exported", request, logging.INFO, user=user.pk)
        response = Response(data.export(user))
        response["Content-Disposition"] = 'attachment; filename="holidayops-data.json"'
        return response


class DeleteAccountView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "account_data"

    @extend_schema(request=DeleteAccountSerializer, responses={204: None})
    def post(self, request: Request) -> Response:
        serializer = DeleteAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = current_user(request)
        values = serializer.validated_data
        if values["confirm"].strip().lower() != user.email.lower():
            return Response(
                {"confirm": [_("Type your email address exactly to confirm.")]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if user.has_usable_password() and not user.check_password(values["password"]):
            return Response(
                {"password": [_("That password is wrong.")]}, status=status.HTTP_400_BAD_REQUEST
            )
        blocking = data.blocking_orgs(user)
        if blocking:
            return Response(
                {
                    "detail": _(
                        "Make someone else an owner of %(orgs)s first: they would be left "
                        "without one."
                    )
                    % {"orgs": ", ".join(blocking)}
                },
                status=status.HTTP_409_CONFLICT,
            )
        security_event("account.deleted", request, logging.WARNING, user=user.pk)
        logout(request._request)
        data.delete_account(user)
        return Response(status=status.HTTP_204_NO_CONTENT)
