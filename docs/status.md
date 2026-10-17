# Project status

Last updated: 2026-10-18 (through #34). Update this file at the end of every work session.

Run it: `npm run dev` → <http://localhost:5173>; `npm run seed` for the demo login
(`demo@holidayops.test`, password = `DEMO_PASSWORD` in `.env`). Docker Desktop must be running.

## Where we are

| Milestone | State |
|---|---|
| 1. Public API over `holidays` | ✅ #2 |
| 2. Accounts, orgs, company calendars, invites | ✅ #6, invites after M4 |
| 3. Web app UI, design system, ur/ar RTL | ✅ #9 |
| 4. Celery, iCal feeds, digests, webhooks | ✅ #12–#15 |
| 5. API keys and plans, SEO pages, production image | ✅ #17–#19; hosting and 5.4 docs wait for launch |
| 6. Showcase website | ✅ code done (#21–#33); Lighthouse re-run and translation review open |

Hosting is deferred by the owner (2026-10-17): launch around GSoC 2027 (owner put it at Feb 2028),
Azure likely. Then follow [deployment.md](deployment.md) and write 5.4 (README, API examples,
screenshots from the live site).

## Milestone 6 log

| PR | What |
|---|---|
| #21 | Art direction: logo-led palette with measured contrast, Outfit, motion primitives, `/style/` |
| #22 | Site frame: shared header/footer, light/dark/device theme cookie, branded 404/500 |
| #23 | Landing page at `/`: hero route kept clear of the copy at every width, no-JS working-day demo |
| #24 | Footer matches the header; one `frame:footer` CSS block for both halves (tested) |
| #25 | Comment rule in AGENTS.md; comments that restated code removed |
| #26 | Security: count-then-create limits under a MySQL named lock, `NUM_PROXIES` (X-Forwarded-For could dodge every per-IP throttle), public page rate limit, `holidayops.security` event log |
| #27 | Country flags: flag-icons 7.5.0 (MIT), allowlist-sanitised, CSP on static SVGs |
| #28 | Country pages: flag-coloured pattern banner, 12-month calendar, CLDR names, day/month names and list patterns via Babel |
| #29 | Route-split app bundle (446 → 382 KB on `/playground`), translations on demand, h1 fixes |
| #30 | Lighthouse 13.5.0 on Linux recorded (below) |
| #31 | Footer cleanup and wordmark fix, CSS scroll-to-top, account menu, themed selects, dev 404 page, page cache versioned per deploy, Lighthouse findings fixed |
| #32 | Log in / sign up redesign: art panel, icons, placeholders, password eye toggle |
| #33 | Pricing redesign (plan cards, request route with arrows, compare table, FAQ); landing use cases and step arrows |
| #34 | AGENTS.md, roadmap and this log brought up to date |

## Lighthouse 13.5.0, Linux (2026-10-18, before #31)

Debian container with Chromium against the production image, single runs, mobile (throttled).

| Page | Perf | A11y | Best pr. | SEO |
|---|---|---|---|---|
| `/` | 93 | 84 | 96 | 100 |
| `/holidays/pk/2026/` | 100 | 96 | 96 | 100 |
| `/playground` | 35 | 100 | 92 | 54 |
| `/login` | 65 | 100 | 92 | 54 |

#31 fixed every finding (playground eager again, hero calendar roles, contrast measured mid-fade,
touch targets, blocked `data:` fonts, stale hashed CSS after deploys, SPA `noindex` and meta
description). **Not re-measured yet.** The runner lives outside the repo; rebuild it from
`node:22-bookworm-slim` + `chromium` + `lighthouse@13.5.0` and run it on the
`holidayops-prod_default` network.

## Open items

- [ ] Re-run Lighthouse on Linux after #31–#33 and record the scores here.
- [ ] Native-speaker review of every ur/ar string (all AI-drafted, none verified). Review sheet:
  <https://claude.ai/artifact/8ysoXpDponxKUH7V8qET4q> (private; share it with reviewers). It
  predates #31–#33: about 60 newer strings still need adding to it.
- [ ] Update local Node.js to ≥ 22.22 (jsdom 30 warns on 22.19).
- [ ] At launch: hosting, then 5.4 docs.

## Gotchas learned

- Use `uv run --env-file ../.env ...` for backend commands; pytest always uses
  `config.settings.test` (`--ds` in `pyproject.toml`).
- Only one test run against MySQL at a time: parallel runs share `test_holidayops` and drop it.
- No GNU gettext on Windows: use `npm run messages` (runs in the backend container;
  `docker compose build backend` first after dependency changes).
- `makemessages` fuzzy-matches new strings to unrelated old ones ("Questions" became «علاقے»,
  "regions"): after every run, grep `#, fuzzy` and fix those entries by hand.
- After changing frontend dependencies, delete `frontend/node_modules/.vite` if the app shows a
  blank page with "Invalid hook call".
- Any non-`/api/v1` route changes drf-spectacular's auto prefix and renames every operationId;
  `SCHEMA_PATH_PREFIX` is pinned to `/api/v1` for that reason.
- `docker-compose.prod.yml` sets `name: holidayops-prod`, or its db/redis would replace the dev
  containers (both files live in the same folder).
- Git Bash heredocs turn `\\` into `\`: write files containing escapes or regexes with the editor
  tools, not `cat <<EOF` or inline `python -`.
- Git Bash rewrites arguments that start with `/` into Windows paths: prefix the command with
  `MSYS_NO_PATHCONV=1`.
- Stale pages in screenshots: public HTML is cached in Redis, and Django's cached template loader
  keeps old templates until the server restarts. Restart `runserver` and clear the cache
  (`manage.py shell -c "from django.core.cache import cache; cache.clear()"`).
- On Windows, stopping a backgrounded `uv run ... runserver` can leave the Python child alive and
  two servers share port 8000. Find them with `Get-CimInstance Win32_Process` (`runserver`).
- Don't mock `socket.*` through an app module: patch a small wrapper like
  `apps.webhooks.net.resolve` instead.
- The Celery worker on Windows needs `--pool=solo` (`npm run dev:worker` passes it).
- Stacked PRs + squash merge: rebase the next branch with `git rebase --onto origin/main <old base>`
  and retarget it before deleting its base branch, or GitHub closes it.
- A scroll-driven animation on the last element of a page must finish by `entry 100%`; `cover 60%`
  is never reached at the bottom of the page.
- Variable fonts (Outfit) keep overlapping contours: `-webkit-text-stroke` draws them as stray
  lines. Fill outlined display text with a gradient instead.
- `background-clip: text` only paints inside the element's box: a line height below 1 or a
  bottom `text-box` trim cuts off descenders.
- Links to `#top` on a sticky header never scroll (it's always in view); use `#page-top`.
- Vite 8 builds with Rolldown: chunking is `build.rolldownOptions.output.codeSplitting.groups`;
  keep `assetsInlineLimit: 0` (the CSP has no `data:` fonts).
