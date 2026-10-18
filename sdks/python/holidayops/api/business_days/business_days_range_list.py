import datetime
from http import HTTPStatus
from typing import Any
from uuid import UUID

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.check_result import CheckResult
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    calendar: UUID | Unset = UNSET,
    categories: str | Unset = UNSET,
    country: str | Unset = UNSET,
    end: datetime.date,
    language: str | Unset = UNSET,
    start: datetime.date,
    subdiv: str | Unset = UNSET,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    json_calendar: str | Unset = UNSET
    if not isinstance(calendar, Unset):
        json_calendar = str(calendar)
    params["calendar"] = json_calendar

    params["categories"] = categories

    params["country"] = country

    json_end = end.isoformat()
    params["end"] = json_end

    params["language"] = language

    json_start = start.isoformat()
    params["start"] = json_start

    params["subdiv"] = subdiv

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/business-days/range/",
        "params": params,
    }

    return _kwargs


def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> list[CheckResult] | None:
    if response.status_code == 200:
        response_200 = []
        _response_200 = response.json()
        for response_200_item_data in _response_200:
            response_200_item = CheckResult.from_dict(response_200_item_data)

            response_200.append(response_200_item)

        return response_200

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[list[CheckResult]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    calendar: UUID | Unset = UNSET,
    categories: str | Unset = UNSET,
    country: str | Unset = UNSET,
    end: datetime.date,
    language: str | Unset = UNSET,
    start: datetime.date,
    subdiv: str | Unset = UNSET,
) -> Response[list[CheckResult]]:
    """
    Args:
        calendar (UUID | Unset):
        categories (str | Unset):
        country (str | Unset):
        end (datetime.date):
        language (str | Unset):
        start (datetime.date):
        subdiv (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[list[CheckResult]]
    """

    kwargs = _get_kwargs(
        calendar=calendar,
        categories=categories,
        country=country,
        end=end,
        language=language,
        start=start,
        subdiv=subdiv,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    calendar: UUID | Unset = UNSET,
    categories: str | Unset = UNSET,
    country: str | Unset = UNSET,
    end: datetime.date,
    language: str | Unset = UNSET,
    start: datetime.date,
    subdiv: str | Unset = UNSET,
) -> list[CheckResult] | None:
    """
    Args:
        calendar (UUID | Unset):
        categories (str | Unset):
        country (str | Unset):
        end (datetime.date):
        language (str | Unset):
        start (datetime.date):
        subdiv (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        list[CheckResult]
    """

    return sync_detailed(
        client=client,
        calendar=calendar,
        categories=categories,
        country=country,
        end=end,
        language=language,
        start=start,
        subdiv=subdiv,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    calendar: UUID | Unset = UNSET,
    categories: str | Unset = UNSET,
    country: str | Unset = UNSET,
    end: datetime.date,
    language: str | Unset = UNSET,
    start: datetime.date,
    subdiv: str | Unset = UNSET,
) -> Response[list[CheckResult]]:
    """
    Args:
        calendar (UUID | Unset):
        categories (str | Unset):
        country (str | Unset):
        end (datetime.date):
        language (str | Unset):
        start (datetime.date):
        subdiv (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[list[CheckResult]]
    """

    kwargs = _get_kwargs(
        calendar=calendar,
        categories=categories,
        country=country,
        end=end,
        language=language,
        start=start,
        subdiv=subdiv,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    calendar: UUID | Unset = UNSET,
    categories: str | Unset = UNSET,
    country: str | Unset = UNSET,
    end: datetime.date,
    language: str | Unset = UNSET,
    start: datetime.date,
    subdiv: str | Unset = UNSET,
) -> list[CheckResult] | None:
    """
    Args:
        calendar (UUID | Unset):
        categories (str | Unset):
        country (str | Unset):
        end (datetime.date):
        language (str | Unset):
        start (datetime.date):
        subdiv (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        list[CheckResult]
    """

    return (
        await asyncio_detailed(
            client=client,
            calendar=calendar,
            categories=categories,
            country=country,
            end=end,
            language=language,
            start=start,
            subdiv=subdiv,
        )
    ).parsed
