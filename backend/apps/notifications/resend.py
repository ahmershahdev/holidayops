"""Django email backend for Resend's HTTP API (https://resend.com/docs/api-reference/emails).
Plain urllib, so no SDK to pin; every existing email (invites, digests, reset codes) uses it."""

import json
import logging
import urllib.error
import urllib.request
from collections.abc import Sequence
from typing import Any

from django.conf import settings
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)

API_URL = "https://api.resend.com/emails"
TIMEOUT = 10


def payload(message: EmailMessage) -> dict[str, Any]:
    data: dict[str, Any] = {
        "from": message.from_email or settings.DEFAULT_FROM_EMAIL,
        "to": list(message.to),
        "subject": message.subject,
        "text": message.body,
    }
    if message.cc:
        data["cc"] = list(message.cc)
    if message.bcc:
        data["bcc"] = list(message.bcc)
    if message.reply_to:
        data["reply_to"] = list(message.reply_to)
    if isinstance(message, EmailMultiAlternatives):
        html = next((body for body, kind in message.alternatives if kind == "text/html"), None)
        if html is not None:
            data["html"] = html
    return data


class ResendEmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages: Sequence[EmailMessage]) -> int:
        sent = 0
        for message in email_messages:
            if not message.recipients():
                continue
            request = urllib.request.Request(
                API_URL,
                data=json.dumps(payload(message)).encode(),
                headers={
                    "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                    "Content-Type": "application/json",
                    "User-Agent": "HolidayOps",
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=TIMEOUT) as response:  # noqa: S310
                    response.read()
                sent += 1
            except (urllib.error.URLError, TimeoutError) as error:
                # Log the status only: the body can echo the recipient's address.
                status = getattr(error, "code", None)
                logger.warning("resend.failed status=%s", status)
                if not self.fail_silently:
                    raise
        return sent
