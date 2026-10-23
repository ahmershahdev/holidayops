from typing import Any

from django.utils.translation import gettext as _
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotAuthenticated, PermissionDenied
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request

from apps.accounts.models import User


def current_user(request: Request) -> User:
    if not isinstance(request.user, User):
        raise NotAuthenticated
    return request.user


def verified_user(request: Request) -> User:
    """The signed-in user, who must have proven their email: anything that reaches other
    people (organizations, invites, digests) waits for that."""
    user = current_user(request)
    if not user.email_verified:
        raise PermissionDenied(_("Confirm your email address first."))
    return user


class CsrfProtected(BasePermission):
    """DRF checks CSRF only for signed-in users, which leaves login, signup and password reset
    open to login CSRF: another site posting the attacker's credentials into your browser."""

    def has_permission(self, request: Request, view: Any) -> bool:
        if request.method not in SAFE_METHODS:
            SessionAuthentication().enforce_csrf(request)
        return True
