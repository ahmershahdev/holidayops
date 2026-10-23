# Security design

Reporting a vulnerability: see [SECURITY.md](../SECURITY.md).

## Authentication

- Web app: Django session auth with CSRF, same origin.
- Public API: `Authorization: Bearer hops_<prefix>_<secret>`. Keys are shown once and stored as a
  SHA-256 hash of a high-entropy secret, compared in constant time. The prefix is stored in clear
  for lookup and display. Keys only authenticate the public endpoints; org management stays
  session-only. A key reaches its own org's private calendars and nothing else.
- Passwords use Argon2.

## Email verification

`apps/accounts/codes.py`, `POST /api/v1/auth/signup/`, `/auth/verify/` and `/auth/verify/resend/`.

- Sign-up never signs in and never says whether the address is taken: it always answers `202`
  ("check your email"). A new address gets an unconfirmed account and a code (valid 1 hour, 5
  guesses). An address with a confirmed account is left unchanged and its owner gets a "someone
  tried to sign up" email with no code. Every branch hashes the password first and emails go
  through Celery, so response times don't tell the cases apart either.
- An unconfirmed account belongs to nobody yet: a later sign-up with the same address replaces
  its password and gets a fresh code, so squatting someone's address gains nothing. Unconfirmed
  accounts with no memberships or linked providers are deleted after 7 days
  (`accounts.prune_unverified`, nightly).
- Logging in to an unconfirmed account with the right password sends a new code instead of a
  session. A password reset, or a Google/Microsoft sign-in whose provider vouches for the same
  address, also confirms it.
- `verified_user()` (`apps/accounts/auth.py`) gates everything that reaches other people:
  creating an organization, sending or accepting invites, digests. Adding a member by email
  ignores unconfirmed accounts. Existing accounts were marked confirmed by the migration.

## Password reset

`apps/accounts/codes.py`, `POST /api/v1/auth/password/forgot/` and `/reset/`.

- A 6-digit code from `secrets.randbelow`, stored only as
  `HMAC-SHA256(SECRET_KEY, purpose + user id + code)` and compared in constant time. A database
  leak alone gives no live codes; a verification code can't be used as a reset code.
- Valid for 10 minutes and once: the row is locked (`select_for_update`) while it is checked and
  marked used, so two parallel requests can't both use it. Asking for a new code retires the old
  one. Five wrong guesses retire it too.
- "Forgot" answers `202` with the same text whether or not the account exists. At most 3 emails
  per address per hour, counting every purpose (inbox flooding), `password_reset` throttle 5/hour
  per IP, and `auth` 10/minute per IP on the reset step.
- A successful reset logs the user in, emails a "password changed" notice and, because the
  password hash changes, signs out every other session.
- Emails are queued to Celery (`accounts.send_email`) so every answer takes the same time; the code
  sits in the Redis broker until the worker sends it, which is inside the private network.

## Two-factor sign-in

`apps/accounts/totp.py` (RFC 6238 on RFC 4226, standard library only) and `twofactor.py`.

- Authenticator-app codes: SHA-1, 6 digits, 30 s steps, ±1 step of drift. The last accepted step
  is stored, so a code can't be replayed. The secret has to stay readable to check codes.
- 10 recovery codes (`xxxxx-xxxxx`, no ambiguous characters), stored as HMAC hashes, single use,
  shown once, regenerated with a valid code.
- Login with two-factor on answers `202 {"two_factor_required": true}` and keeps only
  `{user, time, tries}` in the session for 5 minutes and 5 tries; `/auth/2fa/verify/` finishes it.
- Neither a password reset nor a Google or Microsoft sign-in skips the code step.
- Turning it off needs the password (if the account has one) and a current code.

## Single sign-on

`apps/accounts/sso.py` and `sso_views.py`: Google and Microsoft over OpenID Connect, authorization
code flow with PKCE (S256), `state` and `nonce`, `prompt=select_account`, no SDK.

- The ID token is read from the token endpoint's TLS response (OIDC Core 3.1.3.7), so its signature
  isn't checked; `iss` (Google, or a Microsoft tenant URL), `aud`, `exp`, `iat` and `nonce` are.
- Accounts are matched by the provider's subject id (`SocialIdentity`). An existing password
  account is joined automatically only when Google says it verified the address; Microsoft's email
  claim is never trusted for that ("nOAuth"), so the user logs in and connects it from settings.
- A password reset removes identities linked on an unverified address.
- `next` must stay on this site. The last way into an account can't be unlinked.
- Providers appear only when `GOOGLE_CLIENT_ID/SECRET` or `MICROSOFT_CLIENT_ID/SECRET` are set.

## Account data

`GET /auth/me/export/` returns everything stored about the account and its organizations as JSON,
without passwords, hashes or secrets. `POST /auth/me/delete/` needs the email typed out and the
password, refuses while the user is the only owner of an organization with other members, deletes
organizations where the user was the only member, and keeps other organizations' history with the
actor set to null. Both share the `account_data` throttle (10/hour).

## Bot check

`apps/accounts/captcha.py`, on sign-up, forgot password and new verification codes only. The data
API and login are not behind it (login has per-account limits instead).

- Honeypot: a `website` field moved off-screen, with `tabindex=-1` and `aria-hidden`. If it has
  any value the view answers exactly as on success and does nothing (`auth.honeypot` is logged).
- Google reCAPTCHA v3 scores the request invisibly; the server checks `success`, the expected
  `action` and `RECAPTCHA_MIN_SCORE` (0.5). A low score, a missing token or Google being
  unreachable answers `400` with `"captcha": "v2"`, and the page shows the v2 checkbox, which is
  verified with its own secret key. No v2 keys: the request fails instead.
- The checkbox is drawn in the page's theme (redrawn if it changes) and switches to Google's
  compact size below 304 px. The floating v3 badge is hidden and each form shows Google's notice
  in text instead, as Google's terms allow.
- Keys come from `RECAPTCHA_V3_SITE_KEY`, `RECAPTCHA_V3_SECRET_KEY`, `RECAPTCHA_V2_SITE_KEY` and
  `RECAPTCHA_V2_SECRET_KEY`; with none set (development, tests) only the honeypot runs.

## Account notices

`apps/accounts/emails.py`. The owner is emailed when two-factor sign-in is turned on or off, new
recovery codes are made, a Google or Microsoft sign-in is linked to an existing account or
removed, the password changes, and when the account is deleted (sent before the row goes).

## Email delivery

`EMAIL_BACKEND=apps.notifications.resend.ResendEmailBackend` sends every email (reset codes,
invites, digests) through Resend's HTTPS API with `RESEND_API_KEY`; failures log the status code
only, never the address. `DEFAULT_FROM_EMAIL` must be on a domain verified in Resend (SPF, DKIM).

## CSRF and brute force

- Session writes need a CSRF token. DRF only checks it for signed-in users, so the anonymous
  auth endpoints (signup, login, forgot, reset, two-factor verify) add `CsrfProtected`: without it
  another site could sign a browser into the attacker's account (login CSRF).
- Logins are limited per IP (`auth`, 10/minute) and per account: 10 failures in 15 minutes lock
  that address for the rest of the window, so guesses spread over many IPs still stop.
- Two sign-ups with one address at the same moment: the row lock in `codes.register` serialises
  them and both get the same `202`.

## Injection and XSS

- SQL: only the Django ORM, which sends parameters separately from the query (the role PDO
  prepared statements play in PHP). No raw SQL with string formatting.
- HTML: Django templates (pages and emails) autoescape; React escapes text; JSON-LD is escaped
  like `json_script`; third-party SVGs pass an allowlist sanitiser.
- CSP blocks inline script everywhere and all script on public pages, so an injected tag can't run.
  Public pages also allow no inline styles (only the internal `/style/` guide does), so they need
  no nonce: there is nothing inline to allow.
- The web app's page (`config/spa.py`) uses a nonce: Vite stamps a placeholder on every script and
  module preload (`html.cspNonce`), and Django swaps in a fresh 144-bit value per response.
  `script-src 'nonce-…' 'strict-dynamic'` then lets those scripts load the app's lazy chunks and
  reCAPTCHA, while an injected `<script>` without the nonce never runs.
- `Permissions-Policy` turns off camera, microphone, location, payment and USB for every page.

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

Request size: bodies over 512 KB are refused with `413` before anything reads them
(`config.csp.BodySizeLimitMiddleware`; DRF reads JSON from the stream, past Django's own
`DATA_UPLOAD_MAX_MEMORY_SIZE` check). Gunicorn caps the request line (4094 bytes), header count
(60) and header size (8190 bytes), kills workers stuck for 30 s, and recycles each worker after
about 2000 requests.


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
