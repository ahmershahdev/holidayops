from collections.abc import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.template import loader
from django.utils import translation

from apps.public.content import PREFIX
from apps.public.frame import frame_context
from apps.public.views import PUBLIC_POLICY

JSON_PREFIXES = ("/api/", "/feeds/")


def wants_json(request: HttpRequest) -> bool:
    """API clients get JSON; a browser that opens a missing /api/ URL gets the branded page.
    Browsers send text/html in Accept, fetch() and curl don't."""
    return request.path.startswith(JSON_PREFIXES) and "text/html" not in request.headers.get(
        "Accept", ""
    )


def not_found(request: HttpRequest, exception: Exception | None = None) -> HttpResponse:
    """Branded 404 for pages, JSON for API clients. The language follows the URL prefix."""
    if wants_json(request):
        return JsonResponse({"detail": "Not found."}, status=404)
    lang = next(
        (
            code
            for code, prefix in PREFIX.items()
            if prefix and request.path.startswith(prefix + "/")
        ),
        "en",
    )
    with translation.override(lang):
        context = {
            **frame_context(request, lang),
            "title": translation.gettext("Page not found"),
            "description": translation.gettext("This page doesn't exist."),
            "noindex": True,
        }
        response = render(request, "public/404.html", context, status=404)
    response["Content-Security-Policy"] = PUBLIC_POLICY
    return response


def server_error(request: HttpRequest) -> HttpResponse:
    """Plain template with no database or request context, so it renders even when those fail."""
    if wants_json(request):
        return JsonResponse({"detail": "Server error."}, status=500)
    return HttpResponse(loader.get_template("public/500.html").render(), status=500)


class BrandedNotFoundMiddleware:
    """With DEBUG on, Django answers 404s with its technical page instead of handler404;
    development should give the same page or JSON that production does."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        if (
            settings.DEBUG
            and response.status_code == 404
            and response.get("Content-Type", "").startswith("text/html")
        ):
            return not_found(request)
        return response
