import secrets

from django.conf import settings
from django.http import Http404, HttpRequest, HttpResponse

from apps.public.theme import get_theme

NONCE_PLACEHOLDER = "CSP_NONCE_PLACEHOLDER"
RECAPTCHA = "https://www.google.com/recaptcha/ https://www.gstatic.com/recaptcha/"
RECAPTCHA_FRAMES = "https://www.google.com/recaptcha/ https://recaptcha.google.com/recaptcha/"


def spa_policy(nonce: str) -> str:
    """Scripts run only with this response's nonce; 'strict-dynamic' lets them load others
    (the app's lazy chunks, Google reCAPTCHA) without an allowlist an attacker could use. React
    sets inline styles through the DOM, which style-src doesn't restrict."""
    return (
        f"default-src 'self'; script-src 'nonce-{nonce}' 'strict-dynamic'; style-src 'self'; "
        f"img-src 'self' data: https://www.gstatic.com/recaptcha/; font-src 'self'; "
        f"connect-src 'self' {RECAPTCHA}; frame-src {RECAPTCHA_FRAMES}; object-src 'none'; "
        "base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
    )


# Signed-in screens and one-off links stay out of search; the playground and sign-up are public.
PRIVATE_PREFIXES = ("/app", "/invite", "/unsubscribe", "/forgot-password")


def spa(request: HttpRequest) -> HttpResponse:
    """index.html of the web app for its client-side routes (/, /login, /app/…)."""
    index = settings.SPA_DIR / "index.html"
    if not index.is_file():
        raise Http404("The web app isn't built: run `npm run build` in frontend/.")
    # Write the saved theme into the page, so a dark choice never flashes light on load.
    html = index.read_text(encoding="utf-8").replace(
        'data-theme="system"', f'data-theme="{get_theme(request)}"', 1
    )
    if request.path.startswith(PRIVATE_PREFIXES):
        html = html.replace("<head>", '<head>\n    <meta name="robots" content="noindex" />', 1)
    nonce = secrets.token_urlsafe(18)
    html = html.replace(NONCE_PLACEHOLDER, nonce)
    response = HttpResponse(html, content_type="text/html; charset=utf-8")
    # The file names its hashed assets, so it must never be cached past a deploy.
    response["Cache-Control"] = "no-cache"
    response["Content-Security-Policy"] = spa_policy(nonce)
    return response
