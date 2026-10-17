from config.settings.base import *  # noqa: F403
from config.settings.base import MIDDLEWARE, REST_FRAMEWORK

DEBUG = True
MIDDLEWARE = [*MIDDLEWARE, "config.errors.BrandedNotFoundMiddleware"]

REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
]
