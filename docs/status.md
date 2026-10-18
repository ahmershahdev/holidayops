# Project status

Last updated: 2026-10-18 (through #44). Update at the end of every work session.

## Run it

`npm run dev`, then <http://localhost:5173>. `npm run seed` creates `demo@holidayops.test` with the
password from `DEMO_PASSWORD` in `.env`. Docker Desktop must be running.

## Where we are

All six milestones are done in code; see [roadmap.md](roadmap.md). Hosting waits for launch
(owner decision, 2026-10-17: around GSoC 2027, Azure likely).

Recent work:

| PR | What |
|---|---|
| #36 | Landing redesign with live data (who is off today, weekend patterns, upcoming holidays, FAQ); about, contact, privacy, terms, offline pages; breadcrumbs; titles ≤ 60 and descriptions ≤ 150 (tested); JSON-LD graph; llms.txt, llms-full.txt; manifest and service worker; owner and support email in the footer |
| #37 | README with screenshots, architecture and ERD; CONTRIBUTING, SECURITY; shorter AGENTS.md, roadmap and status |
| #38 | Branded 404 for browsers on missing API URLs; landing "today" in the featured country's zone, hourly cache key |
| #39 | Password reset by emailed code (Resend backend), WebGL globe on auth pages |
| #40 | Two-factor sign-in, Google and Microsoft sign-in, data export, account deletion, account settings page |
| #41 | Who-is-off-today pages, embeddable widget, working-day overlap tool |
| #42 | Status page, changelog, Python and TypeScript SDKs |
| #43 | `manifest-src 'self'` in the public CSP (console error), select arrows kept in every form, CSS banner comments removed, stricter comment rule |
| #44 | Signed-in visitors get "My calendars" in the public header and footer (page cache keyed signed in / out); CSRF on anonymous auth endpoints (login CSRF); per-account login lock (10 failures / 15 min); signup race returns 400; no inline styles on public pages; `Permissions-Policy`; square `og:image`, Twitter tags, founder `sameAs` |

Outside this repo: the portfolio (`D:\syedahmershah`, ahmershah.dev) has HolidayOps as its first
project card plus a case study (`/blogs/holidayops-case-study-working-days-api`) and an article
(`/blogs/the-weekend-is-not-a-constant`), pushed 2026-10-18.

## Next session, in this order

The code is feature-complete. Stop adding features; finish these, then host and close.

1. **Email verification at signup** (the biggest security gap): today anyone can register with
   someone else's address. Send a one-time code or link (reuse the reset-code design in
   `apps/accounts/resets.py`), keep the account unverified until it's used, and block org
   creation, invites and digests until then.
2. **Signup must not reveal registered emails**: "An account with this email already exists" is
   an enumeration oracle. With verification in place, answer "check your email" either way and
   email the existing owner instead.
3. **Encrypt authenticator secrets at rest** (`TwoFactor.secret` is plaintext): a key from the
   environment, not `SECRET_KEY`, so rotating one doesn't break the other.
4. **Bot check on signup** (Cloudflare Turnstile or reCAPTCHA v3), only on signup and forgot
   password; keep it out of the API.
5. **Sessions screen**: list signed-in devices in account settings and sign out the others.
6. **Simulated-users test** on the production image (`docker compose -f docker-compose.prod.yml
   up --build`): script 10 to 17 users (owner, admin, member, viewer, API-key client, anonymous
   visitor) through every action, including attackers trying cross-org access (IDOR), CSRF,
   stored XSS in names, webhooks to internal addresses (SSRF), password guessing, racing the
   count limits, replaying 2FA and reset codes, and API-key and quota abuse. Watch the
   `holidayops.security` log and `/status/`; fix what breaks, add a test for each fix.
7. **Hosting** (free): Oracle Cloud Always Free ARM VM running `docker-compose.prod.yml` (Django,
   worker, beat, MySQL, Redis), Cloudflare for DNS and TLS on `holidayops.ahmershah.dev`, Resend
   free tier for email, UptimeRobot and Sentry free plans, nightly MySQL backups. Then the 5.4
   docs: live URL in the README and the portfolio card.

Not needed before closing: paid plans, Slack/Teams bot, publishing the SDKs to PyPI/npm, data-change
alerts. Add them only if real users ask.

## Security baseline (2026-10-18)

In place: Argon2; TOTP two-factor with hashed single-use recovery codes and replay protection;
Google/Microsoft OIDC with PKCE, state and nonce, no email-based takeover; hashed API keys, feed
tokens, invite and reset codes; CSRF on every session write including anonymous auth; strict CSP
(no script and no inline style on public pages, `script-src 'self'` in the app); ORM-only SQL;
row locks, named locks and unique keys against races; rate limits per IP, per key, per account
and per organization; tenant isolation tested on every endpoint (404, never 403); SSRF guard with
pinned IPs for webhooks; HSTS (preload), secure HttpOnly cookies, `Permissions-Policy`,
clickjacking and open-redirect protection; mypy strict and TypeScript strict; CodeQL, pip-audit,
npm audit and Dependabot in CI. Details: [security.md](security.md).

## Open items

- [ ] Re-run Lighthouse on Linux against the production image and record scores here. Runner:
  `node:22-bookworm-slim` + `chromium` + `lighthouse@13.5.0` on the `holidayops-prod_default`
  network. Last run (before #31): `/` 93/84/96/100, country page 100/96/96/100.
- [ ] Native-speaker review of every ur/ar string (all AI-drafted). Review sheet:
  <https://claude.ai/artifact/8ysoXpDponxKUH7V8qET4q> (private). Strings from #31 to #36 still
  need adding to it.
- [ ] Legal review of `/privacy/` and `/terms/` before launch.
- [ ] Update local Node.js to 22.22 or newer (jsdom warns on 22.19).
- [ ] Items 1 to 7 of "Next session" above.

## Gotchas

- Backend commands: `uv run --env-file ../.env ...`; pytest always uses `config.settings.test`.
- One MySQL test run at a time: parallel runs share `test_holidayops` and drop it.
- No GNU gettext on Windows: `npm run messages` runs in the backend container
  (`docker compose build backend` first after dependency changes).
- `makemessages` fuzzy-matches new strings to unrelated old ones: grep `#, fuzzy` after each run.
- Blank page with "Invalid hook call" after dependency changes: delete `frontend/node_modules/.vite`.
- `SCHEMA_PATH_PREFIX` is pinned to `/api/v1`: any other route would rename every operationId.
- Public pages are cached in the local-memory cache in development; touch a `.py` file (reload) or
  add a throwaway query string to see template changes.
- Class names on the landing page share one stylesheet with the calendars: `.today` is a calendar
  cell, so the live section is `.now`.
- The status page's job heartbeat needs a shared cache: with the local-memory cache in development
  the worker and the web process can't see each other, so it shows "No heartbeat yet".
- New migrations: restart `npm run dev` (it migrates on start) or run `manage.py migrate`.
- Headless Chrome has a 504 px minimum window width; it still hits the phone breakpoint (36rem).
