# Project status

Last updated: 2026-10-16. Update this file at the end of every work session.

## Where we are

| Milestone | State |
|---|---|
| 1. Public API over `holidays` | ✅ merged (#2) |
| 2. Accounts, orgs, company calendars | ✅ merged (#6) |
| 3. Web app UI, design system, ur/ar RTL | ✅ merged (#9) |
| 4. iCal feeds, digests, webhooks | ⏭ next |
| 5. API keys, limits, deployment, SEO pages | planned |
| 6. Showcase website | planned |

Run it: `npm run dev` → <http://localhost:5173>; `npm run seed` for the demo login
(`demo@holidayops.test`, password = `DEMO_PASSWORD` in `.env`). Docker Desktop must be running.

## Next: Milestone 4 (see [roadmap.md](roadmap.md))

1. **4.1 Celery** – worker + Beat services in Compose, `config/celery.py`, task conventions, tests
   with eager mode.
2. **4.2 iCal feeds** – `FeedToken` model (hashed, revocable, rotatable), `/feeds/<token>.ics`,
   cached build, UI to create/rotate/revoke the link in calendar settings.
3. **4.3 Digests** – monthly email "holidays in the next 30 days", per-member opt-in, email backend
   from env (console in dev).
4. **4.4 Webhooks** – `Webhook` model, HMAC-SHA256 signature, HTTPS only, SSRF guard after DNS
   resolution, retries with backoff, delivery log, UI in org settings.
5. Org invites by email (deferred from Milestone 2) once email sending exists.

Start each part on its own `feat/...` branch; write the design note in `docs/design/m4-*.md` first.

## Open items

- [ ] Merge Dependabot #4 (actions/checkout 7) and #8 (actions/setup-node 7) if CI is green.
- [ ] Close Dependabot #7 (TypeScript 7): typescript-eslint supports only < 6.1. Ignore rule added.
- [ ] Native-speaker review of `frontend/src/i18n/{ur,ar}.json` and `backend/locale/*/django.po`.
- [ ] Update local Node.js to ≥ 22.22 (jsdom 30 warns on 22.19).
- [ ] Align the design tokens with the logo palette (navy + bright teal) — Milestone 6 art direction.

## Deferred on purpose (owner milestone)

- Redis cache for serialized holiday lists — 5.3 (in-process LRU is enough today).
- CD pipeline, health endpoint, slimmer multi-stage backend image (now 801 MB) — 5.3.
- API keys and usage chart in org settings — 5.1.

## Gotchas learned

- Use `uv run --env-file ../.env ...` for backend commands; pytest always uses
  `config.settings.test` (`--ds` in `pyproject.toml`).
- Only one test run against MySQL at a time: parallel runs share `test_holidayops` and drop it.
- No GNU gettext on Windows: use `npm run messages` (runs in the backend container).
- After changing frontend dependencies, delete `frontend/node_modules/.vite` if the app shows a
  blank page with "Invalid hook call".
- Stacked PRs + squash merge: rebase the next branch with `git rebase --onto origin/main <old base>`
  before merging, and retarget it before deleting its base branch, or GitHub closes it.
