"""Security events are logged without secrets, and clients can't dodge throttles."""

import logging
from typing import Any
from unittest import mock

import pytest
from django.test import RequestFactory
from rest_framework.test import APIClient

from apps.api.models import ApiKey
from apps.public.views import PublicPageThrottle
from config.security_log import client_ip, email_ref, security_event
from tests.factories import PASSWORD, OrgFactory, UserFactory

pytestmark = pytest.mark.django_db

LOGIN = "/api/v1/auth/login/"
SECURITY = "holidayops.security"


def events(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [r for r in caplog.records if r.name == SECURITY]


def test_failed_login_is_logged_without_password_or_email(
    client: APIClient, caplog: pytest.LogCaptureFixture
) -> None:
    user = UserFactory.create()
    with caplog.at_level(logging.INFO, logger=SECURITY):
        client.post(LOGIN, {"email": user.email, "password": "wrong-Pa55word"}, format="json")
    [record] = events(caplog)
    message = record.getMessage()
    assert record.levelno == logging.WARNING
    assert message.startswith("auth.login_failed ip=127.0.0.1 path=/api/v1/auth/login/")
    assert f"account={email_ref(user.email)}" in message
    assert user.email not in message
    assert "wrong-Pa55word" not in message


def test_successful_login_is_logged_at_info(
    client: APIClient, caplog: pytest.LogCaptureFixture
) -> None:
    user = UserFactory.create()
    with caplog.at_level(logging.INFO, logger=SECURITY):
        response = client.post(LOGIN, {"email": user.email, "password": PASSWORD}, format="json")
    assert response.status_code == 200
    [record] = events(caplog)
    assert record.levelno == logging.INFO
    assert f"auth.login ip=127.0.0.1 path={LOGIN} user={user.pk}" == record.getMessage()


def test_invalid_api_key_logs_the_prefix_never_the_secret(
    client: APIClient, caplog: pytest.LogCaptureFixture
) -> None:
    api_key = ApiKey(org=OrgFactory.create(), name="ci")
    key = api_key.set_new_key()
    api_key.save()
    forged = key[:-4] + "XXXX"
    with caplog.at_level(logging.INFO, logger=SECURITY):
        response = client.get("/api/v1/countries/", HTTP_AUTHORIZATION=f"Bearer {forged}")
    assert response.status_code == 401
    [record] = events(caplog)
    assert f"prefix={api_key.prefix}" in record.getMessage()
    assert forged.split("_", 2)[2] not in record.getMessage()


def test_login_throttle_ignores_a_rotating_forwarded_for(
    client: APIClient, caplog: pytest.LogCaptureFixture
) -> None:
    body = {"email": "nobody@example.com", "password": "x"}
    with caplog.at_level(logging.INFO, logger=SECURITY):
        statuses = [
            client.post(
                LOGIN, body, format="json", HTTP_X_FORWARDED_FOR=f"203.0.113.{n}"
            ).status_code
            for n in range(11)
        ]
    assert statuses[:10] == [400] * 10
    assert statuses[10] == 429
    throttled = [r for r in events(caplog) if r.getMessage().startswith("rate_limited")]
    assert throttled[0].levelno == logging.WARNING
    assert "scope=auth" in throttled[0].getMessage()


def test_client_ip_trusts_forwarded_for_only_behind_configured_proxies(settings: Any) -> None:
    request = RequestFactory().get("/", HTTP_X_FORWARDED_FOR="198.51.100.7, 203.0.113.9")
    assert client_ip(request) == "127.0.0.1"
    settings.REST_FRAMEWORK = {**settings.REST_FRAMEWORK, "NUM_PROXIES": 1}
    assert client_ip(request) == "203.0.113.9"


def test_log_fields_cannot_forge_lines(caplog: pytest.LogCaptureFixture) -> None:
    request = RequestFactory().get("/x")
    with caplog.at_level(logging.INFO, logger=SECURITY):
        security_event("test", request, note="ok\nauth.login user=1")
    assert "\n" not in events(caplog)[0].getMessage()


def test_public_page_renders_are_rate_limited_but_cached_pages_are_not(
    client: APIClient, caplog: pytest.LogCaptureFixture
) -> None:
    with mock.patch.dict(PublicPageThrottle.THROTTLE_RATES, {"public": "2/minute"}):
        assert client.get("/holidays/").status_code == 200
        assert client.get("/?country=PK&date=2026-03-23").status_code == 200
        with caplog.at_level(logging.INFO, logger=SECURITY):
            limited = client.get("/?country=PK&date=2026-03-24")
        assert limited.status_code == 429
        assert int(limited["Retry-After"]) > 0
        assert "scope=public" in events(caplog)[0].getMessage()
        assert client.get("/holidays/").status_code == 200
