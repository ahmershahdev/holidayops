# Security design

Reporting a vulnerability: see [SECURITY.md](../SECURITY.md).

## Authentication

- Web app: Django session auth with CSRF, same origin.
- Public API: `Authorization: Bearer hops_<prefix>_<secret>`. Keys are shown once and stored as a
  SHA-256 hash of a high-entropy secret. The prefix is stored in clear for lookup and display.
- Passwords use Argon2.

## Tenant isolation

- No query on org data without the org filter.
- A test suite tries cross-org access on every endpoint and expects `404`, never `403`, so object
  existence doesn't leak.

## Permissions

DRF permission classes per role. Viewers can't write; only owners manage billing and keys.

## Rate limiting

Redis-backed throttles per API key, and per IP for anonymous calls. Over the limit: `429` with
`Retry-After`.

## Input validation

- Country, subdivision, language and category are checked against the library's supported lists.
- Year range and range lengths are capped; `days` in `add` is capped. Limits live in
  [design/m1-api.md](design/m1-api.md).

## Feeds

iCal URLs carry a random token, stored hashed, revocable and rotatable.

## Webhooks

HMAC-SHA256 signature header, HTTPS only, private/loopback/link-local IPs blocked (SSRF, checked
after DNS resolution), timeouts, retries with backoff.

## HTTP headers and cookies

HTTPS only, HSTS, CSP, `X-Content-Type-Options: nosniff`, `Referrer-Policy`, secure + HttpOnly
cookies, `SameSite=Lax`.

## Secrets

Only from environment variables (`.env` locally, never committed; `.env.example` lists them).

## Audit log

Key creation and revocation, member and role changes, calendar deletion.

## Supply chain

Exact-pinned dependencies with a lock file, Dependabot, pip-audit, npm audit, CodeQL in CI.
