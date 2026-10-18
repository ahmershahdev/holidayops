"""Password reset by emailed code. Docs: docs/security.md, "Password reset".

A 6-digit code from `secrets`, valid for 10 minutes and once, five guesses at most. Only an HMAC
keyed with SECRET_KEY is stored, so a database leak doesn't hand out live codes."""

import hashlib
import hmac
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone, translation
from django.utils.translation import gettext as _
from django.utils.translation import gettext_noop

from apps.accounts.models import PasswordResetCode, User
from apps.public.seo import SUPPORT_EMAIL

CODE_TTL = timedelta(minutes=10)
MAX_ATTEMPTS = 5
# Codes per address per hour: stops anyone using the form to flood someone's inbox.
PER_EMAIL_PER_HOUR = 3
RTL = {"ur", "ar"}
CODE_SUBJECT = gettext_noop("Your HolidayOps password reset code")
CHANGED_SUBJECT = gettext_noop("Your HolidayOps password was changed")


def new_code() -> str:
    return f"{secrets.randbelow(10**6):06d}"


def code_hash(user_id: int, code: str) -> str:
    key = settings.SECRET_KEY.encode()
    return hmac.new(key, f"reset:{user_id}:{code}".encode(), hashlib.sha256).hexdigest()


def _send(user: User, template: str, subject: str, context: dict[str, object]) -> None:
    language = user.language
    context = {**context, "language": language, "dir": "rtl" if language in RTL else "ltr"}
    with translation.override(language):
        text = render_to_string(f"accounts/{template}.txt", context)
        html = render_to_string(f"accounts/{template}.html", context)
        message = EmailMultiAlternatives(_(subject), text, to=[user.email])
    message.attach_alternative(html, "text/html")
    message.send()


def request_reset(email: str) -> bool:
    """Email a code if the account exists and hasn't hit the hourly limit. The caller answers
    the same way either way, so the form can't tell anyone which addresses have accounts."""
    user = User.objects.filter(email__iexact=email, is_active=True).first()
    if user is None:
        return False
    now = timezone.now()
    codes = PasswordResetCode.objects.filter(user=user)
    codes.filter(created_at__lt=now - timedelta(days=1)).delete()
    if codes.filter(created_at__gte=now - timedelta(hours=1)).count() >= PER_EMAIL_PER_HOUR:
        return False
    code = new_code()
    with transaction.atomic():
        codes.filter(used_at__isnull=True).update(used_at=now)
        PasswordResetCode.objects.create(
            user=user, code_hash=code_hash(user.pk, code), expires_at=now + CODE_TTL
        )
    _send(
        user,
        "reset_code",
        CODE_SUBJECT,
        {"code": code, "minutes": int(CODE_TTL.total_seconds() // 60)},
    )
    return True


def reset_password(email: str, code: str, password: str) -> User | None:
    """Set the new password if the code is right; None for any failure, so a caller can't tell
    a wrong code from an expired one or a missing account."""
    user = User.objects.filter(email__iexact=email, is_active=True).first()
    if user is None or not (len(code) == 6 and code.isdigit()):
        return None
    with transaction.atomic():
        # Locked, so two requests with the right code can't both use it.
        reset = (
            PasswordResetCode.objects.select_for_update()
            .filter(user=user, used_at__isnull=True, expires_at__gt=timezone.now())
            .order_by("-created_at")
            .first()
        )
        if reset is None or reset.attempts >= MAX_ATTEMPTS:
            return None
        if not hmac.compare_digest(reset.code_hash, code_hash(user.pk, code)):
            reset.attempts += 1
            reset.save(update_fields=["attempts"])
            return None
        reset.used_at = timezone.now()
        reset.save(update_fields=["used_at"])
        # Changing the password also signs out every other session (their hash no longer
        # matches).
        user.set_password(password)
        user.save(update_fields=["password"])
    _send(user, "password_changed", CHANGED_SUBJECT, {"support": SUPPORT_EMAIL})
    return user
