# Security design

Reporting a vulnerability: see [SECURITY.md](../SECURITY.md).

## Authentication

- Web app: Django session auth with CSRF, same origin.
- Public API: `Authorization: Bearer hops_<prefix>_<secret>`. Keys are shown once and stored as a
  SHA-256 hash of a high-entropy secret, compared in constant time. The prefix is stored in clear
  for lookup and display. Keys only authenticate the public endpoints; org management stays
  session-only. A key reaches its own org's private calendars and nothing else.
- Passwords use Argon2.

## Tenant isolation

- No query on org data without the org filter.
- A test suite tries cross-org access on every endpoint and expects `404`, never `403`, so object
  existence doesn't leak.

## Permissions

DRF permission classes per role. Viewers can't write; only owners manage billing and keys.

## Rate limiting

Redis-backed throttles per API key (rate from the org's plan), a monthly quota per org, and per IP
for anonymous calls. Over the limit: `429` with `Retry-After`.

- Login and signup: `auth` scope, 10/minute per IP. Invite creation: 30/hour per user.
- Public pages: 120 renders/minute per IP (`PUBLIC_PAGE_RATE`). Cached pages are served without
  counting, so only cache misses and landing-demo queries (never cached) use the budget.
- The client IP is `REMOTE_ADDR` unless `NUM_PROXIES` says how many proxies to trust in
  `X-Forwarded-For`. Left unset, DRF would take the whole header as the identity and anyone could
  dodge every per-IP limit by sending a new one per request (`tests/test_security.py`).

## Resource limits

Pending invites (50/org), webhooks (10/org), API keys (plan) and active feed links
(10/calendar) are checked and created under a MySQL named lock per owner
(`apps/orgs/limits.py`), so concurrent requests queue instead of all passing the count. A row lock
on the org would also block every usage and audit insert for that org while an invite email is
sent. If the lock isn't free in 10 s the request gets `409` and can be retried.
`tests/orgs/test_limits.py` races two requests against each limit.

## Security events

`config/security_log.py` logs one line per event on `holidayops.security` (console, so the host's
log stream collects it): `auth.login_failed` (warning), `auth.login`, `auth.signup`,
`api_key.invalid` (warning, key prefix only), `invite.wrong_account` (warning) and `rate_limited`
(warning for `auth`/`invite`, info otherwise). Each has the client IP and path. Passwords,
tokens, key secrets and email addresses are never logged; an email appears only as a 12-character
SHA-256 prefix to group attempts on one account. Field values are stripped of anything but
`[\w.:@/-]`, so user input can't forge extra log lines.

## Input validation

- Country, subdivision, language and category are checked against the library's supported lists.
- Year range and range lengths are capped; `days` in `add` is capped. Limits live in
  [design/m1-api.md](design/m1-api.md).

## Feeds

iCal URLs carry a random token, stored hashed, revocable and rotatable.

## Invites

Invite links carry a random token stored as a SHA-256 hash, valid once for 7 days. Accepting needs
a session whose email matches the invite, so a forwarded link can't be used by someone else. The
email is sent inside the request, so the raw token never sits in the Celery broker. Login and
signup only follow same-site `next` paths (`frontend/src/lib/navigation.ts`).

## Email

Digest unsubscribe links carry a signed subscription id (`django.core.signing`, purpose salt), so
they work without logging in and can't be forged for someone else's subscription. Email
credentials come from env only.

## Webhooks

HMAC-SHA256 signature header over `<timestamp>.<body>`, HTTPS only, no credentials in URLs, no
redirects. SSRF guard (`apps/webhooks/net.py`), at save time and before every attempt: resolve the
host, require every address to be global and not multicast (IPv4-mapped IPv6 unwrapped first),
then connect to that vetted address with the original host for SNI, certificate check and `Host`,
so DNS rebinding can't redirect it. 5 s connect and 10 s read timeouts, 4 KB response cap. Only
admins and owners manage webhooks.

## HTTP headers and cookies

HTTPS only, HSTS, CSP, `X-Content-Type-Options: nosniff`, `Referrer-Policy`, secure + HttpOnly
cookies, `SameSite=Lax`.

CSP (`backend/config/csp.py`): API responses get `default-src 'none'`. The Swagger page allows only
`'self'` and the jsDelivr CDN, uses the split view so it has no inline script, and loads an exact
`swagger-ui-dist` version (never `@latest`).

## Secrets

Only from environment variables (`.env` locally, never committed; `.env.example` lists them).

## Audit log

Key creation and revocation, member and role changes, calendar deletion.

## Supply chain

Exact-pinned dependencies with lock files, Dependabot (Actions, uv, npm), pip-audit, npm audit,
CodeQL (Python, TypeScript, Actions) in CI. The `main` ruleset requires the `backend`, `frontend`
and `codeql` checks to pass before a merge.
