from datetime import date
from smtplib import SMTPException

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from apps.notifications.digests import build_digest
from apps.notifications.models import DigestSubscription
from apps.orgs.models import Membership


def _sent_this_month(last_sent_on: date | None, run_date: date) -> bool:
    return last_sent_on is not None and (last_sent_on.year, last_sent_on.month) == (
        run_date.year,
        run_date.month,
    )


@shared_task(name="notifications.send_digests")
def send_digests(run_date: str | None = None) -> int:
    day = date.fromisoformat(run_date) if run_date else timezone.now().date()
    ids = [
        pk
        for pk, last_sent_on in DigestSubscription.objects.values_list("pk", "last_sent_on")
        if not _sent_this_month(last_sent_on, day)
    ]
    for pk in ids:
        send_digest.delay(pk, day.isoformat())
    return len(ids)


@shared_task(
    name="notifications.send_digest",
    autoretry_for=(SMTPException, OSError),
    retry_backoff=60,
    max_retries=5,
)
def send_digest(subscription_id: int, run_date: str) -> bool:
    day = date.fromisoformat(run_date)
    with transaction.atomic():
        subscription = (
            DigestSubscription.objects.select_for_update()
            .select_related("user", "calendar__org")
            .filter(pk=subscription_id)
            .first()
        )
        if subscription is None or _sent_this_month(subscription.last_sent_on, day):
            return False
        if not Membership.objects.filter(
            user=subscription.user, org=subscription.calendar.org
        ).exists():
            subscription.delete()
            return False
        build_digest(subscription, day).send()
        subscription.last_sent_on = day
        subscription.save(update_fields=["last_sent_on"])
    return True
