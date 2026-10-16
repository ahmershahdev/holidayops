import uuid

from django.db import models

from apps.orgs.models import Organization


class Calendar(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="calendars")
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=60)
    is_public = models.BooleanField(default=False)
    language = models.CharField(max_length=10, blank=True)
    weekend = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["org", "slug"], name="unique_calendar_slug_per_org")
        ]
        ordering = ["name", "id"]

    def __str__(self) -> str:
        return self.name


class CalendarSource(models.Model):
    calendar = models.ForeignKey(Calendar, on_delete=models.CASCADE, related_name="sources")
    country = models.CharField(max_length=3)
    subdiv = models.CharField(max_length=10, blank=True)
    categories = models.JSONField(default=list, blank=True)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["position", "id"]

    def __str__(self) -> str:
        return f"{self.country}-{self.subdiv}" if self.subdiv else self.country


class CustomDayKind(models.TextChoices):
    CLOSURE = "closure"
    HALF_DAY = "half_day"
    WORKING_DAY = "working_day"


class CustomDay(models.Model):
    calendar = models.ForeignKey(Calendar, on_delete=models.CASCADE, related_name="custom_days")
    date = models.DateField()
    name = models.CharField(max_length=120)
    kind = models.CharField(max_length=12, choices=CustomDayKind.choices)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["calendar", "date"], name="unique_custom_day")
        ]
        ordering = ["date"]

    def __str__(self) -> str:
        return f"{self.date} {self.name}"
