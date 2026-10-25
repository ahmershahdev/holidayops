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
  date: `CATEGORIES` is `HOLIDAY`, `CLOSURE`, `HALF-DAY` or `WORKING-DAY`; a custom day replaces
  the holidays on its date. `UID` is `<yyyymmdd>@<calendar uuid>`, so when a day changes, clients
  update the event instead of adding a second one. `TRANSP:TRANSPARENT` keeps free/busy free.
- Calendar apps send odd `Accept` headers, so the feed view ignores content negotiation.
  `If-None-Match` returns `304`. `last_used_at` is written at most once an hour.
- The `.ics` text is built by a small pure function in `apps/core/ical.py` (RFC 5545 escaping and
  75-octet UTF-8-safe line folding), so no new dependency. Built bytes are cached per calendar and
  year for an hour; the key includes `calendar.updated_at`, and saving or deleting a custom day
  touches the calendar (`CustomDay.save`/`delete`).
- Roles: member and up create, rotate and revoke; viewers list (labels and dates, never tokens).
  At most 10 active tokens per calendar. Create, rotate and revoke go to the audit log.

```
GET POST   /api/v1/orgs/{org}/calendars/{uuid}/feeds/               {label}
DELETE     /api/v1/orgs/{org}/calendars/{uuid}/feeds/{id}/          revoke
POST       /api/v1/orgs/{org}/calendars/{uuid}/feeds/{id}/rotate/   → new URL, old one revoked
```

## 4.3 Monthly digests

- Email settings from env: `EMAIL_BACKEND` (console by default), `EMAIL_HOST`, `EMAIL_PORT`,
  `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `DEFAULT_FROM_EMAIL`. `APP_URL` is
  the web app's origin, used for links in emails.
- `DigestSubscription(user, calendar, org, created_at, last_sent_on)`, unique per user and
  calendar. Any member, viewers included, opts in or out for themselves only.
- Beat on the 1st of each month, 06:00 UTC: `notifications.send_digests` enqueues
  `notifications.send_digest(subscription_id, run_date)` per subscription. The task skips if
  `last_sent_on` is already in that month, so retries and duplicate Beat runs send once.
- Before sending, the task checks the user is still a member of the calendar's org; if not, the
  subscription is deleted and nothing is sent. SMTP and network errors retry with backoff (5 max).
- Body: every day from `feed_events` in the 30 days starting at `run_date` (inclusive), holiday
  names in the calendar's language, template text and dates in the user's `language`. An empty
  period still sends a short "nothing coming up" email. Plain text and HTML, `dir="rtl"` for ur/ar.
- `User.language` (`en`/`ur`/`ar`): set from `Accept-Language` at signup and kept in step with
  the UI language switcher through `PATCH /api/v1/auth/me/` (`name`, `language`).
- One-click unsubscribe (RFC 8058): a signed subscription id (`django.core.signing`, own salt, no
  expiry) in `List-Unsubscribe` + `List-Unsubscribe-Post`, which mail clients POST to the API
  without a session; the email's own link opens `/unsubscribe?token=…` in the web app, which asks
  before posting. Unsubscribing twice is fine (`204`); a forged token gets `400`.

```
GET PUT DELETE  /api/v1/orgs/{org}/calendars/{uuid}/digest/   {subscribed, last_sent_on} for me
POST            /api/v1/digests/unsubscribe/                  {token} or ?token=, no login
```

## 4.4 Webhooks

`Webhook(org, url, secret, events, is_active, created_by, created_at, failure_count)` and
`WebhookDelivery(id: uuid, webhook, event, payload, status, attempts, response_status,
response_body, duration_ms, error, created_at, next_attempt_at)`.

- Events: `calendar.updated`, `calendar.deleted`, `custom_day.created`, `custom_day.updated`,
  `custom_day.deleted`, plus `ping` on request. Payload: `{"id", "event", "created_at", "org",
  "data"}`; `data` has `calendar {id, name, slug}` and, for custom days, `custom_day {id, date,
  name, kind}`. The calendar views emit them after saving; deliveries are queued on commit.
- Secret: `whsec_` + 32 random bytes in hex, shown once on create and on rotate. Signing needs it back, so
  it is encrypted (`EncryptedCharField`, `FIELD_ENCRYPTION_KEYS`), not hashed.
- Headers: `X-HolidayOps-Event`, `X-HolidayOps-Delivery`, and
  `X-HolidayOps-Signature: t=<unix seconds>,v1=<hex HMAC-SHA256 of "<t>.<body>">`.
  Receivers should reject timestamps older than 5 minutes.
- SSRF guard, at save time and again before every attempt: `https` only, no credentials in the
  URL, resolve the host and reject unless every address is global (`ipaddress.is_global`), then
  connect to that vetted address with the original host for SNI and `Host`, so a DNS rebind
  can't swap it. No redirects. Timeouts 5 s connect, 10 s read; response body capped at 4 KB.
- Retries: network errors, `429` and `5xx` retry with backoff (1 min, 5 min, 30 min, 2 h, 12 h),
  so at most 6 attempts; `3xx` and other `4xx` fail at once. Retries are scheduled in the
  database (`next_attempt_at`), not as Celery countdowns: Redis redelivers tasks whose ETA is past
  its 1 h visibility timeout. Beat runs `webhooks.retry_due` every minute.
- Each attempt first claims the delivery with a conditional `UPDATE` that pushes
  `next_attempt_at` 5 minutes out (a lease), so two workers never send the same attempt and a
  worker that dies mid-request leaves it due again.
- After 20 failed deliveries in a row the webhook is disabled and shows as such in org settings;
  re-enabling it clears the count. A success also clears it.
- The delivery log shows the last 50 deliveries per webhook.
- Roles: admin and up. At most 10 webhooks per org. Create, rotate, delete go to the audit log.

```
GET POST           /api/v1/orgs/{org}/webhooks/
GET PATCH DELETE   /api/v1/orgs/{org}/webhooks/{id}/
POST               /api/v1/orgs/{org}/webhooks/{id}/rotate-secret/
POST               /api/v1/orgs/{org}/webhooks/{id}/ping/
GET                /api/v1/orgs/{org}/webhooks/{id}/deliveries/
```

Every new org endpoint above is added to `tests/test_isolation.py`.
