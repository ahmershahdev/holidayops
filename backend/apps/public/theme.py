from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.utils.http import url_has_allowed_host_and_scheme

COOKIE = "theme"
THEMES = ("light", "dark")
ONE_YEAR = 365 * 24 * 3600


def get_theme(request: HttpRequest) -> str:
    """'light', 'dark', or 'system' (no choice yet: follow prefers-color-scheme)."""
    value = request.COOKIES.get(COOKIE, "")
    return value if value in THEMES else "system"


def set_theme(request: HttpRequest, choice: str) -> HttpResponse:
    """No-JS theme switch: store the choice in a cookie and go back. The web app writes the same
    cookie from JavaScript, so both halves of the site agree."""
    next_url = request.GET.get("next", "/")
    if not url_has_allowed_host_and_scheme(next_url, {request.get_host()}, request.is_secure()):
        next_url = "/"
    response = HttpResponseRedirect(next_url)
    if choice in THEMES:
        response.set_cookie(COOKIE, choice, max_age=ONE_YEAR, samesite="Lax", path="/")
    else:
        response.delete_cookie(COOKIE, path="/", samesite="Lax")
    return response
