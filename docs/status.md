# Project status

Last updated: 2026-10-18 (through #37). Update at the end of every work session.

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

## Open items

- [ ] Re-run Lighthouse on Linux against the production image and record scores here. Runner:
  `node:22-bookworm-slim` + `chromium` + `lighthouse@13.5.0` on the `holidayops-prod_default`
  network. Last run (before #31): `/` 93/84/96/100, country page 100/96/96/100.
- [ ] Native-speaker review of every ur/ar string (all AI-drafted). Review sheet:
  <https://claude.ai/artifact/8ysoXpDponxKUH7V8qET4q> (private). Strings from #31 to #36 still
  need adding to it.
- [ ] Legal review of `/privacy/` and `/terms/` before launch.
- [ ] Update local Node.js to 22.22 or newer (jsdom warns on 22.19).
- [ ] At launch: hosting per [deployment.md](deployment.md).

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
- Headless Chrome has a 504 px minimum window width; it still hits the phone breakpoint (36rem).
