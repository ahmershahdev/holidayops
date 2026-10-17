from typing import Any

from config.csp import static_headers
from config.settings.base import *  # noqa: F403
from config.settings.base import DATABASES, MIDDLEWARE, SPA_DIR, env, env_list

# New objects rather than in-place edits: base's lists and dicts are shared with every module
# that star-imports it.

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("REDIS_URL"),
    }
}

CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

_db_options: dict[str, Any] = {**DATABASES["default"]["OPTIONS"]}
# Azure Database for MySQL (and most managed MySQL) only accepts TLS connections.
if ssl_mode := env("MYSQL_SSL_MODE", ""):
    _db_options["ssl_mode"] = ssl_mode
if ssl_ca := env("MYSQL_SSL_CA", ""):
    _db_options["ssl"] = {"ca": ssl_ca}
DATABASES = {
    "default": {
        **DATABASES["default"],
        "CONN_MAX_AGE": 60,
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": _db_options,
    }
}

_after_security = MIDDLEWARE.index("django.middleware.security.SecurityMiddleware") + 1
MIDDLEWARE = [
    *MIDDLEWARE[:_after_security],
    "whitenoise.middleware.WhiteNoiseMiddleware",
    *MIDDLEWARE[_after_security:],
]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
# WhiteNoise serves the web app's built files from the site root; config.spa serves its
# index.html for the app's routes.
WHITENOISE_ROOT = SPA_DIR
WHITENOISE_ADD_HEADERS_FUNCTION = static_headers

# DJANGO_HTTPS=false is only for running the production image locally over plain HTTP.
HTTPS = env("DJANGO_HTTPS", "true").lower() == "true"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = HTTPS
SECURE_HSTS_SECONDS = 63072000 if HTTPS else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = HTTPS
SECURE_HSTS_PRELOAD = HTTPS
SESSION_COOKIE_SECURE = HTTPS
CSRF_COOKIE_SECURE = HTTPS
