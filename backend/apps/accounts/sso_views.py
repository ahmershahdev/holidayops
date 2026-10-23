"""Browser redirects for sign in with Google or Microsoft. Logic lives in apps/accounts/sso.py."""

import logging
import secrets
import time
from urllib.parse import urlencode

from django.contrib.auth import login
from django.db import IntegrityError, transaction
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseRedirect
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from apps.accounts import emails, sso, twofactor
from apps.accounts.models import SocialIdentity, User
from config.security_log import security_event

FLOW = "sso_flow"
MODEL_BACKEND = "django.contrib.auth.backends.ModelBackend"


def _safe_next(request: HttpRequest, target: str | None) -> str:
    if target and url_has_allowed_host_and_scheme(target, {request.get_host()}, True):
        return target
    return "/app"


def _fail(request: HttpRequest, reason: str) -> HttpResponse:
    security_event("auth.sso_failed", request, reason=reason)
    return HttpResponseRedirect(f"/login?{urlencode({'sso_error': reason})}")


def start(request: HttpRequest, provider: str) -> HttpResponse:
    chosen = sso.PROVIDERS.get(provider)
    credentials = sso.credentials(provider)
    if chosen is None or credentials is None:
        raise Http404
    link = (
        request.user.pk
        if request.GET.get("link") == "1" and request.user.is_authenticated
        else None
    )
    url, flow = sso.begin(
        chosen, credentials[0], _safe_next(request, request.GET.get("next")), link
    )
    request.session[FLOW] = flow
    return HttpResponseRedirect(url)


def _resolve(
    provider: sso.Provider, claims: sso.Claims, link: int | None, request: HttpRequest
) -> User | str:
    """The account to sign in, or the reason there isn't one."""
    identity = (
        SocialIdentity.objects.filter(provider=provider.id, subject=claims.subject)
        .select_related("user")
        .first()
    )
    if identity:
        return identity.user if identity.user.is_active else "inactive"
    created = False
    if link is not None:
        user = User.objects.filter(pk=link, is_active=True).first()
        if user is None or request.user.pk != link:
            return "expired"
    else:
        if not claims.email:
            return "no_email"
        user = User.objects.filter(email__iexact=claims.email).first()
        # An existing account is only joined on an address the provider vouches for.
        if user is not None and not claims.email_verified:
            return "taken"
        created = user is None
        if user is None:
            language = getattr(request, "LANGUAGE_CODE", "en")
            user = User.objects.create_user(
                claims.email,
                None,
                name=claims.name[:150],
                language=language if language in {"en", "ur", "ar"} else "en",
            )
    try:
        with transaction.atomic():
            SocialIdentity.objects.create(
                user=user,
                provider=provider.id,
                subject=claims.subject,
                email=claims.email,
                email_verified=claims.email_verified,
            )
    except IntegrityError:
        return "expired"
    vouched = claims.email_verified and claims.email.lower() == user.email.lower()
    if vouched and not user.email_verified:
        user.email_verified_at = timezone.now()
        user.save(update_fields=["email_verified_at"])
    if not created:
        emails.notify(user, "sso_linked")
    security_event("auth.sso_linked", request, logging.INFO, user=user.pk, provider=provider.id)
    return user


def callback(request: HttpRequest, provider: str) -> HttpResponse:
    chosen = sso.PROVIDERS.get(provider)
    if chosen is None:
        raise Http404
    flow = request.session.pop(FLOW, None)
    if (
        not flow
        or flow["provider"] != provider
        or time.time() - flow["at"] > sso.FLOW_SECONDS
        or not secrets.compare_digest(flow["state"], request.GET.get("state", ""))
    ):
        return _fail(request, "expired")
    if "code" not in request.GET:
        return _fail(request, "cancelled")
    try:
        claims = sso.validate(
            chosen, sso.exchange(chosen, flow, request.GET["code"]), flow["nonce"], time.time()
        )
    except sso.SsoError:
        return _fail(request, "failed")
    result = _resolve(chosen, claims, flow["link"], request)
    if isinstance(result, str):
        return _fail(request, result)
    if flow["link"] is not None:
        return HttpResponseRedirect("/app/account")
    # A provider sign-in never skips the account's own second factor.
    if twofactor.enabled(result):
        twofactor.start_pending(request, result)
        return HttpResponseRedirect(f"/login?{urlencode({'two_factor': 1, 'next': flow['next']})}")
    login(request, result, backend=MODEL_BACKEND)
    security_event("auth.login", request, logging.INFO, user=result.pk, provider=provider)
    return HttpResponseRedirect(flow["next"])
