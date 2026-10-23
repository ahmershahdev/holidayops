import os

os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-not-a-secret")
os.environ.setdefault("FIELD_ENCRYPTION_KEYS", "dGVzdC1vbmx5LWtleS1ub3QtYS1zZWNyZXQtMDAwMDA=")

from config.settings.base import *  # noqa: F403

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
APP_URL = "https://app.holidayops.test"

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Real keys in a developer's .env must not change what the tests see.
RECAPTCHA = {"v3_site": "", "v3_secret": "", "v2_site": "", "v2_secret": ""}
SSO_CLIENTS = {"google": ("", ""), "microsoft": ("", "")}
RESEND_API_KEY = ""
