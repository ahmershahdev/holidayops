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
from apps.accounts.serializers import LoginSerializer, SignupSerializer, UserSerializer


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
        user = User.objects.create_user(data["email"], data["password"], name=data.get("name", ""))
        login(request._request, user, backend="django.contrib.auth.backends.ModelBackend")
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "auth"

    @extend_schema(request=LoginSerializer, responses=UserSerializer)
    def post(self, request: Request) -> Response:
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request._request,
            email=serializer.validated_data["email"].lower(),
            password=serializer.validated_data["password"],
        )
        if user is None:
            return Response(
                {"non_field_errors": [_("Invalid email or password.")]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        login(request._request, user)
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
