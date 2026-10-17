import os

os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-not-a-secret")

from config.settings.base import *  # noqa: F403

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
