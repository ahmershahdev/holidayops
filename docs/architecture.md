# Architecture

## Users and product

Payroll, HR, logistics and finance teams that need "is this a working day?" for many countries,
regions and their own company days off. They get:

- a public REST API (Milestone 1),
- organizations and company calendars that merge countries with their own closures (Milestone 2),
- a web UI in English, Urdu and Arabic, RTL and mobile friendly (Milestone 3),
- iCal feeds, monthly digests and webhooks (Milestone 4),
- API keys, per-plan rate limits, quotas and usage charts (Milestone 5).

## Public API

Versioned under `/api/v1/`. OpenAPI at `/api/v1/schema/`, Swagger UI at `/api/v1/docs/`.

| Endpoint | Purpose |
|---|---|
| `GET /countries/` | Supported countries with subdivisions, languages, categories, weekend |
| `GET /holidays/?country=PK&subdiv=&year=2027&language=ur_PK&categories=public` | Holiday list |
| `GET /business-days/check/?country=SA&date=2027-04-02` | Working day or not, and why |
| `GET /business-days/add/?country=PK&date=2027-03-20&days=5` | Add or subtract N working days |
| `GET /business-days/between/?country=AE&start=…&end=…` | Working days, inclusive of both ends |

Outside `/api/v1/`: `GET /feeds/<token>.ics`, a private iCal feed of a company calendar, and the
server-rendered public pages, sitemaps and robots.txt ([seo.md](seo.md)).

From Milestone 2 the same endpoints accept `calendar=<id>` instead of `country`. They also accept
`Authorization: Bearer hops_…` API keys (Milestone 5.1): [design/m5-api-keys.md](design/m5-api-keys.md).
Exact parameters, limits and response shapes: [design/m1-api.md](design/m1-api.md).

## Domain layer (`backend/apps/core/`)

Plain functions, no Django imports, 100% branch coverage. Views and serializers only call these.

```python
def get_calendar(country: str, subdiv: str | None, years: Iterable[int],
                 language: str | None, categories: tuple[str, ...]) -> HolidayBase: ...
def is_business_day(cal: HolidayBase, day: date) -> BusinessDayResult: ...
def add_business_days(cal: HolidayBase, start: date, n: int) -> date: ...
def business_days_between(cal: HolidayBase, start: date, end: date) -> int: ...
def check_calendar_args(country, subdiv, language, categories) -> CountryInfo: ...
def merge_calendars(sources: Sequence[HolidayBase], custom: Iterable[CustomDay],
                    weekend: Iterable[int] | None = None) -> MergedCalendar: ...
```

- Use the library's own weekend rules (e.g. Fri–Sat for SA), `weekend_workdays` (moved working
  days), `is_working_day`, `get_nth_working_day`, `get_working_days_count`.
- Dates are `datetime.date`. The API takes ISO dates; the client decides what "today" is.
- Calendars are built with `expand=False` for an explicit set of years, so a cached calendar never
  mutates. Callers ask for every year a computation can touch; the domain raises if it would step
  outside them.
- `is_business_day`, `add_business_days` and `business_days_between` accept a plain calendar or a
  `MergedCalendar`.
- Half-days count as working days in the maths and are flagged in the result.
- Merging uses the library's `HolidaySum`; custom days win over sources. Merge rules:
  [design/m2-orgs.md](design/m2-orgs.md).
- With no `language`, the country's default language is used, never the server locale.

## Caching

1. In-process LRU on `get_calendar` keyed by `(country, subdiv, years, language, categories)`.
2. Redis for serialized holiday lists (Milestone 1 ships the LRU; Redis lists come with load).

## Data model

- `User(email, name, language)`; `language` is `en`, `ur` or `ar` and picks the email language
- `Organization`, `Membership(user, org, role)` with roles `owner`, `admin`, `member`, `viewer`
- `Invite(org, email, role, token_hash, invited_by, expires_at, accepted_at)`
- `Calendar(id: uuid, org, name, slug, is_public, language, weekend)`
- `CalendarSource(calendar, country, subdiv, categories, position)`
- `CustomDay(calendar, date, name, kind: closure|half_day|working_day)`
- `ApiKey(org, name, prefix, key_hash, created_by, last_used_at, revoked_at)`; `Organization.plan`
  (`free`/`pro`) sets per-key rate, monthly quota and key count
- `FeedToken(org, calendar, label, token_hash, created_by, last_used_at, revoked_at)`
- `DigestSubscription(org, calendar, user, last_sent_on)`, one per user and calendar
- `Webhook(org, url, secret, events, is_active, failure_count)` and
  `WebhookDelivery(webhook, event, payload, status, attempts, response_status, next_attempt_at)`
- `UsageEvent(org, api_key, endpoint, status, created_at)`, kept 90 days
- `AuditLog(org, actor, action, target, created_at)`

Every org-owned model has an `org` foreign key; querysets are always filtered by the current org.

## Background jobs (Milestone 4)

Celery with a Redis broker and Celery Beat: monthly digests and webhook delivery. No result
backend; tasks record outcomes in the database. Task conventions:
[design/m4-subscriptions.md](design/m4-subscriptions.md).

## Internationalization

Django gettext (`.po` in `backend/locale/{ur,ar}`) and i18next on the frontend. Holiday names come
from the library's own translations (`language=`). Tailwind logical properties (`ms-`, `me-`) keep
layouts correct in RTL.

## Settings

`config/settings/{base,dev,test,prod}.py`, chosen by `DJANGO_SETTINGS_MODULE`. All secrets and
connection strings come from environment variables; `.env.example` lists them.
