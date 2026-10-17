"""Count-then-create limits (API keys, invites, webhooks, feed links) without a race."""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from django.db import connection, transaction
from django.db.models import QuerySet
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError

LOCK_TIMEOUT = 10


class LimitBusy(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = _("Another change is in progress. Try again.")
    default_code = "busy"


def _count(queryset: QuerySet[Any]) -> int:
    return queryset.count()


# A MySQL named lock rather than SELECT ... FOR UPDATE on the parent row: InnoDB takes a shared
# lock on the parent for every child insert, so locking the org row would stall API usage
# records and audit rows for the whole org while an invite email is being sent.
@contextmanager
def within_limit(
    name: str, owner_id: object, queryset: QuerySet[Any], limit: int, message: str
) -> Iterator[None]:
    """Hold `name` for this owner, fail with `message` if `queryset` is at `limit`, else run
    the body in one transaction. The count runs after the lock, so concurrent requests queue."""
    key = f"hops:{name}:{owner_id}"
    with connection.cursor() as cursor:
        cursor.execute("SELECT GET_LOCK(%s, %s)", [key, LOCK_TIMEOUT])
        row = cursor.fetchone()
    if not row or row[0] != 1:
        raise LimitBusy
    try:
        with transaction.atomic():
            if _count(queryset) >= limit:
                raise ValidationError(message)
            yield
    finally:
        with connection.cursor() as cursor:
            cursor.execute("SELECT RELEASE_LOCK(%s)", [key])
