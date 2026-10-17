from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.utils.http import url_has_allowed_host_and_scheme

COOKIE = "theme"
THEMES = ("light", "dark")
ONE_YEAR = 365 * 24 * 3600


def get_theme(request: HttpRequest) -> str:
    """'light', 'dark', or 'system' (no choice yet: follow prefers-color-scheme). Only these
    literals ever come back, so the value is safe to write into HTML."""
    value = request.COOKIES.get(COOKIE, "")
    if value == "light":
        return "light"
    if value == "dark":
        return "dark"
    return "system"


def set_theme(request: HttpRequest, choice: str) -> HttpResponse:
    """No-JS theme switch: store the choice in a cookie and go back. The web app writes the same
    cookie from JavaScript, so both halves of the site agree."""
    next_url = request.GET.get("next", "/")
    if url_has_allowed_host_and_scheme(next_url, {request.get_host()}, request.is_secure()):
        response = HttpResponseRedirect(next_url)
    else:
        response = HttpResponseRedirect("/")
    if choice == "light":
        response.set_cookie(COOKIE, "light", max_age=ONE_YEAR, samesite="Lax", path="/")
    elif choice == "dark":
        response.set_cookie(COOKIE, "dark", max_age=ONE_YEAR, samesite="Lax", path="/")
    else:
        response.delete_cookie(COOKIE, path="/", samesite="Lax")
    return response
