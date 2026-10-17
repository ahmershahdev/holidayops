# Milestone 1 design: public API

## Request flow

```
request → DRF view → serializer (parse + validate params) → apps/core function → serializer → JSON
```

Views hold no date logic. `apps/core` raises its own errors; the API layer maps them to `400`.

## Common query parameters

| Param | Rule |
|---|---|
| `country` | Required. ISO 3166-1 alpha-2 code supported by `holidays` (case-insensitive) |
| `subdiv` | Optional. Must be in the country's subdivision list |
| `language` | Optional. Must be in the country's `supported_languages`; default is the country's default language, never the server locale |
| `categories` | Optional, comma-separated. Each must be in `supported_categories`; default `public` |

## Limits

| Limit | Value | Why |
|---|---|---|
| Year range | 1970–2100 | Bounded work per request |
| `add` `days` | −1000 … 1000 | Caps the walk length |
| `between` span | ≤ 3660 days | About ten years |

## Endpoints

### `GET /api/v1/countries/`

```json
[{"code": "SA", "name": "Saudi Arabia", "subdivisions": [], "languages": ["ar", "en_US"],
  "default_language": "ar", "categories": ["public"], "weekend": [4, 5]}]
```

`weekend` uses Python weekday numbers (Monday = 0), as the library does.

### `GET /api/v1/holidays/?country=PK&year=2027&language=en_US`

```json
{"country": "PK", "subdiv": null, "year": 2027, "language": "en_US", "categories": ["public"],
 "holidays": [{"date": "2027-02-05", "name": "Kashmir Solidarity Day"}]}
```

Two holidays on the same date produce two entries. Sorted by date, then name.

### `GET /api/v1/business-days/check/?country=SA&date=2027-04-02`

```json
{"date": "2027-04-02", "is_business_day": false, "reason": "weekend", "holidays": []}
```

`reason` is one of:

- `working_day`: a normal working day,
- `weekend`: falls on the country's weekend (holiday names still listed if any),
- `holiday`: a weekday holiday,
- `weekend_workday`: a weekend day the country moved to a working day.

### `GET /api/v1/business-days/add/?country=PK&date=2027-03-20&days=5`

```json
{"start": "2027-03-20", "days": 5, "result": "2027-03-29"}
```

Counting starts from the day after `start` (or before, for negative `days`). `days=0` returns `start`
if it is a working day, otherwise the next working day (the library's `get_nth_working_day`).

### `GET /api/v1/business-days/between/?country=AE&start=2027-01-01&end=2027-01-31`

```json
{"start": "2027-01-01", "end": "2027-01-31", "business_days": 20}
```

Inclusive of both ends. `start` must not be after `end`.

## Errors

`400` with DRF's field-error shape: `{"days": ["Ensure this value is less than or equal to 1000."]}`.
`429` with `Retry-After` when throttled.

## Core API

```python
class CoreError(ValueError): ...           # base for all domain errors
class UnsupportedCountry(CoreError): ...
class UnsupportedSubdivision(CoreError): ...
class UnsupportedLanguage(CoreError): ...
class UnsupportedCategory(CoreError): ...
class YearNotCovered(CoreError): ...       # a computation left the calendar's years

@dataclass(frozen=True)
class BusinessDayResult:
    day: date
    is_business_day: bool
    reason: Reason                         # Literal["working_day","weekend","holiday","weekend_workday"]
    holidays: tuple[str, ...]

@dataclass(frozen=True)
class CountryInfo: code, name, subdivisions, languages, default_language, categories, weekend
```

- `get_calendar` validates its inputs, builds with `expand=False` and is wrapped in `lru_cache`
  (`years` and `categories` are normalised to sorted tuples before the cached call).
- `add_business_days` and `business_days_between` raise `YearNotCovered` if any day they touch is
  outside the calendar's years. The API asks for enough years up front: `add` requests
  `start.year … start.year ± (|days| // 150 + 1)`, clamped to the year range.

## Throttling

Anonymous: `60/minute` per IP (`apps.api.throttles.AnonRateThrottle`). Requests with an API key
skip it and get the plan's per-key rate and monthly quota instead
([m5-api-keys.md](m5-api-keys.md)). Cache backend: local memory in dev and test, Redis in prod.
