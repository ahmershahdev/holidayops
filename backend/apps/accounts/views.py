import logging
from typing import Any

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.core.cache import cache
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.decorators.csrf import ensure_csrf_cookie
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import PolymorphicProxySerializer, extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import BaseThrottle
from rest_framework.views import APIView

from apps.accounts import captcha, codes, data, emails, sessions, sso, twofactor
from apps.accounts.auth import CsrfProtected, current_user
from apps.accounts.models import SocialIdentity, User
from apps.accounts.serializers import (
    CaptchaKeysSerializer,
    CheckEmailSerializer,
    CodeSerializer,
    DeleteAccountSerializer,
    DisableTwoFactorSerializer,
    ForgotPasswordSerializer,
    IdentitySerializer,
    LoginSerializer,
    ProviderSerializer,
    RecoveryCodesSerializer,
    ResetPasswordSerializer,
    SessionSerializer,
    SignupSerializer,
    TwoFactorRequiredSerializer,
    TwoFactorSetupSerializer,
    TwoFactorStatusSerializer,
    UserSerializer,
    VerifyEmailSerializer,
)
from config.security_log import email_ref, security_event

MODEL_BACKEND = "django.contrib.auth.backends.ModelBackend"
ACCOUNT_LOGIN_FAILURES = 10
ACCOUNT_LOGIN_WINDOW = 15 * 60


def check_email_response() -> Response:
    return Response(
        {
            "detail": _("Check your email: if the address can be used, we sent it a code."),
            "verification_required": True,
        },
        status=status.HTTP_202_ACCEPTED,
    )


def bot_check(request: Request, action: str) -> Response | None:
    """None when the request may go on; otherwise the answer to send. A 400 with
    `captcha: "v2"` tells the page to show the checkbox."""
    result = captcha.check(request.data, action, BaseThrottle().get_ident(request))
    if result == "ok":
        return None
    security_event(f"auth.captcha_{result}", request, action=action)
    if captcha.site_keys()["v2"]:
        body = {
            "detail": _("Tick the box to show you're not a robot, then try again."),
            "captcha": "v2",
        }
    else:
        body = {"detail": _("We couldn't check that you're a person. Try again in a minute.")}
    return Response(body, status=status.HTTP_400_BAD_REQUEST)


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


class CaptchaKeysView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses=CaptchaKeysSerializer)
    def get(self, request: Request) -> Response:
        return Response(captcha.site_keys())


class SignupView(APIView):
    """Never signs in and never says whether the address is taken: the account starts once the
    emailed code comes back to VerifyEmailView."""

    permission_classes = [AllowAny, CsrfProtected]
    throttle_scope = "auth"

    @extend_schema(request=SignupSerializer, responses={202: CheckEmailSerializer})
    def post(self, request: Request) -> Response:
        if captcha.is_bot(request.data):
            security_event("auth.honeypot", request, action="signup")
            return check_email_response()
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if blocked := bot_check(request, "signup"):
            return blocked
        values = serializer.validated_data
        language = (
            request.LANGUAGE_CODE if request.LANGUAGE_CODE in dict(settings.LANGUAGES) else "en"
        )
        outcome = codes.register(
            values["email"], values["password"], values.get("name", ""), language
        )
        account = email_ref(values["email"])
        security_event("auth.signup", request, logging.INFO, account=account, outcome=outcome)
        return check_email_response()


class VerifyEmailView(APIView):
    permission_classes = [AllowAny, CsrfProtected]
    throttle_scope = "auth"

    @extend_schema(
        request=VerifyEmailSerializer,
        responses={200: UserSerializer, 202: TwoFactorRequiredSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].lower()
        user = codes.verify_email(email, serializer.validated_data["code"])
        if user is None:
            security_event("auth.verify_failed", request, account=email_ref(email))
            return Response(
                {"code": [_("That code is wrong or has expired. Ask for a new one.")]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return finish_login(request, user, "auth.verified")


class ResendVerificationView(APIView):
    permission_classes = [AllowAny, CsrfProtected]
    throttle_scope = "password_reset"

    @extend_schema(request=ForgotPasswordSerializer, responses={202: CheckEmailSerializer})
    def post(self, request: Request) -> Response:
        if captcha.is_bot(request.data):
            security_event("auth.honeypot", request, action="verify")
            return check_email_response()
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].lower()
        # A signed-in account asking for its own code has already passed a check to get here.
        own = request.user.is_authenticated and request.user.email.lower() == email
        if not own and (blocked := bot_check(request, "verify")):
            return blocked
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        sent = user is not None and codes.send_verification(user)
        security_event(
            "auth.verify_requested", request, logging.INFO, account=email_ref(email), sent=sent
        )
        return check_email_response()


class LoginView(APIView):
    permission_classes = [AllowAny, CsrfProtected]
    throttle_scope = "auth"

    @extend_schema(
        request=LoginSerializer,
        responses={
            200: UserSerializer,
            202: PolymorphicProxySerializer(
                "LoginPending",
                [TwoFactorRequiredSerializer, CheckEmailSerializer],
                resource_type_field_name=None,
            ),
        },
    )
    def post(self, request: Request) -> Response:
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].lower()
        # Per account as well as per IP: a botnet spreads guesses over many addresses.
        failures = f"login-failures:{email_ref(email)}"
        if (cache.get(failures) or 0) >= ACCOUNT_LOGIN_FAILURES:
            security_event("rate_limited", request, scope="account", account=email_ref(email))
            return Response(
                {
                    "detail": _(
                        "Too many attempts for this account. Wait 15 minutes, or reset the "
                        "password."
                    )
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        user = authenticate(
            request._request, email=email, password=serializer.validated_data["password"]
        )
        if user is None:
            cache.add(failures, 0, timeout=ACCOUNT_LOGIN_WINDOW)
            cache.incr(failures)
            security_event("auth.login_failed", request, account=email_ref(email))
            return Response(
                {"non_field_errors": [_("Invalid email or password.")]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        cache.delete(failures)
        if not user.email_verified:
            # The password is right, so this is whoever signed up: send them a code.
            sent = codes.send_verification(user)
            security_event("auth.login_unverified", request, user=user.pk, sent=sent)
            return check_email_response()
        return finish_login(request, user, "auth.login")


class LogoutView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=None, responses={204: None})
    def post(self, request: Request) -> Response:
        logout(request._request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    def get_permissions(self) -> list[Any]:
        # Asking "who am I?" while signed out is normal, not an error for the browser to log.
        return [AllowAny()] if self.request.method == "GET" else [IsAuthenticated()]

    @extend_schema(responses={200: UserSerializer, 204: None})
    def get(self, request: Request) -> Response:
        if not request.user.is_authenticated:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(UserSerializer(current_user(request)).data)

    @extend_schema(request=UserSerializer, responses=UserSerializer)
    def patch(self, request: Request) -> Response:
        serializer = UserSerializer(current_user(request), data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny, CsrfProtected]
    throttle_scope = "password_reset"

    @extend_schema(
        request=ForgotPasswordSerializer,
        responses={202: inline_serializer("ForgotPassword", {"detail": serializers.CharField()})},
    )
    def post(self, request: Request) -> Response:
        sent_answer = Response(
            {"detail": _("If an account uses this email, we sent it a code.")},
            status=status.HTTP_202_ACCEPTED,
        )
        if captcha.is_bot(request.data):
            security_event("auth.honeypot", request, action="reset")
            return sent_answer
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if blocked := bot_check(request, "reset"):
            return blocked
        email = serializer.validated_data["email"].lower()
        sent = codes.request_reset(email)
        security_event(
            "auth.reset_requested", request, logging.INFO, account=email_ref(email), sent=sent
        )
        return sent_answer


class ResetPasswordView(APIView):
    permission_classes = [AllowAny, CsrfProtected]
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
        user = codes.reset_password(email, data["code"], data["password"])
        if user is None:
            security_event("auth.reset_failed", request, account=email_ref(email))
            return Response(
                {"code": [_("That code is wrong or has expired. Ask for a new one.")]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return finish_login(request, user, "auth.reset")


class TwoFactorVerifyView(APIView):
    """The second step of a login that needs a code."""

    permission_classes = [AllowAny, CsrfProtected]
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
        emails.notify(user, "two_factor_on")
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
        emails.notify(user, "two_factor_off")
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
        recovery = twofactor.new_recovery_codes(user)
        emails.notify(user, "recovery_codes")
        return Response({"recovery_codes": recovery})


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
        emails.notify(user, "sso_unlinked")
        return Response(status=status.HTTP_204_NO_CONTENT)


class SessionsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=SessionSerializer(many=True))
    def get(self, request: Request) -> Response:
        current = request.session.session_key
        rows = []
        for row in sessions.active(current_user(request)):
            browser, system = sessions.describe(row.user_agent)
            rows.append(
                {
                    "id": row.pk,
                    "created_at": row.created_at,
                    "last_seen_at": row.last_seen_at,
                    "ip": row.ip,
                    "browser": browser,
                    "system": system,
                    "current": row.session_key == current,
                }
            )
        return Response(SessionSerializer(rows, many=True).data)


class EndOtherSessionsView(APIView):
    """Sign out every device but this one."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None,
        responses=inline_serializer("EndedSessions", {"ended": serializers.IntegerField()}),
    )
    def post(self, request: Request) -> Response:
        user = current_user(request)
        ended = sessions.end(user, keep=request.session.session_key)
        security_event("auth.sessions_ended", request, logging.INFO, user=user.pk, ended=ended)
        return Response({"ended": ended})


class SessionView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={204: None})
    def delete(self, request: Request, session_id: int) -> Response:
        user = current_user(request)
        # The current session ends through logout, which also clears its cookie.
        if not sessions.end(user, keep=request.session.session_key, only=session_id):
            return Response(status=status.HTTP_404_NOT_FOUND)
        security_event("auth.session_ended", request, logging.INFO, user=user.pk)
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
        emails.notify_now(user, "account_deleted")
        data.delete_account(user)
        return Response(status=status.HTTP_204_NO_CONTENT)
