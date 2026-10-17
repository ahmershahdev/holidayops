from django.conf import settings
from django.db import models

from apps.calendars.models import Calendar
from apps.orgs.models import Organization


class DigestSubscription(models.Model):
    org = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="+")
    calendar = models.ForeignKey(Calendar, on_delete=models.CASCADE, related_name="digests")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="digests"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_sent_on = models.DateField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "calendar"], name="unique_digest_per_user")
        ]

    def __str__(self) -> str:
        return f"{self.user} ← {self.calendar}"
