from datetime import date, timedelta

from django.conf import settings
from django.core import signing
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import translation
from django.utils.translation import gettext as _

from apps.calendars.services import build_merged
from apps.core import feed_events
from apps.notifications.models import DigestSubscription

DIGEST_DAYS = 30
UNSUBSCRIBE_SALT = "notifications.digest.unsubscribe"
RTL = {"ur", "ar"}


def unsubscribe_token(subscription: DigestSubscription) -> str:
    return signing.dumps(subscription.pk, salt=UNSUBSCRIBE_SALT)


def subscription_id_from(token: str) -> int | None:
    try:
        value = signing.loads(token, salt=UNSUBSCRIBE_SALT)
    except signing.BadSignature:
        return None
    return value if isinstance(value, int) else None


def build_digest(subscription: DigestSubscription, run_date: date) -> EmailMultiAlternatives:
    calendar, user = subscription.calendar, subscription.user
    end = run_date + timedelta(days=DIGEST_DAYS - 1)
    merged = build_merged(calendar, range(run_date.year, end.year + 1))
    events = feed_events(merged, run_date, end)
    token = unsubscribe_token(subscription)
    context = {
        "calendar": calendar,
        "events": events,
        "start": run_date,
        "end": end,
        "days": DIGEST_DAYS,
        "calendar_url": f"{settings.APP_URL}/app/{calendar.org.slug}/calendars/{calendar.pk}",
        "unsubscribe_url": f"{settings.APP_URL}/unsubscribe?token={token}",
        "dir": "rtl" if user.language in RTL else "ltr",
        "language": user.language,
    }
    with translation.override(user.language):
        subject = _("Holidays in the next %(days)s days: %(calendar)s") % {
            "days": DIGEST_DAYS,
            "calendar": calendar.name,
        }
        text = render_to_string("notifications/digest.txt", context)
        html = render_to_string("notifications/digest.html", context)
    message = EmailMultiAlternatives(
        subject,
        text,
        to=[user.email],
        headers={
            "List-Unsubscribe": f"<{settings.APP_URL}/api/v1/digests/unsubscribe/?token={token}>",
            "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
        },
    )
    message.attach_alternative(html, "text/html")
    return message
