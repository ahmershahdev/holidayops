import hmac
from typing import Any

from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
from django.utils.translation import gettext as _
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request

from apps.api.models import KEY_PREFIX, ApiKey, hash_key
from apps.api.usage import mark_used


class ApiKeyAuthentication(BaseAuthentication):
    """`Authorization: Bearer hops_<prefix>_<secret>`. The request stays anonymous; the key is
    `request.auth`, and it speaks for its org."""

    def authenticate(self, request: Request) -> tuple[AnonymousUser, ApiKey] | None:
        scheme, _sep, key = get_authorization_header(request).decode("latin-1").partition(" ")
        if scheme.lower() != "bearer" or not key.startswith(f"{KEY_PREFIX}_"):
            return None
        parts = key.strip().split("_", 2)
        api_key = None
        if len(parts) == 3:
            api_key = (
                ApiKey.objects.select_related("org")
                .filter(prefix=parts[1], revoked_at__isnull=True)
                .first()
            )
        if api_key is None or not hmac.compare_digest(api_key.key_hash, hash_key(key.strip())):
            raise AuthenticationFailed(_("Invalid or revoked API key."))
        mark_used(api_key, timezone.now())
        return AnonymousUser(), api_key

    def authenticate_header(self, request: Request) -> str:
        return "Bearer"


class ApiKeyScheme(OpenApiAuthenticationExtension):  # type: ignore[no-untyped-call]
    target_class = "apps.api.authentication.ApiKeyAuthentication"
    name = "apiKey"

    def get_security_definition(self, auto_schema: Any) -> dict[str, str]:
        return {"type": "http", "scheme": "bearer", "bearerFormat": "hops_<prefix>_<secret>"}
