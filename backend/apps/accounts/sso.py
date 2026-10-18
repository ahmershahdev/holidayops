"""Sign in with Google or Microsoft: OpenID Connect authorization code flow with PKCE.
Docs: docs/security.md, "Single sign-on".

The ID token comes straight from the provider's token endpoint over TLS, which OpenID Connect
Core 3.1.3.7 accepts in place of checking its signature; issuer, audience, expiry and nonce are
still checked. Accounts are matched by the provider's stable subject id, never by email alone."""

import base64
import hashlib
import json
import re
import secrets
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from django.conf import settings

TIMEOUT = 10
FLOW_SECONDS = 600


@dataclass(frozen=True)
class Provider:
    id: str
    name: str
    authorize_url: str
    token_url: str
    issuer: re.Pattern[str]
    # Only Google says whether it checked the address; Microsoft's email claim is whatever the
    # tenant admin typed (the "nOAuth" problem), so it never links an existing account.
    trusts_email: bool


PROVIDERS = {
    "google": Provider(
        "google",
        "Google",
        "https://accounts.google.com/o/oauth2/v2/auth",
        "https://oauth2.googleapis.com/token",
        re.compile(r"^(https://)?accounts\.google\.com$"),
        trusts_email=True,
    ),
    "microsoft": Provider(
        "microsoft",
        "Microsoft",
        "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        re.compile(r"^https://login\.microsoftonline\.com/[0-9a-f-]{36}/v2\.0$"),
        trusts_email=False,
    ),
}


@dataclass(frozen=True)
class Claims:
    subject: str
    email: str
    email_verified: bool
    name: str


class SsoError(Exception):
    pass


def credentials(provider: str) -> tuple[str, str] | None:
    client_id, secret = settings.SSO_CLIENTS.get(provider, ("", ""))
    return (client_id, secret) if client_id and secret else None


def enabled_providers() -> list[Provider]:
    return [p for p in PROVIDERS.values() if credentials(p.id)]


def redirect_uri(provider: str) -> str:
    return f"{settings.APP_URL}/sso/{provider}/callback/"


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def begin(
    provider: Provider, client_id: str, next_path: str, link_user: int | None
) -> tuple[str, dict[str, Any]]:
    """The provider URL to send the browser to, and the flow state to keep in the session."""
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    query = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri(provider.id),
            "scope": "openid email profile",
            "state": state,
            "nonce": nonce,
            "code_challenge": _b64url(hashlib.sha256(verifier.encode()).digest()),
            "code_challenge_method": "S256",
            "prompt": "select_account",
        }
    )
    flow = {
        "provider": provider.id,
        "state": state,
        "nonce": nonce,
        "verifier": verifier,
        "next": next_path,
        "link": link_user,
        "at": time.time(),
    }
    return f"{provider.authorize_url}?{query}", flow


def _decode_payload(id_token: str) -> dict[str, Any]:
    try:
        payload = id_token.split(".")[1]
        data: dict[str, Any] = json.loads(
            base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))
        )
    except (IndexError, ValueError) as error:
        raise SsoError("malformed id_token") from error
    return data


def exchange(provider: Provider, flow: dict[str, Any], code: str) -> dict[str, Any]:
    client_id, secret = credentials(provider.id) or ("", "")
    body = urllib.parse.urlencode(
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri(provider.id),
            "client_id": client_id,
            "client_secret": secret,
            "code_verifier": flow["verifier"],
        }
    ).encode()
    request = urllib.request.Request(  # noqa: S310 - fixed https URL from PROVIDERS
        provider.token_url,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:  # noqa: S310
            tokens: dict[str, Any] = json.loads(response.read())
    except (OSError, ValueError) as error:
        raise SsoError("token exchange failed") from error
    if "id_token" not in tokens:
        raise SsoError("no id_token")
    return _decode_payload(tokens["id_token"])


def validate(provider: Provider, claims: dict[str, Any], nonce: str, now: float) -> Claims:
    client_id, _secret = credentials(provider.id) or ("", "")
    audience = claims.get("aud")
    audiences = audience if isinstance(audience, list) else [audience]
    checks = (
        provider.issuer.match(str(claims.get("iss", ""))),
        client_id in audiences,
        float(claims.get("exp", 0)) > now,
        float(claims.get("iat", now)) <= now + 300,
        secrets.compare_digest(str(claims.get("nonce", "")), nonce),
        bool(claims.get("sub")),
    )
    if not all(checks):
        raise SsoError("id_token rejected")
    email = str(claims.get("email") or claims.get("preferred_username") or "").lower()
    verified = provider.trusts_email and claims.get("email_verified") is True
    return Claims(str(claims["sub"]), email, verified, str(claims.get("name") or ""))
