from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any
from unittest import mock

import pytest

from apps.webhooks import net

PUBLIC_IP = "93.184.216.34"


def addrinfo(*addresses: str) -> list[str]:
    return list(addresses)


@pytest.fixture(autouse=True)
def dns() -> Iterator[mock.MagicMock]:
    with mock.patch("apps.webhooks.net.resolve") as resolve:
        resolve.return_value = addrinfo(PUBLIC_IP)
        yield resolve


@dataclass
class FakeReceiver:
    status: int | None = 200
    error: str = ""
    calls: list[dict[str, Any]] = field(default_factory=list)

    def __call__(self, target: net.Target, body: bytes, headers: dict[str, str]) -> net.Result:
        self.calls.append({"target": target, "body": body, "headers": headers})
        return net.Result(self.status, "ok" if self.status else "", 12, self.error)


@pytest.fixture
def receiver() -> Iterator[FakeReceiver]:
    fake = FakeReceiver()
    with mock.patch("apps.webhooks.net.post", side_effect=fake):
        yield fake
