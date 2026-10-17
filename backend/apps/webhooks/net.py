"""Outbound HTTPS for webhooks, guarded against SSRF.

The host is resolved once, every address must be public, and the connection goes to that vetted
address with the original host name for SNI, certificate checks and the Host header, so a DNS
rebind between the check and the request can't point it somewhere internal.
"""

import http.client
import ipaddress
import socket
import ssl
import time
from dataclasses import dataclass
from urllib.parse import urlsplit

from django.utils.translation import gettext as _

CONNECT_TIMEOUT = 5
READ_TIMEOUT = 10
MAX_BODY = 4096


@dataclass(frozen=True)
class Target:
    host: str
    port: int
    path: str
    address: str


@dataclass(frozen=True)
class Result:
    status: int | None
    body: str
    duration_ms: int
    error: str


def _is_public(address: str) -> bool:
    ip = ipaddress.ip_address(address.split("%", 1)[0])
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    # 224.0.0.0/4 counts as global in `ipaddress`, but nothing should receive webhooks there.
    return ip.is_global and not ip.is_multicast


def resolve(host: str, port: int) -> list[str]:
    return [str(info[4][0]) for info in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)]


def vet(url: str) -> Target | str:
    """The connection target, or why the URL is refused (a message that is safe to show)."""
    parts = urlsplit(url)
    if parts.scheme != "https":
        return _("Webhook URLs must use https.")
    if parts.username or parts.password:
        return _("Webhook URLs must not contain credentials.")
    if not parts.hostname:
        return _("Webhook URL has no host.")
    try:
        port = parts.port or 443
    except ValueError:
        return _("Webhook URL has an invalid port.")
    try:
        addresses = resolve(parts.hostname, port)
    except OSError:
        return _("Webhook host does not resolve.")
    if not addresses or not all(_is_public(a) for a in addresses):
        return _("Webhook host must resolve to public addresses only.")
    path = parts.path or "/"
    if parts.query:
        path = f"{path}?{parts.query}"
    return Target(parts.hostname, port, path, addresses[0])


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, target: Target, context: ssl.SSLContext) -> None:
        super().__init__(target.host, target.port, timeout=CONNECT_TIMEOUT, context=context)
        self._address = target.address

    def connect(self) -> None:
        sock = socket.create_connection((self._address, self.port), CONNECT_TIMEOUT)
        sock.settimeout(READ_TIMEOUT)
        self.sock = self._context.wrap_socket(sock, server_hostname=self.host)  # type: ignore[attr-defined]


def post(target: Target, body: bytes, headers: dict[str, str]) -> Result:
    started = time.monotonic()
    connection = _PinnedHTTPSConnection(target, ssl.create_default_context())
    try:
        connection.request("POST", target.path, body=body, headers=headers)
        response = connection.getresponse()
        text = response.read(MAX_BODY).decode("utf-8", errors="replace")
        status, error = response.status, ""
    except (OSError, http.client.HTTPException) as exc:
        status, text, error = None, "", f"{type(exc).__name__}: {exc}"[:300]
    finally:
        connection.close()
    return Result(status, text, int((time.monotonic() - started) * 1000), error)
