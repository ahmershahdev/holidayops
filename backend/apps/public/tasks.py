import time

from celery import shared_task
from django.core.cache import caches

from apps.public.status import HEARTBEAT_KEY


@shared_task(name="public.heartbeat")
def heartbeat() -> None:
    """Proves Beat and a worker are both running; /status/ reads it."""
    caches["shared"].set(HEARTBEAT_KEY, time.time(), timeout=3600)
