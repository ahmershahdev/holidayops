"""Security events (failed logins, bad API keys, rate limits) on the `holidayops.security` logger.

Never pass passwords, tokens, keys or raw emails: emails go through `email_ref`."""

import hashlib
import logging
import re
from typing import Any

from rest_framework.throttling import BaseThrottle

logger = logging.getLogger("holidayops.security")

_UNSAFE = re.compile(r"[^\w.:@/-]")


def client_ip(request: Any) -> str:
    """The address the throttles count, so logs and limits agree (honours NUM_PROXIES)."""
    return str(BaseThrottle().get_ident(request))


def email_ref(email: str) -> str:
    """Enough to tell repeated attempts on one account apart without storing the address."""
    return hashlib.sha256(email.strip().lower().encode()).hexdigest()[:12]


def _clean(value: object) -> str:
    return _UNSAFE.sub("_", str(value))[:80]


def security_event(
    event: str, request: Any, level: int = logging.WARNING, **fields: object
) -> None:
    parts = {"ip": client_ip(request), "path": request.path, **fields}
    text = " ".join(f"{key}={_clean(value)}" for key, value in parts.items())
    logger.log(level, "%s %s", event, text, extra={"event": event})
