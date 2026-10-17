import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db.models import QuerySet
from django.template.loader import render_to_string
from django.utils import timezone, translation
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

from apps.accounts.models import User
from apps.orgs.models import Invite, Membership, Organization

INVITE_DAYS = 7
RTL = {"ur", "ar"}
ROLE_NAMES = {
    "owner": gettext_lazy("Owner"),
    "admin": gettext_lazy("Admin"),
    "member": gettext_lazy("Member"),
    "viewer": gettext_lazy("Viewer"),
}


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def pending(org: Organization) -> QuerySet[Invite]:
    return org.invites.filter(accepted_at__isnull=True, expires_at__gt=timezone.now())


def find_pending(token: str) -> Invite | None:
    return (
        Invite.objects.select_related("org", "invited_by")
        .filter(token_hash=hash_token(token), accepted_at__isnull=True)
        .filter(expires_at__gt=timezone.now())
        .first()
    )


def issue(invite: Invite) -> str:
    """Give the invite a fresh token and expiry; the caller saves it."""
    token = secrets.token_urlsafe(32)
    invite.token_hash = hash_token(token)
    invite.expires_at = timezone.now() + timedelta(days=INVITE_DAYS)
    return token


def send(invite: Invite, token: str, fallback_language: str) -> None:
    account = User.objects.filter(email__iexact=invite.email).first()
    language = account.language if account else fallback_language
    inviter = invite.invited_by
    context = {
        "org": invite.org,
        "inviter": (inviter.name or inviter.email) if inviter else "HolidayOps",
        "url": f"{settings.APP_URL}/invite?token={token}",
        "days": INVITE_DAYS,
        "language": language,
        "dir": "rtl" if language in RTL else "ltr",
    }
    with translation.override(language):
        context["role"] = str(ROLE_NAMES[invite.role])
        subject = _("You're invited to %(org)s on HolidayOps") % {"org": invite.org.name}
        text = render_to_string("orgs/invite.txt", context)
        html = render_to_string("orgs/invite.html", context)
    message = EmailMultiAlternatives(subject, text, to=[invite.email])
    message.attach_alternative(html, "text/html")
    message.send()


def accept(invite: Invite, user: User) -> Membership:
    membership, _created = Membership.objects.get_or_create(
        user=user, org=invite.org, defaults={"role": invite.role}
    )
    invite.accepted_at = timezone.now()
    invite.save(update_fields=["accepted_at"])
    return membership
