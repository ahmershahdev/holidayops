from datetime import date
from typing import Any

import holidays
import pytest
from rest_framework.test import APIClient
from rest_framework.throttling import AnonRateThrottle


def get(client: APIClient, url: str, **params: Any) -> Any:
    return client.get(f"/api/v1/{url}", params)


def test_countries(client: APIClient) -> None:
    response = get(client, "countries/")
    assert response.status_code == 200
    sa = next(c for c in response.json() if c["code"] == "SA")
    assert sa["weekend"] == [4, 5]
    assert sa["name"] == "Saudi Arabia"


def test_holidays_list(client: APIClient) -> None:
    response = get(client, "holidays/", country="pk", year=2027, language="en_US")
    assert response.status_code == 200
    body = response.json()
    assert body["country"] == "PK"
    assert body["subdiv"] is None
    assert body["categories"] == ["public"]
    assert {"date": "2027-03-23", "name": "Pakistan Day", "kind": "holiday"} in body["holidays"]
    dates = [h["date"] for h in body["holidays"]]
    assert dates == sorted(dates)
    assert dates.count("2027-08-14") == 2


def test_holidays_language_changes_names(client: APIClient) -> None:
    body = get(client, "holidays/", country="PK", year=2027, language="ur_PK").json()
    names = {h["name"] for h in body["holidays"]}
    assert "Pakistan Day" not in names


def test_holidays_with_subdivision_and_categories(client: APIClient) -> None:
    body = get(
        client, "holidays/", country="US", subdiv="CA", year=2027, categories="public, government"
    ).json()
    assert body["subdiv"] == "CA"
    assert body["categories"] == ["government", "public"]


def test_check(client: APIClient) -> None:
    response = get(client, "business-days/check/", country="SA", date="2027-04-02")
    assert response.status_code == 200
    assert response.json() == {
        "date": "2027-04-02",
        "is_business_day": False,
        "reason": "weekend",
        "holidays": [],
        "half_day": False,
    }


def test_add(client: APIClient) -> None:
    response = get(client, "business-days/add/", country="PK", date="2027-03-20", days=5)
    assert response.json() == {"start": "2027-03-20", "days": 5, "result": "2027-03-29"}


@pytest.mark.parametrize("days", [-1000, 1000])
def test_add_at_the_cap_matches_an_auto_expanding_calendar(client: APIClient, days: int) -> None:
    start = date(2027, 1, 4)
    expected = holidays.country_holidays("PK").get_nth_working_day(start, days)
    body = get(client, "business-days/add/", country="PK", date=start.isoformat(), days=days).json()
    assert body["result"] == expected.isoformat()


def test_add_past_supported_years_is_400(client: APIClient) -> None:
    response = get(client, "business-days/add/", country="PK", date="2100-12-31", days=1)
    assert response.status_code == 400
    assert "non_field_errors" in response.json()


def test_between(client: APIClient) -> None:
    response = get(
        client, "business-days/between/", country="PK", start="2027-03-01", end="2027-03-31"
    )
    assert response.json() == {"start": "2027-03-01", "end": "2027-03-31", "business_days": 19}


@pytest.mark.parametrize(
    ("url", "params", "field"),
    [
        ("holidays/", {"year": 2027}, "country"),
        ("holidays/", {"country": "ZZ", "year": 2027}, "country"),
        ("holidays/", {"country": "PK", "year": 1969}, "year"),
        ("holidays/", {"country": "PK", "year": 2027, "subdiv": "ZZ"}, "subdiv"),
        ("holidays/", {"country": "PK", "year": 2027, "language": "xx"}, "language"),
        ("holidays/", {"country": "PK", "year": 2027, "categories": "nope"}, "categories"),
        ("business-days/check/", {"country": "PK", "date": "2027-02-30"}, "date"),
        ("business-days/check/", {"country": "PK", "date": "2101-01-01"}, "date"),
        ("business-days/add/", {"country": "PK", "date": "2027-01-01", "days": 1001}, "days"),
        (
            "business-days/between/",
            {"country": "PK", "start": "2027-02-01", "end": "2027-01-01"},
            "end",
        ),
        (
            "business-days/between/",
            {"country": "PK", "start": "2020-01-01", "end": "2030-12-31"},
            "end",
        ),
    ],
)
def test_bad_input_is_400_with_field(
    client: APIClient, url: str, params: dict[str, Any], field: str
) -> None:
    response = get(client, url, **params)
    assert response.status_code == 400
    assert field in response.json()


def test_schema_and_docs(client: APIClient) -> None:
    assert client.get("/api/v1/schema/").status_code == 200
    assert client.get("/api/v1/docs/").status_code == 200


def test_security_headers(client: APIClient) -> None:
    response = get(client, "countries/")
    assert response["X-Content-Type-Options"] == "nosniff"
    assert response["X-Frame-Options"] == "DENY"
    assert response["Referrer-Policy"] == "same-origin"


def test_anonymous_requests_are_throttled(
    client: APIClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(AnonRateThrottle, "THROTTLE_RATES", {"anon": "2/minute"})
    for _ in range(2):
        assert get(client, "countries/").status_code == 200
    response = get(client, "countries/")
    assert response.status_code == 429
    assert "Retry-After" in response


def test_between_uses_country_weekend(client: APIClient) -> None:
    body = get(
        client, "business-days/between/", country="AE", start="2027-01-01", end="2027-01-31"
    ).json()
    assert body["business_days"] == 20


def test_holidays_default_to_country_language_not_server_locale(client: APIClient) -> None:
    body = get(client, "holidays/", country="SA", year=2027).json()
    assert body["language"] == "ar"
    assert all(not h["name"].isascii() for h in body["holidays"])
