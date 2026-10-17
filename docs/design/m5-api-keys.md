# Milestone 5.1 design: API keys, plans, quotas, usage

## Keys

`ApiKey(org, name, prefix, key_hash, created_by, created_at, last_used_at, revoked_at)`.

- Format `hops_<prefix>_<secret>`: `prefix` is 8 hex characters (unique, stored in clear for
  lookup and display), `secret` is `secrets.token_urlsafe(32)`. Only the SHA-256 of the whole key
  is stored; it is compared with `hmac.compare_digest`. The key is shown once, on create.
- Sent as `Authorization: Bearer hops_…` to the public endpoints only (`/countries/`,
  `/holidays/`, `/business-days/*`). Org management stays session-only: a key there is ignored,
  so the request is anonymous and gets `403`.
- A key acts for its org: `calendar=<id>` works for that org's private calendars, as it does for
  a logged-in member. Unknown, malformed or revoked key → `401` with `WWW-Authenticate: Bearer`.
- `last_used_at` is written at most once a minute per key.
- Owners create and revoke keys; admins see the list and the usage. Create and revoke go to the
  audit log.

```
GET POST   /api/v1/orgs/{org}/api-keys/          {name}
DELETE     /api/v1/orgs/{org}/api-keys/{id}/     revoke
GET        /api/v1/orgs/{org}/usage/?days=30     daily counts + plan and quota state
```

## Plans

`Organization.plan`: `free` (default) or `pro`. There is no billing yet; an operator sets the plan
with `manage.py set_plan <org-slug> <plan>`. Limits live in settings and can be overridden from
env:

| Plan | Rate per key | Monthly quota per org | Active keys |
|---|---|---|---|
| free | 120/minute | 10,000 requests | 3 |
| pro | 1,200/minute | 1,000,000 requests | 20 |

- Rate: `ApiKeyRateThrottle`, keyed by the key's prefix. Anonymous calls keep the 60/minute per IP
  limit; keyed calls skip it.
- Quota: `QuotaThrottle` counts keyed requests per org per UTC month in the cache
  (`quota:<org id>:<yyyymm>`, Redis in prod). Over quota → `429` with `Retry-After` until the
  next month starts. Throttled requests don't count.
- Both answer `429` with `Retry-After`, like every other throttle.

## Usage

`UsageEvent(api_key, org, endpoint, status, created_at)`: one row per keyed request, written
after the response is built (`endpoint` is the URL name, e.g. `business-days-check`). Session and
anonymous calls aren't recorded.

- `GET /usage/` returns `{plan, rate, monthly_quota, used_this_month, max_keys, days: [{date,
  requests, failed}]}` for the last `days` (1–90, default 30) UTC days, zero-filled. `failed`
  counts `status >= 400` (not `errors`, which would shadow DRF's `Serializer.errors`).
- Beat `api.prune_usage` runs daily at 03:00 UTC and deletes events older than 90 days.

## UI

Org settings: "API keys" card (owners create and revoke; the new key is shown once with a copy
button), and "Usage" card with a 30-day bar chart and the month's quota bar.
