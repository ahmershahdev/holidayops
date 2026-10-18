import time

import pytest
from django.core import mail
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.accounts import resets, totp, twofactor
from apps.accounts.models import TwoFactor
from tests.factories import PASSWORD, UserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def fresh_throttles() -> None:
    cache.clear()


def current_code(secret: str, offset: int = 0) -> str:
    return totp.code_at(secret, int(time.time() // totp.STEP_SECONDS) + offset)


def test_rfc_6238_vectors() -> None:
    # RFC 6238 appendix B, SHA-1, last six digits.
    secret = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"  # base32 of "12345678901234567890"
    assert totp.code_at(secret, 59 // 30) == "287082"
    assert totp.code_at(secret, 1111111109 // 30) == "081804"
    assert totp.code_at(secret, 2000000000 // 30) == "279037"


def test_codes_allow_one_step_of_drift_and_never_replay() -> None:
    secret = totp.new_secret()
    now = 1_800_000_000.0
    step = int(now // 30)
    assert totp.matching_step(secret, totp.code_at(secret, step - 1), now, 0) == step - 1
    assert totp.matching_step(secret, totp.code_at(secret, step + 2), now, 0) is None
    assert totp.matching_step(secret, totp.code_at(secret, step), now, step) is None
    assert totp.provisioning_uri(secret, "a@b.com").startswith(
        "otpauth://totp/HolidayOps:a%40b.com?"
    )


def enable(client: APIClient) -> tuple[str, list[str]]:
    setup = client.post("/api/v1/auth/2fa/setup/").json()
    assert setup["qr"].startswith("data:image/svg+xml;base64,")
    confirmed = client.post("/api/v1/auth/2fa/confirm/", {"code": current_code(setup["secret"])})
    assert confirmed.status_code == 200
    return setup["secret"], confirmed.json()["recovery_codes"]


def test_setup_confirm_and_login_with_a_code() -> None:
    user = UserFactory.create(email="two@example.com")
    owner = APIClient()
    owner.force_login(user)
    secret, recovery = enable(owner)
    assert len(recovery) == twofactor.RECOVERY_CODES
    assert owner.get("/api/v1/auth/me/").json()["two_factor"] is True

    client = APIClient()
    step_one = client.post("/api/v1/auth/login/", {"email": user.email, "password": PASSWORD})
    assert step_one.status_code == 202
    assert step_one.json() == {"two_factor_required": True}
    assert client.get("/api/v1/auth/me/").status_code == 403
    TwoFactor.objects.filter(user=user).update(last_step=0)
    step_two = client.post("/api/v1/auth/2fa/verify/", {"code": current_code(secret)})
    assert step_two.status_code == 200
    assert client.get("/api/v1/auth/me/").status_code == 200


def test_recovery_codes_work_once() -> None:
    user = UserFactory.create()
    owner = APIClient()
    owner.force_login(user)
    _secret, recovery = enable(owner)
    for expected in (200, 400):
        client = APIClient()
        client.post("/api/v1/auth/login/", {"email": user.email, "password": PASSWORD})
        response = client.post("/api/v1/auth/2fa/verify/", {"code": recovery[0].upper()})
        assert response.status_code == expected
    assert twofactor.recovery_codes_left(user) == twofactor.RECOVERY_CODES - 1


def test_the_code_step_gives_up_after_five_tries() -> None:
    user = UserFactory.create()
    owner = APIClient()
    owner.force_login(user)
    secret, _codes = enable(owner)
    client = APIClient()
    client.post("/api/v1/auth/login/", {"email": user.email, "password": PASSWORD})
    for _ in range(twofactor.PENDING_TRIES):
        client.post("/api/v1/auth/2fa/verify/", {"code": "000000"})
    TwoFactor.objects.filter(user=user).update(last_step=0)
    assert (
        client.post("/api/v1/auth/2fa/verify/", {"code": current_code(secret)}).status_code == 400
    )


def test_verify_without_a_password_step_fails(client: APIClient) -> None:
    assert client.post("/api/v1/auth/2fa/verify/", {"code": "123456"}).status_code == 400


def test_password_reset_does_not_skip_the_second_factor() -> None:
    user = UserFactory.create()
    owner = APIClient()
    owner.force_login(user)
    enable(owner)
    resets.request_reset(user.email)
    code = next(w for w in str(mail.outbox[-1].body).split() if w.isdigit() and len(w) == 6)
    client = APIClient()
    body = {"email": user.email, "code": code, "password": "another-long-passphrase-9"}
    response = client.post("/api/v1/auth/password/reset/", body)
    assert response.status_code == 202
    assert client.get("/api/v1/auth/me/").status_code == 403


def test_disable_needs_the_password_and_a_code() -> None:
    user = UserFactory.create()
    client = APIClient()
    client.force_login(user)
    secret, _codes = enable(client)
    TwoFactor.objects.filter(user=user).update(last_step=0)
    wrong = client.post(
        "/api/v1/auth/2fa/disable/", {"password": "nope", "code": current_code(secret)}
    )
    assert wrong.status_code == 400
    ok = client.post(
        "/api/v1/auth/2fa/disable/", {"password": PASSWORD, "code": current_code(secret)}
    )
    assert ok.status_code == 204
    assert not twofactor.enabled(user)


def test_setup_twice_is_refused_once_enabled() -> None:
    user = UserFactory.create()
    client = APIClient()
    client.force_login(user)
    enable(client)
    assert client.post("/api/v1/auth/2fa/setup/").status_code == 409
