from typing import Any

from django.db.models import Model, QuerySet
from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from django.utils.translation import gettext as _
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import SAFE_METHODS
from rest_framework.request import Request

from apps.orgs.models import AuditLog, Membership, Organization, Role


def unique_slug(name: str, taken: QuerySet[Any], field: str = "slug") -> str:
    base = slugify(name)[:50] or "item"
    slug, n = base, 2
    while taken.filter(**{field: slug}).exists():
        slug, n = f"{base}-{n}", n + 1
    return slug


def get_membership(user: Any, org_slug: str) -> Membership:
    return get_object_or_404(
        Membership.objects.select_related("org"), org__slug=org_slug, user=user
    )


def audit(membership: Membership, action: str, target: Model | str) -> None:
    AuditLog.objects.create(
        org=membership.org, actor=membership.user, action=action, target=str(target)[:200]
    )


class OrgScopedMixin:
    """Resolves the org from the URL. Non-members get 404, too-low roles get 403."""

    read_role = Role.VIEWER
    write_role = Role.MEMBER
    delete_role: Role | None = None

    membership: Membership
    org: Organization

    def initial(self, request: Request, *args: Any, **kwargs: Any) -> None:
        super().initial(request, *args, **kwargs)  # type: ignore[misc]
        self.membership = get_membership(request.user, kwargs["org_slug"])
        self.org = self.membership.org
        if request.method in SAFE_METHODS:
            needed = self.read_role
        elif request.method == "DELETE" and self.delete_role is not None:
            needed = self.delete_role
        else:
            needed = self.write_role
        if not self.membership.has_role(needed):
            raise PermissionDenied(_("Your role does not allow this action."))
