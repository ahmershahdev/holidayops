"""Two-factor sign-in with an authenticator app, plus single-use recovery codes.
Docs: docs/security.md, "Two-factor sign-in"."""

import base64
import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass

import segno
from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone

from apps.accounts import totp
from apps.accounts.models import RecoveryCode, TwoFactor, User

RECOVERY_CODES = 10
# Ambiguous characters (0/o, 1/l/i) left out: these get copied by hand.
_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"
PENDING = "two_factor_pending"
PENDING_SECONDS = 300
PENDING_TRIES = 5


@dataclass(frozen=True)
class Setup:
    secret: str
    uri: str
    qr: str


def enabled(user: User) -> bool:
    return TwoFactor.objects.filter(user=user, confirmed_at__isnull=False).exists()


def _recovery_hash(user_id: int, code: str) -> str:
    key = settings.SECRET_KEY.encode()
    normalised = code.replace("-", "").replace(" ", "").lower()
    return hmac.new(key, f"recovery:{user_id}:{normalised}".encode(), hashlib.sha256).hexdigest()


def _new_recovery_code() -> str:
    raw = "".join(secrets.choice(_ALPHABET) for _ in range(10))
    return f"{raw[:5]}-{raw[5:]}"


def new_recovery_codes(user: User) -> list[str]:
    """Replace every recovery code; the plain codes are shown once and never stored."""
    codes = [_new_recovery_code() for _ in range(RECOVERY_CODES)]
    with transaction.atomic():
        RecoveryCode.objects.filter(user=user).delete()
        RecoveryCode.objects.bulk_create(
            RecoveryCode(user=user, code_hash=_recovery_hash(user.pk, code)) for code in codes
        )
    return codes


def start_setup(user: User) -> Setup:
    """A fresh, unconfirmed secret. Calling it again replaces an unconfirmed one; a confirmed
    one has to be disabled first."""
    secret = totp.new_secret()
    TwoFactor.objects.update_or_create(
        user=user, defaults={"secret": secret, "confirmed_at": None, "last_step": 0}
    )
    uri = totp.provisioning_uri(secret, user.email)
    svg = segno.make(uri, error="m").svg_inline(scale=5, border=2, dark="#0b1b3f")
    qr = "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()
    return Setup(secret, uri, qr)


def _check_totp(device: TwoFactor, code: str) -> bool:
    step = totp.matching_step(device.secret, code, time.time(), device.last_step)
    if step is None:
        return False
    device.last_step = step
    device.save(update_fields=["last_step"])
    return True


def confirm(user: User, code: str) -> list[str] | None:
    with transaction.atomic():
        device = (
            TwoFactor.objects.select_for_update()
            .filter(user=user, confirmed_at__isnull=True)
            .first()
        )
        if device is None or not _check_totp(device, code):
            return None
        device.confirmed_at = timezone.now()
        device.save(update_fields=["confirmed_at"])
    return new_recovery_codes(user)


def verify(user: User, code: str) -> bool:
    """An app code, or an unused recovery code (which is then spent)."""
    code = code.strip()
    with transaction.atomic():
        device = (
            TwoFactor.objects.select_for_update()
            .filter(user=user, confirmed_at__isnull=False)
            .first()
        )
        if device is None:
            return False
        if len(code) == totp.DIGITS and code.isdigit():
            return _check_totp(device, code)
        recovery = (
            RecoveryCode.objects.select_for_update()
            .filter(user=user, used_at__isnull=True, code_hash=_recovery_hash(user.pk, code))
            .first()
        )
        if recovery is None:
            return False
        recovery.used_at = timezone.now()
        recovery.save(update_fields=["used_at"])
        return True


def disable(user: User, password: str, code: str) -> bool:
    if user.has_usable_password() and not check_password(password, user.password):
        return False
    if not verify(user, code):
        return False
    TwoFactor.objects.filter(user=user).delete()
    RecoveryCode.objects.filter(user=user).delete()
    return True


def recovery_codes_left(user: User) -> int:
    return RecoveryCode.objects.filter(user=user, used_at__isnull=True).count()


# The password (or SSO) step passed, the code step hasn't: the session remembers who, briefly.
def start_pending(request: HttpRequest, user: User) -> None:
    request.session[PENDING] = {"user": user.pk, "at": time.time(), "tries": 0}


def pending_user(request: HttpRequest) -> User | None:
    pending = request.session.get(PENDING)
    if not pending or time.time() - pending["at"] > PENDING_SECONDS:
        request.session.pop(PENDING, None)
        return None
    return User.objects.filter(pk=pending["user"], is_active=True).first()


def verify_pending(request: HttpRequest, code: str) -> User | None:
    user = pending_user(request)
    if user is None:
        return None
    pending = request.session[PENDING]
    if pending["tries"] >= PENDING_TRIES:
        request.session.pop(PENDING, None)
        return None
    if not verify(user, code):
        pending["tries"] += 1
        request.session[PENDING] = pending
        return None
    request.session.pop(PENDING, None)
    return user
