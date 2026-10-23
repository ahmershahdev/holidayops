"""One-time codes emailed to prove a mailbox: password reset and email verification.
Docs: docs/security.md, "Password reset" and "Email verification".

A 6-digit code from `secrets`, valid for a short time and once, five guesses at most. Only an
HMAC keyed with SECRET_KEY is stored, so a database leak doesn't hand out live codes."""

import hashlib
import hmac
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.utils import timezone

from apps.accounts import emails, sessions
from apps.accounts.models import EmailCode, User

Purpose = EmailCode.Purpose
TTL = {Purpose.RESET: timedelta(minutes=10), Purpose.VERIFY: timedelta(hours=1)}
MAX_ATTEMPTS = 5
# Emails per address per hour: stops anyone using a form to flood someone's inbox.
PER_EMAIL_PER_HOUR = 3


def new_code() -> str:
    return f"{secrets.randbelow(10**6):06d}"


def code_hash(user_id: int, code: str, purpose: str = Purpose.RESET) -> str:
    key = settings.SECRET_KEY.encode()
    return hmac.new(key, f"{purpose}:{user_id}:{code}".encode(), hashlib.sha256).hexdigest()


def _over_limit(user: User) -> bool:
    """Every email to an address counts, whatever its purpose."""
    now = timezone.now()
    codes = EmailCode.objects.filter(user=user)
    codes.filter(created_at__lt=now - timedelta(days=1)).delete()
    return codes.filter(created_at__gte=now - timedelta(hours=1)).count() >= PER_EMAIL_PER_HOUR


def _issue(user: User, purpose: Purpose) -> str | None:
    if _over_limit(user):
        return None
    now = timezone.now()
    code = new_code()
    with transaction.atomic():
        EmailCode.objects.filter(user=user, purpose=purpose, used_at__isnull=True).update(
            used_at=now
        )
        EmailCode.objects.create(
            user=user,
            purpose=purpose,
            code_hash=code_hash(user.pk, code, purpose),
            expires_at=now + TTL[purpose],
        )
    return code


def _redeem(user: User, purpose: Purpose, code: str) -> bool:
    """Call inside a transaction: the row lock stops two requests using one code."""
    if not (len(code) == 6 and code.isdigit()):
        return False
    record = (
        EmailCode.objects.select_for_update()
        .filter(user=user, purpose=purpose, used_at__isnull=True, expires_at__gt=timezone.now())
        .order_by("-created_at")
        .first()
    )
    if record is None or record.attempts >= MAX_ATTEMPTS:
        return False
    if not hmac.compare_digest(record.code_hash, code_hash(user.pk, code, purpose)):
        record.attempts += 1
        record.save(update_fields=["attempts"])
        return False
    record.used_at = timezone.now()
    record.save(update_fields=["used_at"])
    return True


def _send_code(user: User, purpose: Purpose) -> bool:
    code = _issue(user, purpose)
    if code is None:
        return False
    template, subject = {
        Purpose.RESET: ("reset_code", emails.RESET_SUBJECT),
        Purpose.VERIFY: ("verify_code", emails.VERIFY_SUBJECT),
    }[purpose]
    minutes = int(TTL[purpose].total_seconds() // 60)
    emails.queue(user, template, subject, {"code": code, "minutes": minutes})
    return True


def request_reset(email: str) -> bool:
    """Email a code if the account exists and hasn't hit the hourly limit. The caller answers
    the same way either way, so the form can't tell anyone which addresses have accounts."""
    user = User.objects.filter(email__iexact=email, is_active=True).first()
    return user is not None and _send_code(user, Purpose.RESET)


def reset_password(email: str, code: str, password: str) -> User | None:
    """Set the new password if the code is right; None for any failure, so a caller can't tell
    a wrong code from an expired one or a missing account."""
    user = User.objects.filter(email__iexact=email, is_active=True).first()
    if user is None:
        return None
    with transaction.atomic():
        if not _redeem(user, Purpose.RESET, code):
            return None
        # Changing the password also signs out every other session (their hash no longer
        # matches).
        user.set_password(password)
        # The code reached the mailbox, which is all verification asks for.
        user.email_verified_at = user.email_verified_at or timezone.now()
        user.save(update_fields=["password", "email_verified_at"])
        # A provider account linked on an address nobody checked could belong to whoever made
        # it; proving the mailbox here cuts it loose (see sso.Provider.trusts_email).
        user.identities.filter(email_verified=False).delete()
    sessions.end(user)
    emails.queue(user, "password_changed", emails.CHANGED_SUBJECT)
    return user


def send_verification(user: User) -> bool:
    return not user.email_verified and _send_code(user, Purpose.VERIFY)


def register(email: str, password: str, name: str, language: str) -> str:
    """Sign-up that never says whether the address is taken. Returns what happened, for the
    security log only: created, replaced, exists or limited.

    - New address: an unverified account and a code.
    - Unverified account: nobody has proven it's theirs, so the newest sign-up replaces the
      password and gets a fresh code. Squatting someone's address gains nothing.
    - Verified account: unchanged; the owner is told someone tried, with a way to reset."""
    # Hashed before the lookup so every branch pays for Argon2 and timing stays flat.
    hashed = make_password(password)
    with transaction.atomic():
        user = User.objects.select_for_update().filter(email__iexact=email).first()
        if user is None:
            user = User.objects.create(email=email, name=name, language=language, password=hashed)
            outcome = "created"
        elif not user.email_verified:
            user.password = hashed
            user.name = name or user.name
            user.save(update_fields=["password", "name"])
            outcome = "replaced"
        else:
            outcome = "exists"
    if outcome != "exists":
        return outcome if send_verification(user) else "limited"
    if _over_limit(user):
        return "limited"
    # A spent row, so the note counts against the hourly limit like a code would.
    now = timezone.now()
    EmailCode.objects.create(
        user=user, purpose=Purpose.VERIFY, code_hash="", expires_at=now, used_at=now
    )
    emails.queue(user, "account_exists", emails.EXISTS_SUBJECT)
    return outcome


def verify_email(email: str, code: str) -> User | None:
    user = User.objects.filter(email__iexact=email, is_active=True).first()
    if user is None or user.email_verified:
        return None
    with transaction.atomic():
        if not _redeem(user, Purpose.VERIFY, code):
            return None
        user.email_verified_at = timezone.now()
        user.save(update_fields=["email_verified_at"])
    emails.queue(user, "welcome", emails.WELCOME_SUBJECT)
    return user


def prune_unverified(days: int = 7) -> int:
    """Delete sign-ups never confirmed: nobody owns them, and they hold the address hostage."""
    stale = User.objects.filter(
        email_verified_at__isnull=True,
        date_joined__lt=timezone.now() - timedelta(days=days),
        identities__isnull=True,
        memberships__isnull=True,
    )
    ids = list(stale.values_list("pk", flat=True))
    User.objects.filter(pk__in=ids).delete()
    return len(ids)
