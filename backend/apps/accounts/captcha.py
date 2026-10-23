"""Bot check for sign-up and the forms that send email. Docs: docs/security.md, "Bot check".

Two layers. A honeypot field people never see: anything typed into it means a script filled the
form, and the view answers as if it worked without doing anything. Then Google reCAPTCHA: v3
scores the request invisibly; a low score (or no v3 token) asks the page for a v2 checkbox,
which is verified on its own. With no keys configured (development, tests) only the honeypot
runs."""

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Literal

from django.conf import settings

logger = logging.getLogger(__name__)

VERIFY_URL = "https://www.google.com/recaptcha/api/siteverify"
TIMEOUT = 5
HONEYPOT = "website"

Result = Literal["ok", "challenge", "failed"]


@dataclass(frozen=True)
class Keys:
    v3_site: str
    v3_secret: str
    v2_site: str
    v2_secret: str

    @property
    def enabled(self) -> bool:
        return bool(self.v3_secret or self.v2_secret)


def keys() -> Keys:
    return Keys(**settings.RECAPTCHA)


def site_keys() -> dict[str, str | None]:
    k = keys()
    return {"v3": k.v3_site or None, "v2": k.v2_site or None}


def is_bot(data: Any) -> bool:
    return bool(isinstance(data, dict) and str(data.get(HONEYPOT, "")).strip())


def _siteverify(secret: str, token: str, ip: str | None) -> dict[str, Any] | None:
    fields = {"secret": secret, "response": token}
    if ip:
        fields["remoteip"] = ip
    request = urllib.request.Request(
        VERIFY_URL, data=urllib.parse.urlencode(fields).encode(), method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:  # noqa: S310
            answer: dict[str, Any] = json.loads(response.read())
            return answer
    except (urllib.error.URLError, TimeoutError, ValueError) as error:
        logger.warning("recaptcha.unreachable %s", type(error).__name__)
        return None


def check(data: Any, action: str, ip: str | None) -> Result:
    """`data` carries `captcha_v3` and/or `captcha_v2` tokens from the page."""
    k = keys()
    if not k.enabled:
        return "ok"
    data = data if isinstance(data, dict) else {}
    v2_token = str(data.get("captcha_v2") or "")[:4096]
    v3_token = str(data.get("captcha_v3") or "")[:4096]
    if v2_token and k.v2_secret:
        answer = _siteverify(k.v2_secret, v2_token, ip)
        return "ok" if answer and answer.get("success") else "failed"
    if v3_token and k.v3_secret:
        answer = _siteverify(k.v3_secret, v3_token, ip)
        if (
            answer
            and answer.get("success")
            and answer.get("action") == action
            and float(answer.get("score", 0)) >= settings.RECAPTCHA_MIN_SCORE
        ):
            return "ok"
    # No v3 key, a low score, or Google unreachable: a person can still pass the checkbox.
    return "challenge" if k.v2_secret else "failed"
