from typing import Any, ClassVar

from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager["User"]):
    use_in_migrations = True

    def create_user(self, email: str, password: str | None = None, **extra: Any) -> "User":
        user = self.model(email=self.normalize_email(email), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str | None = None, **extra: Any) -> "User":
        return self.create_user(email, password, is_staff=True, is_superuser=True, **extra)


class User(AbstractUser):
    username = None  # type: ignore[assignment]
    first_name = None  # type: ignore[assignment]
    last_name = None  # type: ignore[assignment]
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=150, blank=True)
    language = models.CharField(max_length=5, choices=settings.LANGUAGES, default="en")

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: ClassVar[list[str]] = []

    objects: ClassVar[UserManager] = UserManager()  # type: ignore[assignment]

    def __str__(self) -> str:
        return self.email
