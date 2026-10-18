from typing import Any

from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotAuthenticated
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request

from apps.accounts.models import User


def current_user(request: Request) -> User:
    if not isinstance(request.user, User):
        raise NotAuthenticated
    return request.user


class CsrfProtected(BasePermission):
    """DRF checks CSRF only for signed-in users, which leaves login, signup and password reset
    open to login CSRF: another site posting the attacker's credentials into your browser."""

    def has_permission(self, request: Request, view: Any) -> bool:
        if request.method not in SAFE_METHODS:
            SessionAuthentication().enforce_csrf(request)
        return True
