import hashlib
import hmac
import json
from datetime import timedelta
from typing import Any
from unittest import mock

import pytest
from django.utils import timezone

from apps.webhooks.delivery import (
    BACKOFF,
    DISABLE_AFTER_FAILURES,
    LEASE,
    MAX_ATTEMPTS,
    attempt,
    claim,
    sign,
)
from apps.webhooks.events import create_delivery, emit
from apps.webhooks.models import DeliveryStatus, Webhook, WebhookDelivery
from apps.webhooks.tasks import deliver, retry_due
from tests.factories import OrgFactory
from tests.webhooks.conftest import FakeReceiver, addrinfo

pytestmark = pytest.mark.django_db


def make_hook(**kwargs: Any) -> Webhook:
    defaults = {
        "org": OrgFactory.create(),
        "url": "https://hooks.example.com/in",
        "events": ["custom_day.created"],
    }
    return Webhook.objects.create(**{**defaults, **kwargs})


def test_signature_is_hmac_sha256_of_timestamp_and_body() -> None:
    expected = hmac.new(b"whsec_x", b"1700000000.{}", hashlib.sha256).hexdigest()
    assert sign("whsec_x", 1700000000, b"{}") == f"t=1700000000,v1={expected}"


def test_emit_reaches_only_active_hooks_that_want_the_event(
    receiver: FakeReceiver, django_capture_on_commit_callbacks: Any
) -> None:
    hook = make_hook()
    make_hook(org=hook.org, events=["calendar.updated"])
    make_hook(org=hook.org, is_active=False)
    make_hook(events=["custom_day.created"])
    with django_capture_on_commit_callbacks(execute=True):
        assert emit(hook.org, "custom_day.created", {"x": 1}) == 1
    assert len(receiver.calls) == 1

    call = receiver.calls[0]
    payload = json.loads(call["body"])
    assert payload["event"] == "custom_day.created"
    assert payload["org"] == hook.org.slug
    assert payload["data"] == {"x": 1}
    headers = call["headers"]
    assert headers["X-HolidayOps-Event"] == "custom_day.created"
    assert headers["X-HolidayOps-Delivery"] == payload["id"]
    timestamp = int(headers["X-HolidayOps-Signature"].split(",")[0].removeprefix("t="))
    assert headers["X-HolidayOps-Signature"] == sign(hook.secret, timestamp, call["body"])
    delivery = WebhookDelivery.objects.get()
    assert delivery.status == DeliveryStatus.SUCCESS
    assert delivery.response_status == 200
    assert delivery.next_attempt_at is None


def test_server_errors_retry_with_backoff_then_fail(receiver: FakeReceiver) -> None:
    receiver.status = 503
    hook = make_hook()
    delivery = create_delivery(hook, "custom_day.created", {})
    now = timezone.now()
    for n in range(1, MAX_ATTEMPTS):
        claimed = claim(str(delivery.pk), now)
        assert claimed is not None
        attempt(claimed, now)
        assert claimed.status == DeliveryStatus.PENDING
        assert claimed.attempts == n
        assert claimed.next_attempt_at == now + BACKOFF[n - 1]
        assert claim(str(delivery.pk), now) is None
        now += BACKOFF[n - 1]
    last = claim(str(delivery.pk), now)
    assert last is not None
    attempt(last, now)
    assert last.status == DeliveryStatus.FAILED
    assert last.attempts == MAX_ATTEMPTS
    assert len(receiver.calls) == MAX_ATTEMPTS
    hook.refresh_from_db()
    assert hook.failure_count == 1


@pytest.mark.parametrize("status", [429, None])
def test_rate_limits_and_network_errors_retry(receiver: FakeReceiver, status: int | None) -> None:
    receiver.status = status
    receiver.error = "" if status else "TimeoutError: timed out"
    delivery = create_delivery(make_hook(), "custom_day.created", {})
    assert deliver.delay(str(delivery.pk)).get() is False
    delivery.refresh_from_db()
    assert delivery.status == DeliveryStatus.PENDING
    assert delivery.error == receiver.error


def test_client_errors_fail_at_once(receiver: FakeReceiver) -> None:
    receiver.status = 404
    delivery = create_delivery(make_hook(), "custom_day.created", {})
    deliver.delay(str(delivery.pk))
    delivery.refresh_from_db()
    assert delivery.status == DeliveryStatus.FAILED
    assert delivery.attempts == 1


def test_redirects_are_not_followed(receiver: FakeReceiver) -> None:
    receiver.status = 302
    delivery = create_delivery(make_hook(), "custom_day.created", {})
    deliver.delay(str(delivery.pk))
    delivery.refresh_from_db()
    assert delivery.status == DeliveryStatus.FAILED
    assert delivery.error == "Redirects are not followed."


def test_host_that_now_resolves_inside_is_blocked_before_sending(
    receiver: FakeReceiver, dns: mock.MagicMock
) -> None:
    delivery = create_delivery(make_hook(), "custom_day.created", {})
    dns.return_value = addrinfo("10.0.0.7")
    deliver.delay(str(delivery.pk))
    delivery.refresh_from_db()
    assert delivery.status == DeliveryStatus.FAILED
    assert "public addresses" in delivery.error
    assert receiver.calls == []


def test_disabled_hook_does_not_send(receiver: FakeReceiver) -> None:
    hook = make_hook()
    delivery = create_delivery(hook, "custom_day.created", {})
    Webhook.objects.filter(pk=hook.pk).update(is_active=False)
    deliver.delay(str(delivery.pk))
    delivery.refresh_from_db()
    assert delivery.status == DeliveryStatus.FAILED
    assert receiver.calls == []


def test_hook_is_disabled_after_too_many_failed_deliveries(receiver: FakeReceiver) -> None:
    receiver.status = 410
    hook = make_hook(failure_count=DISABLE_AFTER_FAILURES - 1)
    deliver.delay(str(create_delivery(hook, "custom_day.created", {}).pk))
    hook.refresh_from_db()
    assert hook.failure_count == DISABLE_AFTER_FAILURES
    assert hook.is_active is False


def test_success_resets_the_failure_count(receiver: FakeReceiver) -> None:
    hook = make_hook(failure_count=5)
    deliver.delay(str(create_delivery(hook, "custom_day.created", {}).pk))
    hook.refresh_from_db()
    assert hook.failure_count == 0


def test_a_crashed_attempt_becomes_due_again_after_the_lease() -> None:
    delivery = create_delivery(make_hook(), "custom_day.created", {})
    now = timezone.now()
    assert claim(str(delivery.pk), now) is not None
    assert claim(str(delivery.pk), now + LEASE - timedelta(seconds=1)) is None
    assert claim(str(delivery.pk), now + LEASE) is not None


def test_retry_due_enqueues_only_due_pending_deliveries(receiver: FakeReceiver) -> None:
    hook = make_hook()
    due = create_delivery(hook, "custom_day.created", {})
    later = create_delivery(hook, "custom_day.created", {})
    WebhookDelivery.objects.filter(pk=later.pk).update(
        next_attempt_at=timezone.now() + timedelta(hours=1)
    )
    done = create_delivery(hook, "custom_day.created", {})
    WebhookDelivery.objects.filter(pk=done.pk).update(status=DeliveryStatus.SUCCESS)
    assert retry_due.delay().get() == 1
    due.refresh_from_db()
    assert due.status == DeliveryStatus.SUCCESS


def test_unknown_delivery_is_ignored() -> None:
    assert deliver.delay("00000000-0000-0000-0000-000000000000").get() is False
