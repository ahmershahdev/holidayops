"""Self-serve data export and account deletion (privacy policy, "Your rights")."""

from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.api.models import ApiKey
from apps.calendars.models import Calendar
from apps.feeds.models import FeedToken
from apps.notifications.models import DigestSubscription
from apps.orgs.models import AuditLog, Membership, Organization, Role
from apps.webhooks.models import Webhook


def _calendar(calendar: Calendar) -> dict[str, Any]:
    return {
        "id": str(calendar.id),
        "name": calendar.name,
        "is_public": calendar.is_public,
        "language": calendar.language,
        "weekend": calendar.weekend,
        "sources": [
            {"country": s.country, "subdiv": s.subdiv, "categories": s.categories}
            for s in calendar.sources.all()
        ],
        "custom_days": [
            {"date": d.date.isoformat(), "name": d.name, "kind": d.kind}
            for d in calendar.custom_days.order_by("date")
        ],
    }


def _org(membership: Membership) -> dict[str, Any]:
    org = membership.org
    data: dict[str, Any] = {
        "name": org.name,
        "slug": org.slug,
        "plan": org.plan,
        "role": membership.role,
        "joined_at": membership.created_at.isoformat(),
        "calendars": [_calendar(c) for c in Calendar.objects.filter(org=org)],
    }
    # Admins and owners manage these; secrets and hashes are never exported.
    if membership.has_role(Role.ADMIN):
        data["api_keys"] = list(
            ApiKey.objects.filter(org=org).values("name", "prefix", "created_at", "revoked_at")
        )
        data["feeds"] = list(
            FeedToken.objects.filter(org=org).values("label", "calendar_id", "created_at")
        )
        data["webhooks"] = list(Webhook.objects.filter(org=org).values("url", "events"))
    return data


def export(user: User) -> dict[str, Any]:
    memberships = Membership.objects.filter(user=user).select_related("org")
    return {
        "exported_at": timezone.now().isoformat(),
        "account": {
            "email": user.email,
            "name": user.name,
            "language": user.language,
            "date_joined": user.date_joined.isoformat(),
            "last_login": user.last_login.isoformat() if user.last_login else None,
            "two_factor": hasattr(user, "two_factor") and user.two_factor.confirmed_at is not None,
            "sign_in_with": [
                {"provider": i.provider, "email": i.email, "linked_at": i.created_at.isoformat()}
                for i in user.identities.all()
            ],
        },
        "organizations": [_org(m) for m in memberships],
        "digests": [
            {"calendar": str(d.calendar_id), "last_sent_on": d.last_sent_on}
            for d in DigestSubscription.objects.filter(user=user)
        ],
        "activity": list(
            AuditLog.objects.filter(actor=user).values(
                "org__name", "action", "target", "created_at"
            )
        ),
    }


def blocking_orgs(user: User) -> list[str]:
    """Organizations the user owns alone while others are still members: deleting the account
    would leave them without an owner, so ownership has to move first."""
    owned = Organization.objects.filter(memberships__user=user, memberships__role=Role.OWNER)
    return [
        org.name
        for org in owned
        if org.memberships.count() > 1
        and not org.memberships.filter(role=Role.OWNER).exclude(user=user).exists()
    ]


def delete_account(user: User) -> None:
    """Delete the user and every organization they are the only member of. Records other
    members still rely on (audit log, keys they created) stay, without the user's name."""
    with transaction.atomic():
        mine = Organization.objects.filter(memberships__user=user)
        solo = [org.pk for org in mine if org.memberships.count() == 1]
        Organization.objects.filter(pk__in=solo).delete()
        user.delete()
