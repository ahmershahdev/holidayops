"""Account emails: codes and security notices, sent from the worker.

Queuing instead of sending in the request keeps every answer equally fast, so response times
don't tell anyone whether an address has an account."""

from typing import Any

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import translation
from django.utils.translation import gettext as _
from django.utils.translation import gettext_noop

from apps.accounts.models import User
from apps.public.seo import SUPPORT_EMAIL

RTL = {"ur", "ar"}

RESET_SUBJECT = gettext_noop("Your HolidayOps password reset code")
VERIFY_SUBJECT = gettext_noop("Confirm your HolidayOps email")
CHANGED_SUBJECT = gettext_noop("Your HolidayOps password was changed")
EXISTS_SUBJECT = gettext_noop("Someone tried to sign up with your email")
WELCOME_SUBJECT = gettext_noop("Welcome to HolidayOps")
NOTICE_SUBJECT = gettext_noop("Security alert for your HolidayOps account")

# Security notices share one template; the event picks the sentence.
NOTICES = {
    "two_factor_on": gettext_noop("Two-factor sign-in was turned on."),
    "two_factor_off": gettext_noop("Two-factor sign-in was turned off."),
    "recovery_codes": gettext_noop("New recovery codes were made; the old ones no longer work."),
    "sso_linked": gettext_noop("A Google or Microsoft account was linked for sign-in."),
    "sso_unlinked": gettext_noop("A Google or Microsoft sign-in was removed."),
    "account_deleted": gettext_noop("Your account and its data were deleted."),
}


def render(
    user: User, template: str, subject: str, context: dict[str, Any]
) -> EmailMultiAlternatives:
    language = user.language
    context = {
        **context,
        "language": language,
        "dir": "rtl" if language in RTL else "ltr",
        "support": SUPPORT_EMAIL,
        "app_url": settings.APP_URL,
    }
    with translation.override(language):
        if "notice" in context:
            context["notice"] = _(NOTICES[context["notice"]])
        text = render_to_string(f"accounts/{template}.txt", context)
        html = render_to_string(f"accounts/{template}.html", context)
        message = EmailMultiAlternatives(_(subject), text, to=[user.email])
    message.attach_alternative(html, "text/html")
    return message


@shared_task(name="accounts.send_email", autoretry_for=(OSError,), retry_backoff=30, max_retries=3)
def send_email(user_id: int, template: str, subject: str, context: dict[str, Any]) -> bool:
    user = User.objects.filter(pk=user_id).first()
    if user is None:
        return False
    render(user, template, subject, context).send()
    return True


def queue(user: User, template: str, subject: str, context: dict[str, Any] | None = None) -> None:
    send_email.delay(user.pk, template, subject, context or {})


def notify(user: User, event: str) -> None:
    queue(user, "notice", NOTICE_SUBJECT, {"notice": event})


def notify_now(user: User, event: str) -> None:
    """For an account about to be deleted: the worker would find no one to write to."""
    render(user, "notice", NOTICE_SUBJECT, {"notice": event}).send(fail_silently=True)
