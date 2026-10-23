from celery import shared_task

from apps.accounts import codes
from apps.accounts.emails import send_email

__all__ = ["prune_unverified", "send_email"]


@shared_task(name="accounts.prune_unverified")
def prune_unverified() -> int:
    return codes.prune_unverified()
