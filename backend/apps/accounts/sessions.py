"""Signed-in devices: one UserSession row per Django session, so a user can see where they are
signed in and sign the others out. Docs: docs/security.md, "Signed-in devices".

Django's session table can't be searched by user, hence the extra row, keyed by session_key."""

import re
from collections.abc import Callable
from typing import Any

from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.db import transaction
from django.dispatch import receiver
from django.http import HttpRequest, HttpResponse
from django.utils import timezone

from apps.accounts.models import User, UserSession
from config.security_log import client_ip

# last_seen_at is written at most this often per session, so browsing costs no extra queries.
TOUCH_SECONDS = 300

_BROWSERS = (("Edg/", "Edge"), ("OPR/", "Opera"), ("Firefox/", "Firefox"), ("Chrome/", "Chrome"))
_SYSTEMS = (
    ("Windows", "Windows"),
    ("Android", "Android"),
    ("iPhone", "iOS"),
    ("iPad", "iPadOS"),
    ("Mac OS X", "macOS"),
    ("CrOS", "ChromeOS"),
    ("Linux", "Linux"),
)


def describe(user_agent: str) -> tuple[str, str]:
    """A rough (browser, system) from the User-Agent, for people to recognise their devices."""
    browser = next((name for token, name in _BROWSERS if token in user_agent), "")
    if not browser and re.search(r"Version/[\d.]+ .*Safari/", user_agent):
        browser = "Safari"
    system = next((name for token, name in _SYSTEMS if token in user_agent), "")
    return browser, system


def _record(request: HttpRequest, user: User) -> None:
    key = request.session.session_key
    if not key:
        return
    UserSession.objects.update_or_create(
        session_key=key,
        defaults={
            "user": user,
            "ip": client_ip(request),
            "user_agent": request.META.get("HTTP_USER_AGENT", "")[:300],
            "last_seen_at": timezone.now(),
        },
    )


@receiver(user_logged_in)
def _on_login(sender: Any, request: HttpRequest | None, user: User, **kwargs: Any) -> None:
    if request is not None and hasattr(request, "session"):
        _record(request, user)


@receiver(user_logged_out)
def _on_logout(sender: Any, request: HttpRequest | None, **kwargs: Any) -> None:
    key = getattr(getattr(request, "session", None), "session_key", None)
    if key:
        UserSession.objects.filter(session_key=key).delete()


class TouchSessionMiddleware:
    """Keeps last_seen_at roughly current. Goes after AuthenticationMiddleware."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        user = getattr(request, "user", None)
        key = request.session.session_key if hasattr(request, "session") else None
        if (
            isinstance(user, User)
            and key
            and cache.add(f"session-seen:{key}", 1, timeout=TOUCH_SECONDS)
        ):
            _record(request, user)
        return response


def active(user: User) -> list[UserSession]:
    """Sessions that still sign someone in; rows of expired or deleted ones are dropped."""
    rows = list(UserSession.objects.filter(user=user).order_by("-last_seen_at"))
    live = set(
        Session.objects.filter(
            session_key__in=[r.session_key for r in rows], expire_date__gt=timezone.now()
        ).values_list("session_key", flat=True)
    )
    dead = [r.pk for r in rows if r.session_key not in live]
    if dead:
        UserSession.objects.filter(pk__in=dead).delete()
    return [r for r in rows if r.session_key in live]


def end(user: User, keep: str | None = None, only: int | None = None) -> int:
    """Sign out the user's sessions: all but `keep`, or just the row `only`."""
    rows = UserSession.objects.filter(user=user)
    if keep:
        rows = rows.exclude(session_key=keep)
    if only is not None:
        rows = rows.filter(pk=only)
    keys = list(rows.values_list("session_key", flat=True))
    with transaction.atomic():
        Session.objects.filter(session_key__in=keys).delete()
        rows.delete()
    for key in keys:
        cache.delete(f"session-seen:{key}")
    return len(keys)
