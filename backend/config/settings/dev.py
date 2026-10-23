from config.settings.base import *  # noqa: F403
from config.settings.base import CACHES, MIDDLEWARE, REST_FRAMEWORK, env

DEBUG = True
# The worker runs in its own process: only Redis lets the web process see its heartbeat.
CACHES = {
    **CACHES,
    "shared": {"BACKEND": "django_redis.cache.RedisCache", "LOCATION": env("REDIS_URL")},
}
MIDDLEWARE = [*MIDDLEWARE, "config.errors.BrandedNotFoundMiddleware"]

REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
]
