import hashlib
import secrets

from django.conf import settings
from django.db import models

from apps.orgs.models import Organization

KEY_PREFIX = "hops"


def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


class ApiKey(models.Model):
    org = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="api_keys")
    name = models.CharField(max_length=80)
    prefix = models.CharField(max_length=8, unique=True)
    key_hash = models.CharField(max_length=64)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"{self.name} ({self.prefix})"

    def set_new_key(self) -> str:
        prefix = secrets.token_hex(4)
        while ApiKey.objects.filter(prefix=prefix).exists():
            prefix = secrets.token_hex(4)
        key = f"{KEY_PREFIX}_{prefix}_{secrets.token_urlsafe(32)}"
        self.prefix = prefix
        self.key_hash = hash_key(key)
        return key


class UsageEvent(models.Model):
    org = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="+")
    api_key = models.ForeignKey(ApiKey, on_delete=models.CASCADE, related_name="usage")
    endpoint = models.CharField(max_length=60)
    status = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["org", "created_at"])]

    def __str__(self) -> str:
        return f"{self.endpoint} {self.status}"
