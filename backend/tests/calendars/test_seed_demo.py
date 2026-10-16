import pytest
from django.core.management import CommandError, call_command

from apps.accounts.models import User
from apps.calendars.models import Calendar

pytestmark = pytest.mark.django_db


def test_seed_demo_is_idempotent(settings, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    settings.DEBUG = True
    monkeypatch.setenv("DEMO_PASSWORD", "demo-password-123")
    call_command("seed_demo")
    call_command("seed_demo")
    user = User.objects.get(email="demo@holidayops.test")
    assert user.check_password("demo-password-123")
    calendar = Calendar.objects.get(slug="karachi-riyadh")
    assert [s.country for s in calendar.sources.all()] == ["PK", "SA"]
    assert calendar.custom_days.count() == 3


def test_seed_demo_refuses_without_debug_or_password(settings, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    settings.DEBUG = False
    with pytest.raises(CommandError):
        call_command("seed_demo")
    settings.DEBUG = True
    monkeypatch.delenv("DEMO_PASSWORD", raising=False)
    with pytest.raises(CommandError):
        call_command("seed_demo")
