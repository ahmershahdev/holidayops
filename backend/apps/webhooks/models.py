import secrets
import uuid

from django.conf import settings
from django.db import models

from apps.orgs.models import Organization
from config.crypto import EncryptedCharField

EVENTS = [
    "calendar.updated",
    "calendar.deleted",
    "custom_day.created",
    "custom_day.updated",
    "custom_day.deleted",
]
PING = "ping"


def new_secret() -> str:
    return f"whsec_{secrets.token_hex(32)}"


class Webhook(models.Model):
    org = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="webhooks")
    url = models.URLField(max_length=500)
    # Encrypted, not hashed: every delivery signs with it.
    secret = EncryptedCharField(max_length=255, default=new_secret)
    events = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)
    failure_count = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self) -> str:
        return self.url


class DeliveryStatus(models.TextChoices):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class WebhookDelivery(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    webhook = models.ForeignKey(Webhook, on_delete=models.CASCADE, related_name="deliveries")
    event = models.CharField(max_length=40)
    payload = models.JSONField()
    status = models.CharField(
        max_length=10, choices=DeliveryStatus.choices, default=DeliveryStatus.PENDING
    )
    attempts = models.PositiveSmallIntegerField(default=0)
    response_status = models.PositiveSmallIntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    error = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    next_attempt_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.event} → {self.webhook}"
