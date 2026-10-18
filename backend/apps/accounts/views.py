import logging

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.decorators.csrf import ensure_csrf_cookie
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.auth import current_user
from apps.accounts.models import User
from apps.accounts.resets import request_reset, reset_password
from apps.accounts.serializers import (
    ForgotPasswordSerializer,
    LoginSerializer,
    ResetPasswordSerializer,
    SignupSerializer,
    UserSerializer,
)
from config.security_log import email_ref, security_event


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

    @extend_schema(request=LoginSerializer, responses=UserSerializer)
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
        login(request._request, user)
        security_event("auth.login", request, logging.INFO, user=user.pk)
        return Response(UserSerializer(user).data)


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

    @extend_schema(request=ResetPasswordSerializer, responses=UserSerializer)
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
        login(request._request, user, backend="django.contrib.auth.backends.ModelBackend")
        security_event("auth.reset", request, logging.INFO, user=user.pk)
        return Response(UserSerializer(user).data)
