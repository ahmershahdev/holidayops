from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.template import loader
from django.utils import translation

from apps.public.content import PREFIX
from apps.public.frame import frame_context
from apps.public.views import PUBLIC_POLICY

JSON_PREFIXES = ("/api/", "/feeds/")


def not_found(request: HttpRequest, exception: Exception | None = None) -> HttpResponse:
    """Branded 404 for pages, JSON for the API. The language follows the URL prefix."""
    if request.path.startswith(JSON_PREFIXES):
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
    response["Content-Security-Policy"] = PUBLIC_POLICY.replace(
        "style-src 'self'", "style-src 'self' 'unsafe-inline'"
    )
    return response


def server_error(request: HttpRequest) -> HttpResponse:
    """Plain template with no database or request context, so it renders even when those fail."""
    if request.path.startswith(JSON_PREFIXES):
        return JsonResponse({"detail": "Server error."}, status=500)
    return HttpResponse(loader.get_template("public/500.html").render(), status=500)
