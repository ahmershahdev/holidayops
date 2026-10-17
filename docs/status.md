# Project status

Last updated: 2026-10-17. Update this file at the end of every work session.

## Where we are

| Milestone | State |
|---|---|
| 1. Public API over `holidays` | ✅ merged (#2) |
| 2. Accounts, orgs, company calendars | ✅ merged (#6) |
| 3. Web app UI, design system, ur/ar RTL | ✅ merged (#9) |
| 4. iCal feeds, digests, webhooks | ✅ merged (#12, #13, #14, #15) |
| 5. API keys, limits, deployment, SEO pages | 🚧 5.1 on `feat/api-keys` |
| 6. Showcase website | planned |

Run it: `npm run dev` → <http://localhost:5173>; `npm run seed` for the demo login
(`demo@holidayops.test`, password = `DEMO_PASSWORD` in `.env`). Docker Desktop must be running.

## Milestone 4 recap (see [roadmap.md](roadmap.md))

Design note: [design/m4-subscriptions.md](design/m4-subscriptions.md) (all four parts).

1. ✅ **4.1 Celery** – worker + Beat in Compose and `npm run dev`, `config/celery.py`, task
   conventions, eager-mode tests. `redis` went 8.1 → 6.4: kombu's Redis extra caps it below 6.5.
2. ✅ **4.2 iCal feeds** – `FeedToken` (hashed, revocable, rotatable, max 10 per calendar),
   `/feeds/<token>.ics` built by `apps/core/ical.py`, cached by `calendar.updated_at`, ETag/304;
   "Calendar feeds" card in calendar settings.
3. ✅ **4.3 Digests** – `DigestSubscription`, Beat on the 1st at 06:00 UTC fans out one task per
   subscription, once per month even on retries; `User.language` for the email; one-click
   unsubscribe; "Email me monthly" toggle on the calendar page and `/unsubscribe` page.
4. ✅ **4.4 Webhooks** – `apps/webhooks`: HMAC-SHA256 `t=…,v1=…` signature, SSRF guard with
   a pinned connection, DB-scheduled retries (Beat `webhooks.retry_due` every minute), delivery
   log, auto-disable after 20 failures; "Webhooks" card in org settings for admins.
## Next

1. ✅ Org invites by email: `Invite` (hashed token, 7 days, one use), email sent in the request,
   accept only with the invited address; `/invite` page, pending list in org settings.
2. ✅ **5.1 API keys** – `hops_<prefix>_<secret>` (hashed), plans `free`/`pro` (`set_plan`
   command, limits in settings/env), per-key rate + monthly org quota, `UsageEvent` (90 days),
   "API keys" and "Usage" cards (30-day chart) in org settings.
3. Next: 5.2 public SEO pages ([seo.md](seo.md)), then 5.3 deployment, 5.4 docs.

Each part: one `feat/...` branch, PR, merge as soon as CI is green, delete the branch.

## Open items

- [ ] Native-speaker review of `frontend/src/i18n/{ur,ar}.json` and `backend/locale/*/django.po`.
- [ ] Update local Node.js to ≥ 22.22 (jsdom 30 warns on 22.19).
- [ ] Align the design tokens with the logo palette (navy + bright teal) — Milestone 6 art direction.

## Deferred on purpose (owner milestone)

- Redis cache for serialized holiday lists — 5.3 (in-process LRU is enough today).
- CD pipeline, health endpoint, slimmer multi-stage backend image (now 801 MB) — 5.3.

## Gotchas learned

- Use `uv run --env-file ../.env ...` for backend commands; pytest always uses
  `config.settings.test` (`--ds` in `pyproject.toml`).
- Only one test run against MySQL at a time: parallel runs share `test_holidayops` and drop it.
- No GNU gettext on Windows: use `npm run messages` (runs in the backend container).
- After changing frontend dependencies, delete `frontend/node_modules/.vite` if the app shows a
  blank page with "Invalid hook call".
- Any non-`/api/v1` route changes drf-spectacular's auto prefix and renames every operationId;
  `SCHEMA_PATH_PREFIX` is pinned to `/api/v1` for that reason.
- `docker compose build backend` after backend dependency changes, or `npm run messages` fails.
- Git Bash heredocs here turn a doubled backslash into a single one: write files containing
  escapes, regexes or `\u` sequences with the editor tools, not `cat <<EOF` or inline `python -`.
- Don't mock `socket.*` through an app module (`apps.x.socket.getaddrinfo` is the real `socket`
  module): patch a small wrapper like `apps.webhooks.net.resolve` instead.
- `makemessages` can fuzzy-match a new string to an unrelated old translation: check for
  `#, fuzzy` in the `.po` files and fix those entries by hand.
- The Celery worker on Windows needs `--pool=solo` (`npm run dev:worker` passes it).
- Stacked PRs + squash merge: rebase the next branch with `git rebase --onto origin/main <old base>`
  before merging, and retarget it before deleting its base branch, or GitHub closes it.
