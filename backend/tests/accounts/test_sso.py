import base64
import json
import time
from typing import Any
from unittest import mock
from urllib.parse import parse_qs, urlparse

import pytest
from django.test import Client

from apps.accounts import sso
from apps.accounts.models import SocialIdentity, User
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db
TENANT = "9188040d-6c67-4c5b-b112-36a304b66dad"


@pytest.fixture(autouse=True)
def providers(settings: Any) -> None:
    settings.SSO_CLIENTS = {"google": ("g-id", "g-secret"), "microsoft": ("m-id", "m-secret")}
    settings.APP_URL = "http://testserver"


def id_token(claims: dict[str, Any]) -> str:
    body = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
    return f"header.{body}.signature"


def sign_in(client: Client, provider: str, claims: dict[str, Any], next_path: str = "/app") -> Any:
    start = client.get(f"/sso/{provider}/start/?next={next_path}")
    assert start.status_code == 302
    query = parse_qs(urlparse(start["Location"]).query)
    assert query["code_challenge_method"] == ["S256"]
    full = {
        "iss": "https://accounts.google.com"
        if provider == "google"
        else f"https://login.microsoftonline.com/{TENANT}/v2.0",
        "aud": "g-id" if provider == "google" else "m-id",
        "exp": time.time() + 300,
        "iat": time.time(),
        "nonce": query["nonce"][0],
        **claims,
    }
    with mock.patch.object(
        sso,
        "exchange",
        return_value=json.loads(base64.urlsafe_b64decode(id_token(full).split(".")[1] + "==")),
    ):
        return client.get(f"/sso/{provider}/callback/?code=abc&state={query['state'][0]}")


def test_providers_are_listed_only_when_configured(settings: Any) -> None:
    assert [p["id"] for p in Client().get("/api/v1/auth/sso/").json()] == ["google", "microsoft"]
    settings.SSO_CLIENTS = {"google": ("", "")}
    assert Client().get("/api/v1/auth/sso/").json() == []
    assert Client().get("/sso/google/start/").status_code == 404


def test_new_google_user_is_created_and_logged_in() -> None:
    client = Client()
    response = sign_in(
        client, "google", {"sub": "g-1", "email": "New@x.com", "email_verified": True}
    )
    assert response["Location"] == "/app"
    user = User.objects.get(email="new@x.com")
    assert not user.has_usable_password()
    assert SocialIdentity.objects.get(user=user).subject == "g-1"
    assert client.get("/api/v1/auth/me/").status_code == 200


def test_verified_google_email_links_an_existing_account() -> None:
    user = UserFactory.create(email="sam@x.com")
    sign_in(Client(), "google", {"sub": "g-2", "email": "sam@x.com", "email_verified": True})
    assert SocialIdentity.objects.get(provider="google").user == user


def test_microsoft_never_takes_over_an_existing_email() -> None:
    UserFactory.create(email="victim@x.com")
    response = sign_in(Client(), "microsoft", {"sub": "m-1", "email": "victim@x.com"})
    assert response["Location"] == "/login?sso_error=taken"
    assert not SocialIdentity.objects.exists()


def test_wrong_nonce_audience_or_expiry_is_refused() -> None:
    for bad in ({"nonce": "other"}, {"aud": "someone-else"}, {"exp": time.time() - 1}):
        client = Client()
        response = sign_in(client, "google", {"sub": "g-3", "email": "z@x.com", **bad})
        assert response["Location"] == "/login?sso_error=failed"
    assert not User.objects.filter(email="z@x.com").exists()


def test_state_must_match(client: Client) -> None:
    client.get("/sso/google/start/")
    response = client.get("/sso/google/callback/?code=abc&state=forged")
    assert response["Location"] == "/login?sso_error=expired"


def test_next_is_kept_on_this_site() -> None:
    response = sign_in(
        Client(),
        "google",
        {"sub": "g-4", "email": "n@x.com", "email_verified": True},
        next_path="https://evil.example/",
    )
    assert response["Location"] == "/app"


def test_linking_from_account_settings(client: Client) -> None:
    user = UserFactory.create(email="me@x.com")
    client.force_login(user)
    start = client.get("/sso/microsoft/start/?link=1")
    query = parse_qs(urlparse(start["Location"]).query)
    claims = {
        "iss": f"https://login.microsoftonline.com/{TENANT}/v2.0",
        "aud": "m-id",
        "exp": time.time() + 300,
        "nonce": query["nonce"][0],
        "sub": "m-9",
        "email": "work@corp.com",
    }
    with mock.patch.object(sso, "exchange", return_value=claims):
        response = client.get(f"/sso/microsoft/callback/?code=x&state={query['state'][0]}")
    assert response["Location"] == "/app/account"
    assert SocialIdentity.objects.get(provider="microsoft").user == user
    identities = client.get("/api/v1/auth/identities/").json()
    assert identities[0]["provider"] == "microsoft"
    assert client.delete("/api/v1/auth/identities/microsoft/").status_code == 204


def test_the_last_way_in_cannot_be_unlinked() -> None:
    client = Client()
    sign_in(client, "google", {"sub": "g-5", "email": "only@x.com", "email_verified": True})
    assert client.delete("/api/v1/auth/identities/google/").status_code == 409
