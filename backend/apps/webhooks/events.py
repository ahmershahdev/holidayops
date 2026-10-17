from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.calendars.models import Calendar, CustomDay
from apps.orgs.models import Organization
from apps.webhooks.models import PING, Webhook, WebhookDelivery
from apps.webhooks.tasks import deliver


def create_delivery(webhook: Webhook, event: str, data: dict[str, Any]) -> WebhookDelivery:
    delivery = WebhookDelivery(webhook=webhook, event=event, next_attempt_at=timezone.now())
    delivery.payload = {
        "id": str(delivery.id),
        "event": event,
        "created_at": timezone.now().isoformat(),
        "org": webhook.org.slug,
        "data": data,
    }
    delivery.save()
    return delivery


def enqueue(delivery: WebhookDelivery) -> None:
    transaction.on_commit(lambda: deliver.delay(str(delivery.pk)))


def emit(org: Organization, event: str, data: dict[str, Any]) -> int:
    hooks = [
        hook
        for hook in Webhook.objects.filter(org=org, is_active=True).select_related("org")
        if event in hook.events
    ]
    for hook in hooks:
        enqueue(create_delivery(hook, event, data))
    return len(hooks)


def ping(webhook: Webhook) -> WebhookDelivery:
    delivery = create_delivery(webhook, PING, {"webhook": webhook.pk})
    enqueue(delivery)
    return delivery


def calendar_data(calendar: Calendar) -> dict[str, Any]:
    return {"calendar": {"id": str(calendar.pk), "name": calendar.name, "slug": calendar.slug}}


def custom_day_data(day: CustomDay) -> dict[str, Any]:
    return {
        **calendar_data(day.calendar),
        "custom_day": {
            "id": day.pk,
            "date": day.date.isoformat(),
            "name": day.name,
            "kind": day.kind,
        },
    }
