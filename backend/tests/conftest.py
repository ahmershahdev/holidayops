from collections.abc import Callable

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.accounts.models import User


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    cache.clear()


@pytest.fixture
def client() -> APIClient:
    return APIClient()


@pytest.fixture
def client_for() -> Callable[[User], APIClient]:
    def make(user: User) -> APIClient:
        client = APIClient()
        client.force_authenticate(user)
        return client

    return make
