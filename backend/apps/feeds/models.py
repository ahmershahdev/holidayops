import hashlib
import secrets

from django.conf import settings
from django.db import models

from apps.calendars.models import Calendar
from apps.orgs.models import Organization


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class FeedToken(models.Model):
    org = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="feed_tokens")
    calendar = models.ForeignKey(Calendar, on_delete=models.CASCADE, related_name="feed_tokens")
    label = models.CharField(max_length=80, blank=True)
    token_hash = models.CharField(max_length=64, unique=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"{self.calendar}: {self.label or self.pk}"

    def set_new_token(self) -> str:
        token = secrets.token_urlsafe(32)
        self.token_hash = hash_token(token)
        return token
