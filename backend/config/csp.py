from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

SWAGGER_CDN = "https://cdn.jsdelivr.net"

# The API only returns JSON; inline styles are allowed so Django's own error pages stay readable.
API_POLICY = (
    "default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'none'; "
    "base-uri 'none'; form-action 'none'"
)
DOCS_POLICY = (
    f"default-src 'self'; script-src 'self' {SWAGGER_CDN}; "
    f"style-src 'self' 'unsafe-inline' {SWAGGER_CDN}; img-src 'self' data: {SWAGGER_CDN}; "
    "frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
)
DOCS_PATH = "/api/v1/docs/"
# Nothing here uses a camera, microphone, location or payment API, so no page or embed may ask.
PERMISSIONS_POLICY = (
    "camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()"
)
# WhiteNoise answers before this middleware runs. An SVG opened directly is a document that
# could run script, so static SVGs get their own policy even though the flags are sanitised.
STATIC_SVG_POLICY = "default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'none'"


def static_headers(headers: dict[str, str], path: str, url: str) -> None:
    if path.endswith(".svg"):
        headers["Content-Security-Policy"] = STATIC_SVG_POLICY


class ContentSecurityPolicyMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        response.setdefault("Permissions-Policy", PERMISSIONS_POLICY)
        if "Content-Security-Policy" not in response:
            policy = DOCS_POLICY if request.path == DOCS_PATH else API_POLICY
            response["Content-Security-Policy"] = policy
        return response
