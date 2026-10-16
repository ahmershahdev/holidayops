# Milestone 2 design: accounts, organizations, company calendars

## Auth

Session auth with CSRF (the SPA is same-origin). Passwords use Argon2; min length 10 plus Django's
common/numeric/similarity validators. Login and signup share an `auth` throttle (10/minute).

| Endpoint | Notes |
|---|---|
| `GET /api/v1/auth/csrf/` | Sets the CSRF cookie, returns `{"csrf_token": …}` |
| `POST /api/v1/auth/signup/` | `{email, password, name?}` → 201, logged in |
| `POST /api/v1/auth/login/` | `{email, password}`; email is case-insensitive |
| `POST /api/v1/auth/logout/` | 204 |
| `GET /api/v1/auth/me/` | Current user |

## Roles

| Action | viewer | member | admin | owner |
|---|---|---|---|---|
| Read org, members, calendars, custom days | ✓ | ✓ | ✓ | ✓ |
| Create/edit calendars and custom days | | ✓ | ✓ | ✓ |
| Delete calendars, rename org, manage members, read audit log | | | ✓ | ✓ |
| Grant/remove the owner role, delete org | | | | ✓ |

An org always keeps at least one owner. Non-members get `404` on every org URL, never `403`.

## Endpoints

```
GET POST           /api/v1/orgs/
GET PATCH DELETE   /api/v1/orgs/{org}/
GET POST           /api/v1/orgs/{org}/members/            {email, role}
PATCH DELETE       /api/v1/orgs/{org}/members/{id}/       {role}
GET                /api/v1/orgs/{org}/audit-log/
GET POST           /api/v1/orgs/{org}/calendars/
GET PATCH DELETE   /api/v1/orgs/{org}/calendars/{uuid}/
GET POST           /api/v1/orgs/{org}/calendars/{uuid}/custom-days/        ?year=
GET PATCH DELETE   /api/v1/orgs/{org}/calendars/{uuid}/custom-days/{id}/
```

Lists from generic views are paginated: `{"count", "next", "previous", "results"}`, 100 per page.

### Calendar body

```json
{"name": "Karachi + Riyadh offices", "is_public": false, "language": "en_US",
 "weekend": null, "sources": [{"country": "PK"}, {"country": "SA", "categories": ["public"]}]}
```

- 1–20 sources, each validated against the library. Sending `sources` replaces all of them.
- `weekend`: weekday numbers (Monday = 0) or `null` for the first source's own (per-date) rule.
- `language`: used for every source country that supports it; others use their default.

### Custom day body

`{"date": "2027-04-05", "name": "Office move", "kind": "closure" | "half_day" | "working_day"}`,
one per calendar per date.

## Business-day endpoints with a company calendar

Pass `calendar=<uuid>` instead of `country` (not both; `subdiv`, `language` and `categories` are
not allowed with it). Visible when the calendar `is_public` or the caller is a member of its org;
otherwise `404`.

New `reason` values: `closure`, `half_day` (working, `half_day: true`), `custom_working_day`.
Holiday lists gain `kind`: `holiday`, `closure` or `half_day`.

## Merge rules (`apps/core/merge.py`)

1. Sources are combined with the library's `HolidaySum`.
2. The weekend rule is pinned on the result: the company `weekend`, else the first source's own
   per-date rule. (`HolidaySum` alone would fall back to Sat–Sun.)
3. Custom days win: a closure adds a holiday; a half-day or extra working day removes any holiday on
   that date and makes it a working day even on a weekend.
4. Cached source calendars are never mutated.

## Audit log actions

`org.create`, `org.update`, `member.add`, `member.role_change`, `member.remove`, `calendar.create`,
`calendar.delete`.
