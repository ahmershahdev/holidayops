from http import HTTPStatus
from typing import Any
from uuid import UUID

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.holiday_list import HolidayList
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    calendar: UUID | Unset = UNSET,
    categories: str | Unset = UNSET,
    country: str | Unset = UNSET,
    language: str | Unset = UNSET,
    subdiv: str | Unset = UNSET,
    year: int,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    json_calendar: str | Unset = UNSET
    if not isinstance(calendar, Unset):
        json_calendar = str(calendar)
    params["calendar"] = json_calendar

    params["categories"] = categories

    params["country"] = country

    params["language"] = language

    params["subdiv"] = subdiv

    params["year"] = year

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/holidays/",
        "params": params,
    }

    return _kwargs


def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> HolidayList | None:
    if response.status_code == 200:
        response_200 = HolidayList.from_dict(response.json())

        return response_200

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[HolidayList]:
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
    language: str | Unset = UNSET,
    subdiv: str | Unset = UNSET,
    year: int,
) -> Response[HolidayList]:
    """
    Args:
        calendar (UUID | Unset):
        categories (str | Unset):
        country (str | Unset):
        language (str | Unset):
        subdiv (str | Unset):
        year (int):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HolidayList]
    """

    kwargs = _get_kwargs(
        calendar=calendar,
        categories=categories,
        country=country,
        language=language,
        subdiv=subdiv,
        year=year,
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
    language: str | Unset = UNSET,
    subdiv: str | Unset = UNSET,
    year: int,
) -> HolidayList | None:
    """
    Args:
        calendar (UUID | Unset):
        categories (str | Unset):
        country (str | Unset):
        language (str | Unset):
        subdiv (str | Unset):
        year (int):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HolidayList
    """

    return sync_detailed(
        client=client,
        calendar=calendar,
        categories=categories,
        country=country,
        language=language,
        subdiv=subdiv,
        year=year,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    calendar: UUID | Unset = UNSET,
    categories: str | Unset = UNSET,
    country: str | Unset = UNSET,
    language: str | Unset = UNSET,
    subdiv: str | Unset = UNSET,
    year: int,
) -> Response[HolidayList]:
    """
    Args:
        calendar (UUID | Unset):
        categories (str | Unset):
        country (str | Unset):
        language (str | Unset):
        subdiv (str | Unset):
        year (int):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HolidayList]
    """

    kwargs = _get_kwargs(
        calendar=calendar,
        categories=categories,
        country=country,
        language=language,
        subdiv=subdiv,
        year=year,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    calendar: UUID | Unset = UNSET,
    categories: str | Unset = UNSET,
    country: str | Unset = UNSET,
    language: str | Unset = UNSET,
    subdiv: str | Unset = UNSET,
    year: int,
) -> HolidayList | None:
    """
    Args:
        calendar (UUID | Unset):
        categories (str | Unset):
        country (str | Unset):
        language (str | Unset):
        subdiv (str | Unset):
        year (int):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HolidayList
    """

    return (
        await asyncio_detailed(
            client=client,
            calendar=calendar,
            categories=categories,
            country=country,
            language=language,
            subdiv=subdiv,
            year=year,
        )
    ).parsed
