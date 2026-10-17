from celery import shared_task
from django.utils import timezone

from apps.api.models import UsageEvent
from apps.api.usage import RETENTION


@shared_task(name="api.prune_usage")
def prune_usage() -> int:
    deleted, _ = UsageEvent.objects.filter(created_at__lt=timezone.now() - RETENTION).delete()
    return deleted
