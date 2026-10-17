import datetime
from collections.abc import Callable
from smtplib import SMTPException
from typing import Any
from unittest import mock

import pytest
from celery.exceptions import Retry
from celery.schedules import crontab
from django.conf import settings
from django.core import mail
from django.core.mail import EmailMultiAlternatives
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.calendars.models import CustomDay
from apps.notifications.digests import unsubscribe_token
from apps.notifications.models import DigestSubscription
from apps.notifications.tasks import send_digest, send_digests
from apps.orgs.models import Role
from tests.factories import CalendarFactory, MembershipFactory, SourceFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def setup(client_for: Callable[[User], APIClient]) -> dict[str, Any]:
    member = MembershipFactory.create(role=Role.VIEWER)
    calendar = CalendarFactory.create(org=member.org, name="Karachi office", language="en_US")
    SourceFactory.create(calendar=calendar, country="PK")
    url = f"/api/v1/orgs/{member.org.slug}/calendars/{calendar.id}/digest/"
    return {"member": member, "calendar": calendar, "url": url, "api": client_for(member.user)}


def subscribe(setup: dict[str, Any]) -> DigestSubscription:
    assert setup["api"].put(setup["url"]).status_code == 200
    return DigestSubscription.objects.get(user=setup["member"].user)


def test_any_member_can_opt_in_and_out(setup: dict[str, Any]) -> None:
    assert setup["api"].get(setup["url"]).data == {"subscribed": False, "last_sent_on": None}
    assert setup["api"].put(setup["url"]).data["subscribed"] is True
    assert setup["api"].put(setup["url"]).data["subscribed"] is True
    assert DigestSubscription.objects.count() == 1
    assert setup["api"].delete(setup["url"]).data["subscribed"] is False
    assert DigestSubscription.objects.count() == 0


def test_subscription_is_per_user(
    setup: dict[str, Any], client_for: Callable[[User], APIClient]
) -> None:
    subscribe(setup)
    colleague = MembershipFactory.create(org=setup["member"].org, role=Role.ADMIN)
    assert client_for(colleague.user).get(setup["url"]).data["subscribed"] is False
    client_for(colleague.user).delete(setup["url"])
    assert DigestSubscription.objects.count() == 1


def test_monthly_digest_lists_the_next_30_days(setup: dict[str, Any]) -> None:
    subscription = subscribe(setup)
    CustomDay.objects.create(
        calendar=setup["calendar"], date=datetime.date(2027, 3, 10), name="Offsite", kind="closure"
    )
    CustomDay.objects.create(
        calendar=setup["calendar"],
        date=datetime.date(2027, 4, 4),
        name="Too late",
        kind="closure",
    )

    assert send_digests.delay("2027-03-05").get() == 1

    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert isinstance(message, EmailMultiAlternatives)
    assert message.to == [setup["member"].user.email]
    assert message.subject == "Holidays in the next 30 days: Karachi office"
    assert "Pakistan Day" in message.body
    assert "Offsite (Company closure)" in message.body
    assert "Too late" not in message.body
    token = unsubscribe_token(subscription)
    assert f"{settings.APP_URL}/unsubscribe?token={token}" in message.body
    assert message.extra_headers["List-Unsubscribe"] == (
        f"<{settings.APP_URL}/api/v1/digests/unsubscribe/?token={token}>"
    )
    assert message.extra_headers["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click"
    html, mimetype = message.alternatives[0]
    assert mimetype == "text/html"
    assert isinstance(html, str)
    assert 'dir="ltr"' in html
    assert "Pakistan Day" in html
    subscription.refresh_from_db()
    assert subscription.last_sent_on == datetime.date(2027, 3, 5)


def test_digest_is_sent_once_per_month(setup: dict[str, Any]) -> None:
    subscription = subscribe(setup)
    send_digests.delay("2027-03-01")
    assert send_digests.delay("2027-03-15").get() == 0
    assert send_digest.delay(subscription.pk, "2027-03-20").get() is False
    assert len(mail.outbox) == 1
    send_digests.delay("2027-04-01")
    assert len(mail.outbox) == 2


def test_empty_period_still_sends_a_short_digest(setup: dict[str, Any]) -> None:
    subscribe(setup)
    send_digests.delay("2027-09-01")
    assert "No holidays or company days off in this period." in mail.outbox[0].body


def test_digest_uses_the_users_language(setup: dict[str, Any]) -> None:
    User.objects.filter(pk=setup["member"].user.pk).update(language="ur")
    subscribe(setup)
    send_digests.delay("2027-03-05")
    message = mail.outbox[0]
    assert isinstance(message, EmailMultiAlternatives)
    assert "Karachi office" in message.subject
    assert not message.subject.startswith("Holidays")
    html = message.alternatives[0][0]
    assert isinstance(html, str)
    assert 'dir="rtl"' in html
    assert 'lang="ur"' in html


def test_former_members_get_nothing_and_lose_the_subscription(setup: dict[str, Any]) -> None:
    subscription = subscribe(setup)
    setup["member"].delete()
    assert send_digest.delay(subscription.pk, "2027-03-01").get() is False
    assert mail.outbox == []
    assert not DigestSubscription.objects.exists()


def test_missing_subscription_is_skipped() -> None:
    assert send_digest.delay(999_999, "2027-03-01").get() is False


def test_smtp_errors_are_retried(setup: dict[str, Any]) -> None:
    subscription = subscribe(setup)
    with (
        mock.patch(
            "django.core.mail.EmailMultiAlternatives.send", side_effect=SMTPException("busy")
        ),
        pytest.raises(Retry),
    ):
        send_digest.delay(subscription.pk, "2027-03-01")
    subscription.refresh_from_db()
    assert subscription.last_sent_on is None
    assert send_digest.delay(subscription.pk, "2027-03-01").get() is True


def test_one_click_unsubscribe_needs_no_session_or_csrf(setup: dict[str, Any]) -> None:
    subscription = subscribe(setup)
    client = APIClient(enforce_csrf_checks=True)
    response = client.post(
        f"/api/v1/digests/unsubscribe/?token={unsubscribe_token(subscription)}",
        "List-Unsubscribe=One-Click",
        content_type="application/x-www-form-urlencoded",
    )
    assert response.status_code == 204
    assert not DigestSubscription.objects.exists()


def test_unsubscribe_from_the_web_page_and_twice(setup: dict[str, Any]) -> None:
    token = unsubscribe_token(subscribe(setup))
    url = "/api/v1/digests/unsubscribe/"
    assert APIClient().post(url, {"token": token}, format="json").status_code == 204
    assert APIClient().post(url, {"token": token}, format="json").status_code == 204


def test_unsubscribe_rejects_bad_tokens() -> None:
    url = "/api/v1/digests/unsubscribe/"
    assert APIClient().post(url, {"token": "forged"}, format="json").status_code == 400
    assert APIClient().post(url, {}, format="json").status_code == 400
    assert APIClient().post(url, [1], format="json").status_code == 400


def test_beat_runs_digests_on_the_first_of_the_month() -> None:
    entry = settings.CELERY_BEAT_SCHEDULE["monthly-digests"]
    assert entry["task"] == "notifications.send_digests"
    assert entry["schedule"] == crontab(minute="0", hour="6", day_of_month="1")
