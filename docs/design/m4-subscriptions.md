# Milestone 4 design: Celery, iCal feeds, digests, webhooks

Four parts, one PR each, in this order: 4.1 Celery → 4.2 feeds → 4.3 digests → 4.4 webhooks.
Org invites by email (deferred from Milestone 2) follow 4.3, once email sending exists.

## 4.1 Celery

- App in `config/celery.py`, loaded from `config/__init__.py`; settings use the `CELERY_` prefix.
- Broker: Redis (`REDIS_URL`). No result backend: tasks write their outcome to the database
  (delivery log, `last_sent_on`), never to Celery results.
- Beat schedule lives in settings (`CELERY_BEAT_SCHEDULE`), UTC.
- Compose runs `worker` and `beat` from the backend image. `npm run dev` runs both locally;
  on Windows the worker uses `--pool=solo`.
- Tests run tasks eagerly (`CELERY_TASK_ALWAYS_EAGER`), so no broker is needed in CI.

### Task conventions

- A task lives in its app's `tasks.py` and is named `<app>.<verb>_<noun>`.
- Arguments are JSON primitives (IDs, ISO dates), never model instances; the JSON serializer is
  the only one accepted.
- Tasks are idempotent: running one twice has the same effect as once. They are acknowledged late
  and re-queued if a worker dies.
- Enqueue from views with `transaction.on_commit(lambda: task.delay(...))`, so a task never sees
  a row that was rolled back.
- Default limits: 30 s soft, 60 s hard. Retries are per task (`autoretry_for`, backoff, max).
- Fan-out: a Beat task selects IDs and enqueues one small task per item.

## 4.2 iCal feeds

`FeedToken(calendar, org, token_hash, label, created_by, created_at, last_used_at, revoked_at)`.

- Token: `secrets.token_urlsafe(32)`; only its SHA-256 hex is stored. The full URL is shown once,
  when created or rotated.
- `GET /feeds/<token>.ics` is public: no session, anonymous throttle. Unknown or revoked → `404`.
  Response: `text/calendar; charset=utf-8`, `ETag`, `Cache-Control: private, max-age=3600`.
- Content: last year through next year (UTC "today" picked in the view). One all-day `VEVENT` per
  holiday, closure and half-day; extra working days carry `CATEGORIES:WORKING-DAY`. Stable `UID`s
  (`<date>-<kind>@<calendar uuid>`), so clients update events instead of duplicating them.
- The `.ics` text is built by a small pure function in `apps/core/ical.py` (RFC 5545 escaping and
  75-octet UTF-8-safe line folding), so no new dependency. Built bytes are cached per calendar and
  year range; the key includes `calendar.updated_at`, and saving a custom day touches the calendar.
- Roles: member and up create, rotate and revoke; viewers list (labels and dates, never tokens).
  At most 10 active tokens per calendar. Create, rotate and revoke go to the audit log.

```
GET POST   /api/v1/orgs/{org}/calendars/{uuid}/feeds/               {label}
DELETE     /api/v1/orgs/{org}/calendars/{uuid}/feeds/{id}/          revoke
POST       /api/v1/orgs/{org}/calendars/{uuid}/feeds/{id}/rotate/   → new URL, old one revoked
```

## 4.3 Monthly digests

- Email settings from env: `EMAIL_BACKEND` (console by default), `EMAIL_HOST`, `EMAIL_PORT`,
  `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `DEFAULT_FROM_EMAIL`.
- `DigestSubscription(user, calendar, org, created_at, last_sent_on)`, unique per user and
  calendar. Any member, viewers included, opts in or out for themselves only.
- Beat on the 1st of each month, 06:00 UTC: `notifications.send_digests` enqueues
  `notifications.send_digest(subscription_id, run_date)` per subscription. The task skips if
  `last_sent_on` is already in that month, so retries and duplicate Beat runs send once.
- Body: holidays, closures and half-days in the 30 days from `run_date`, holiday names in the
  calendar's language, template text in the user's `language` (new field, default `en`). Plain
  text and HTML, `dir="rtl"` for ur/ar.
- One-click unsubscribe: a signed token (`django.core.signing`, salted per purpose) in the link
  and in `List-Unsubscribe` / `List-Unsubscribe-Post`.

```
GET PUT DELETE  /api/v1/orgs/{org}/calendars/{uuid}/digest/   current user's subscription
POST            /api/v1/digests/unsubscribe/                  {token}, no login needed
```

## 4.4 Webhooks

`Webhook(org, url, secret, events, is_active, created_by, created_at, failure_count)` and
`WebhookDelivery(webhook, event, payload, status, attempts, response_status, duration_ms, error,
created_at, next_attempt_at)`.

- Events: `calendar.updated`, `calendar.deleted`, `custom_day.created`, `custom_day.updated`,
  `custom_day.deleted`, `ping`. Payload: `{"id", "event", "created_at", "org", "data"}`.
- Secret: 32 random bytes, shown once on create and on rotate. It is stored as is, because
  signing needs it; the database is the trust boundary, as with any webhook provider.
- Headers: `X-HolidayOps-Event`, `X-HolidayOps-Delivery`, and
  `X-HolidayOps-Signature: t=<unix seconds>,v1=<hex HMAC-SHA256 of "<t>.<body>">`.
  Receivers should reject timestamps older than 5 minutes.
- SSRF guard, at save time and again before every attempt: `https` only, no credentials in the
  URL, resolve the host and reject unless every address is global (`ipaddress.is_global`), then
  connect to that vetted address with the original host for SNI and `Host`, so a DNS rebind
  can't swap it. No redirects. Timeouts 5 s connect, 10 s read; response body capped at 4 KB.
- Retries: network errors, `429` and `5xx` retry with backoff (1 min, 5 min, 30 min, 2 h, 12 h);
  other `4xx` fail at once. After 20 failed deliveries in a row the webhook is deactivated and the
  org admins see it in settings.
- Roles: admin and up. At most 10 webhooks per org. Create, rotate, delete go to the audit log.

```
GET POST           /api/v1/orgs/{org}/webhooks/
GET PATCH DELETE   /api/v1/orgs/{org}/webhooks/{id}/
POST               /api/v1/orgs/{org}/webhooks/{id}/rotate-secret/
POST               /api/v1/orgs/{org}/webhooks/{id}/ping/
GET                /api/v1/orgs/{org}/webhooks/{id}/deliveries/
```

Every new org endpoint above is added to `tests/test_isolation.py`.
