# AGENTS.md

Guide for coding agents and contributors. Short on purpose: details live in `docs/`, read only when
a task needs them. When a decision changes, update the matching doc in the same PR.

HolidayOps: business-day and holiday platform (REST API, company calendars, iCal feeds, digests,
webhooks, web app and public site in en/ur/ar) on the Python [holidays](https://github.com/vacanza/holidays)
library. Owner: Syed Ahmer Shah, <https://ahmershah.dev>, support@ahmershah.dev.

## Read on demand

| Task touches | Read |
|---|---|
| Starting a session | [docs/status.md](docs/status.md) |
| Endpoints, domain, data model, caching | [docs/architecture.md](docs/architecture.md) |
| Auth, keys, tenancy, webhooks, headers | [docs/security.md](docs/security.md) |
| Public pages, SEO, sitemaps, llms.txt, PWA | [docs/seo.md](docs/seo.md) |
| Production image, Azure, CD | [docs/deployment.md](docs/deployment.md) |
| What to build next | [docs/roadmap.md](docs/roadmap.md) |
| API contracts and limits | [docs/design/m1-api.md](docs/design/m1-api.md) |
| Orgs, roles, company calendars | [docs/design/m2-orgs.md](docs/design/m2-orgs.md) |
| UI, design system, i18n/RTL | [docs/design/m3-ui.md](docs/design/m3-ui.md) |
| Celery, feeds, digests, webhooks | [docs/design/m4-subscriptions.md](docs/design/m4-subscriptions.md) |
| API keys, plans, quotas | [docs/design/m5-api-keys.md](docs/design/m5-api-keys.md) |
| Public site palette, motion, patterns | [docs/design/m6-showcase.md](docs/design/m6-showcase.md) |

## Stack

Python 3.12, Django 5.2, DRF, drf-spectacular, `holidays` (exact pin), MySQL 8 (utf8mb4; never
SQLite, even in tests), Redis, Celery. React + TypeScript (strict), Vite, Tailwind, TanStack Query,
React Router, i18next. pytest, factory_boy, Vitest. Ruff, mypy (strict), ESLint, Prettier.

## Layout

```
backend/config/        settings/{base,dev,test,prod}.py, urls, csp, spa, celery, security_log
backend/apps/core/     pure date logic: no Django imports, 100% branch coverage
backend/apps/api/      DRF views, serializers, throttles, API keys, usage
backend/apps/{accounts,orgs,calendars,feeds,notifications,webhooks}/
backend/apps/public/   server-rendered site: views, landing, pages, world (live data), seo,
                       discovery (robots, llms, manifest, sw), sitemaps, templates, static
backend/tests/         mirrors apps/
frontend/src/          api/ (generated), components/, pages/, i18n/, lib/
docs/                  architecture, security, seo, deployment, roadmap, status, design/
```

Reuse, don't rebuild: `apps/orgs/limits.within_limit` (count-then-create),
`config/security_log.security_event`, `apps/public/content` (`country_name`, `join_list`,
`month_grid`), `apps/public/seo` (`fit_title`, `breadcrumbs`, `ld_json`), template tags `flag`,
`cldr`, `as_list`, `page_title`, and `apps/public/flags.sanitize` for any third-party SVG.

## Hard rules

- `apps/core` is plain Python; views and serializers only call it. Use the library's own logic
  (`weekend`, `weekend_workdays`, `is_working_day`, `get_nth_working_day`,
  `get_working_days_count`). Never copy holiday data.
- Dates are `datetime.date`; no timezone maths in the domain. `between` includes both ends.
- Every org-owned query is filtered by the current org (`OrgScopedMixin`); cross-org access is
  `404`. Add every new org endpoint to `tests/test_isolation.py`.
- Validate country, subdiv, language and category against the library; cap years and `days`.
- Secrets only from environment variables. Never commit `.env`, dumps or personal data.
- API changes update `schema.yml` and the frontend client in the same PR.
- No new dependency without a reason in the PR. Pin exact versions.
- The maintainer must be able to explain every line; keep core logic small.
- Footer CSS is one `frame:footer` block in both `site.css` and `frontend/src/index.css`; same for
  the palette tokens. Tests compare them.
- Public pages work without JavaScript: motion is CSS only, off under `prefers-reduced-motion`,
  and nothing readable starts at `opacity: 0`.
- Public page `<title>` ≤ 60 and meta description ≤ 150 characters (`tests/public/test_seo.py`).
- No emojis in code, UI text or docs.

## Comments

Few, short, like a colleague's note: why it's done this way, a data or library quirk, a spec, or a
trap for the next person. Not: restating the code, section banners, "This function…" docstrings,
history, owner-less TODOs, or filler (simply, robust, seamless, ensure, leverage, comprehensive).
Delete comments the change made obsolete. Short docstrings are fine when they add a fact the
signature doesn't.

## i18n

- Every user-facing string: `t("key")` in the frontend (en, ur, ar JSON share keys; tested),
  `gettext` in Django. `apps/core` errors stay English with `params`; `apps/api/errors.py`
  translates them.
- Logical properties only (`ms-`, `ps-`, `text-start`, `inset-inline-*`, `rtl:`).
- On public pages use `join_list`/`as_list`, `country_name` and `cldr`, never hard-coded `", "` or
  English country, day or month names.
- ur/ar strings are unverified until a native speaker marks them in the review sheet (see
  status.md). Commit `.po` and `.mo`; CI fails on untranslated, fuzzy or stale catalogs.
- Legal pages (`/privacy/`, `/terms/`) are English only by design.

## Workflow

- Branches `feat/…`, `fix/…`, `docs/…`, `chore/…`. `main` takes PRs only, squash-merged.
- Commit messages: short, imperative, no prefixes.
- Every feature PR has tests.
- Before pushing, run what CI runs: ruff, ruff format, mypy, pytest; frontend lint (ESLint and
  Prettier), typecheck, tests. Template or `gettext` changes: `npm run messages`, then fix fuzzy
  entries.
- UI changes: check phone (390), tablet (820), desktop (1440), light and dark, en and one RTL
  language.

## Commands

```
cp .env.example .env && npm install && npm run setup     # once
npm run dev                  # Docker db+redis, Django :8000, Vite :5173, Celery
npm run seed                 # demo user, org and calendar (needs DEMO_PASSWORD)
npm run messages             # refresh and compile ur/ar catalogs (in the backend container)
docker compose up -d         # everything in containers
docker compose -f docker-compose.prod.yml up --build     # production image on :8080
cd backend
uv run --env-file ../.env pytest
uv run pytest tests/core --cov=apps/core --cov-branch --cov-fail-under=100
uv run ruff check . && uv run ruff format --check . && uv run mypy .
uv run python manage.py spectacular --file schema.yml --validate
cd ../frontend && npm run gen:api && npm run lint && npm run typecheck && npm test
```
