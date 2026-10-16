from rest_framework.exceptions import NotAuthenticated
from rest_framework.request import Request

from apps.accounts.models import User


def current_user(request: Request) -> User:
    if not isinstance(request.user, User):
        raise NotAuthenticated
    return request.user
