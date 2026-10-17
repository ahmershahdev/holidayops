from django.conf import settings
from django.http import Http404, HttpRequest, HttpResponse

from apps.public.theme import get_theme

# The built app's scripts, styles and fonts are all same-origin files; React sets inline styles
# through the DOM, which style-src doesn't restrict.
SPA_POLICY = (
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
    "font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; "
    "form-action 'self'; frame-ancestors 'none'"
)


def spa(request: HttpRequest) -> HttpResponse:
    """index.html of the web app for its client-side routes (/, /login, /app/…)."""
    index = settings.SPA_DIR / "index.html"
    if not index.is_file():
        raise Http404("The web app isn't built: run `npm run build` in frontend/.")
    # Write the saved theme into the page, so a dark choice never flashes light on load.
    html = index.read_text(encoding="utf-8").replace(
        'data-theme="system"', f'data-theme="{get_theme(request)}"', 1
    )
    response = HttpResponse(html, content_type="text/html; charset=utf-8")
    # The file names its hashed assets, so it must never be cached past a deploy.
    response["Cache-Control"] = "no-cache"
    response["Content-Security-Policy"] = SPA_POLICY
    return response
