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
    # Set once the owner proves the mailbox (a code, a reset, or a provider that vouches for it).
    email_verified_at = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: ClassVar[list[str]] = []

    objects: ClassVar[UserManager] = UserManager()  # type: ignore[assignment]

    def __str__(self) -> str:
        return self.email

    @property
    def email_verified(self) -> bool:
        return self.email_verified_at is not None


class EmailCode(models.Model):
    """A one-time code emailed to prove the mailbox, for a password reset or to verify the
    address. Only an HMAC of the code is stored."""

    class Purpose(models.TextChoices):
        RESET = "reset"
        VERIFY = "verify"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="email_codes")
    purpose = models.CharField(max_length=10, choices=Purpose.choices, default=Purpose.RESET)
    code_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)

    class Meta:
        indexes: ClassVar = [models.Index(fields=["user", "created_at"])]

    def __str__(self) -> str:
        return f"{self.purpose} code for user {self.user_id}"


class TwoFactor(models.Model):
    """An authenticator-app secret. It has to stay readable to check codes, so it is stored as
    is; `confirmed_at` is set once the user proves their app produces matching codes."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="two_factor")
    secret = models.CharField(max_length=64)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    last_step = models.BigIntegerField(default=0)

    def __str__(self) -> str:
        return f"2FA for user {self.user_id}"


class RecoveryCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="recovery_codes")
    code_hash = models.CharField(max_length=64)
    used_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"recovery code for user {self.user_id}"


class SocialIdentity(models.Model):
    """A Google or Microsoft account linked by its stable subject id, never by email."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="identities")
    provider = models.CharField(max_length=20)
    subject = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    email_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints: ClassVar = [
            models.UniqueConstraint(fields=["provider", "subject"], name="unique_identity")
        ]

    def __str__(self) -> str:
        return f"{self.provider} identity of user {self.user_id}"
