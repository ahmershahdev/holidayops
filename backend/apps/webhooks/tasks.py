from celery import shared_task
from django.utils import timezone

from apps.webhooks.delivery import attempt, claim
from apps.webhooks.models import DeliveryStatus, WebhookDelivery

DUE_BATCH = 500


@shared_task(name="webhooks.deliver")
def deliver(delivery_id: str) -> bool:
    now = timezone.now()
    delivery = claim(delivery_id, now)
    if delivery is None:
        return False
    attempt(delivery, now)
    return delivery.status == DeliveryStatus.SUCCESS


# Retries are scheduled in the database, not as Celery countdowns: Redis redelivers tasks whose
# ETA is past its visibility timeout (1 h), which would run the 2 h and 12 h retries twice.
@shared_task(name="webhooks.retry_due")
def retry_due() -> int:
    ids = list(
        WebhookDelivery.objects.filter(
            status=DeliveryStatus.PENDING, next_attempt_at__lte=timezone.now()
        )
        .order_by("next_attempt_at")
        .values_list("pk", flat=True)[:DUE_BATCH]
    )
    for pk in ids:
        deliver.delay(str(pk))
    return len(ids)
