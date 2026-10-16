from config.settings.base import *  # noqa: F403
from config.settings.base import REST_FRAMEWORK

DEBUG = True

REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
]
