import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from unittest import mock

import pytest

from apps.webhooks import net
from tests.webhooks.conftest import PUBLIC_IP, addrinfo

REAL_RESOLVE = net.resolve


def test_public_https_url_is_accepted(dns: mock.MagicMock) -> None:
    target = net.vet("https://hooks.example.com:8443/in?team=ops")
    assert target == net.Target("hooks.example.com", 8443, "/in?team=ops", PUBLIC_IP)
    assert net.vet("https://hooks.example.com") == net.Target(
        "hooks.example.com", 443, "/", PUBLIC_IP
    )


@pytest.mark.parametrize(
    "url",
    [
        "http://hooks.example.com/",
        "ftp://hooks.example.com/",
        "https://user:pass@hooks.example.com/",
        "https:///nohost",
        "https://hooks.example.com:99999/",
    ],
)
def test_bad_urls_are_rejected(url: str) -> None:
    assert isinstance(net.vet(url), str)


@pytest.mark.parametrize(
    "address",
    [
        "127.0.0.1",
        "10.1.2.3",
        "172.16.0.1",
        "192.168.1.1",
        "169.254.169.254",
        "100.64.0.1",
        "0.0.0.0",
        "224.0.0.1",
        "::1",
        "fe80::1%eth0",
        "fd00::1",
        "::ffff:127.0.0.1",
    ],
)
def test_internal_addresses_are_rejected(dns: mock.MagicMock, address: str) -> None:
    dns.return_value = addrinfo(address)
    assert isinstance(net.vet("https://hooks.example.com/"), str)


def test_one_internal_address_among_public_ones_is_enough_to_reject(dns: mock.MagicMock) -> None:
    dns.return_value = addrinfo(PUBLIC_IP, "10.0.0.5")
    assert isinstance(net.vet("https://hooks.example.com/"), str)


def test_unresolvable_or_empty_hosts_are_rejected(dns: mock.MagicMock) -> None:
    dns.side_effect = OSError("no such host")
    assert isinstance(net.vet("https://nope.example.com/"), str)
    dns.side_effect = None
    dns.return_value = []
    assert isinstance(net.vet("https://nope.example.com/"), str)


class _Handler(BaseHTTPRequestHandler):
    seen: list[dict[str, Any]] = []

    def do_POST(self) -> None:
        length = int(self.headers["Content-Length"])
        _Handler.seen.append(
            {"path": self.path, "headers": dict(self.headers), "body": self.rfile.read(length)}
        )
        self.send_response(201)
        self.end_headers()
        self.wfile.write(b"x" * (net.MAX_BODY + 100))

    def log_message(self, *args: Any) -> None:
        pass


@pytest.fixture
def local_server() -> Iterator[int]:
    server = HTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server.server_address[1]
    server.shutdown()


class _PlainContext:
    """Stands in for TLS so a local plain-HTTP server can play the receiver."""

    def __init__(self) -> None:
        self.server_hostname: str | None = None

    def wrap_socket(self, sock: Any, server_hostname: str) -> Any:
        self.server_hostname = server_hostname
        return sock


def test_post_connects_to_the_vetted_address_with_the_original_host(local_server: int) -> None:
    _Handler.seen.clear()
    context = _PlainContext()
    target = net.Target("hooks.example.com", local_server, "/in?x=1", "127.0.0.1")
    with mock.patch("apps.webhooks.net.ssl.create_default_context", return_value=context):
        result = net.post(target, b'{"a":1}', {"X-Test": "yes"})
    assert result.status == 201
    assert result.error == ""
    assert len(result.body) == net.MAX_BODY
    assert context.server_hostname == "hooks.example.com"
    request = _Handler.seen[0]
    assert request["path"] == "/in?x=1"
    assert request["headers"]["Host"] == f"hooks.example.com:{local_server}"
    assert request["headers"]["X-Test"] == "yes"
    assert request["body"] == b'{"a":1}'


def test_post_reports_network_errors() -> None:
    target = net.Target("hooks.example.com", 443, "/", PUBLIC_IP)
    with mock.patch(
        "apps.webhooks.net.socket.create_connection", side_effect=ConnectionRefusedError("no")
    ):
        result = net.post(target, b"{}", {})
    assert result.status is None
    assert result.error.startswith("ConnectionRefusedError")


def test_real_lookup_of_localhost_is_rejected(dns: mock.MagicMock) -> None:
    dns.side_effect = REAL_RESOLVE
    assert isinstance(net.vet("https://localhost/"), str)
