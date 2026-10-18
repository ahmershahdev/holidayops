"""Time-based one-time passwords for authenticator apps (RFC 6238, built on RFC 4226 HOTP).
SHA-1, 6 digits, 30-second steps: the defaults every authenticator app understands."""

import base64
import hashlib
import hmac
import secrets
import struct
from urllib.parse import quote, urlencode

STEP_SECONDS = 30
DIGITS = 6
ISSUER = "HolidayOps"


def new_secret() -> str:
    # 160 bits, the size RFC 4226 recommends for HMAC-SHA1.
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def _key(secret: str) -> bytes:
    return base64.b32decode(secret + "=" * (-len(secret) % 8))


def code_at(secret: str, step: int) -> str:
    digest = hmac.new(_key(secret), struct.pack(">Q", step), hashlib.sha1).digest()
    # RFC 4226 5.3: dynamic truncation.
    offset = digest[-1] & 0x0F
    number = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return f"{number % 10**DIGITS:0{DIGITS}d}"


def matching_step(secret: str, code: str, now: float, last_step: int) -> int | None:
    """The step the code belongs to, allowing one step of clock drift either way. Steps at or
    before `last_step` are refused, so a code seen over someone's shoulder can't be replayed."""
    current = int(now // STEP_SECONDS)
    for step in (current - 1, current, current + 1):
        if step > last_step and hmac.compare_digest(code_at(secret, step), code):
            return step
    return None


def provisioning_uri(secret: str, account: str) -> str:
    """The otpauth:// link a QR code carries (Google Authenticator key URI format)."""
    query = urlencode({"secret": secret, "issuer": ISSUER, "digits": DIGITS})
    return f"otpauth://totp/{quote(ISSUER)}:{quote(account)}?{query}"
