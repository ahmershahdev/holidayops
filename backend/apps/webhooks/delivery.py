import hashlib
import hmac
import json
from datetime import datetime, timedelta

from django.db.models import F

from apps.webhooks import net
from apps.webhooks.models import DeliveryStatus, Webhook, WebhookDelivery

# Wait before attempts 2-6; attempt 1 is immediate.
BACKOFF = [
    timedelta(minutes=1),
    timedelta(minutes=5),
    timedelta(minutes=30),
    timedelta(hours=2),
    timedelta(hours=12),
]
MAX_ATTEMPTS = len(BACKOFF) + 1
DISABLE_AFTER_FAILURES = 20
LEASE = timedelta(minutes=5)


def sign(secret: str, timestamp: int, body: bytes) -> str:
    digest = hmac.new(secret.encode(), f"{timestamp}.".encode() + body, hashlib.sha256)
    return f"t={timestamp},v1={digest.hexdigest()}"


def body_of(delivery: WebhookDelivery) -> bytes:
    return json.dumps(delivery.payload, ensure_ascii=False, separators=(",", ":")).encode()


def claim(delivery_id: str, now: datetime) -> WebhookDelivery | None:
    """Take a due delivery for one attempt; the lease makes a crashed attempt due again later."""
    claimed = WebhookDelivery.objects.filter(
        pk=delivery_id, status=DeliveryStatus.PENDING, next_attempt_at__lte=now
    ).update(next_attempt_at=now + LEASE)
    if not claimed:
        return None
    return WebhookDelivery.objects.select_related("webhook").get(pk=delivery_id)


def _retryable(result: net.Result) -> bool:
    return result.status is None or result.status == 429 or result.status >= 500


def attempt(delivery: WebhookDelivery, now: datetime) -> None:
    webhook = delivery.webhook
    delivery.attempts += 1
    if not webhook.is_active:
        _finish(delivery, DeliveryStatus.FAILED, error="Webhook is disabled.")
        return
    try:
        target = net.check_url(webhook.url)
    except net.UnsafeURL as exc:
        _fail(delivery, net.Result(None, "", 0, str(exc)[:300]), now, retry=False)
        return
    body = body_of(delivery)
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "HolidayOps-Webhooks/1",
        "X-HolidayOps-Event": delivery.event,
        "X-HolidayOps-Delivery": str(delivery.pk),
        "X-HolidayOps-Signature": sign(webhook.secret, int(now.timestamp()), body),
    }
    result = net.post(target, body, headers)
    _record(delivery, result)
    if result.status is not None and 200 <= result.status < 300:
        _finish(delivery, DeliveryStatus.SUCCESS)
        Webhook.objects.filter(pk=webhook.pk).update(failure_count=0)
    else:
        if result.status is not None and 300 <= result.status < 400 and not result.error:
            delivery.error = "Redirects are not followed."
        _fail(delivery, result, now, retry=_retryable(result))


def _record(delivery: WebhookDelivery, result: net.Result) -> None:
    delivery.response_status = result.status
    delivery.response_body = result.body
    delivery.duration_ms = result.duration_ms
    delivery.error = result.error


def _finish(delivery: WebhookDelivery, status: str, error: str | None = None) -> None:
    delivery.status = status
    delivery.next_attempt_at = None
    if error is not None:
        delivery.error = error
    delivery.save()


def _fail(delivery: WebhookDelivery, result: net.Result, now: datetime, retry: bool) -> None:
    if result.error:
        delivery.error = result.error
    if retry and delivery.attempts < MAX_ATTEMPTS:
        delivery.next_attempt_at = now + BACKOFF[delivery.attempts - 1]
        delivery.save()
        return
    _finish(delivery, DeliveryStatus.FAILED)
    Webhook.objects.filter(pk=delivery.webhook_id).update(failure_count=F("failure_count") + 1)
    Webhook.objects.filter(
        pk=delivery.webhook_id, failure_count__gte=DISABLE_AFTER_FAILURES
    ).update(is_active=False)
