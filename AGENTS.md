# AGENTS.md — HolidayOps

Working guide for coding agents and contributors. Keep it short: details live in `docs/` and are read
only when a task needs them. When a decision changes, update the matching doc in the same PR.

HolidayOps is a business-day and holiday calendar platform (REST API, company calendars, iCal feeds,
web UI in en/ur/ar) built on the Python [holidays](https://github.com/vacanza/holidays) library.

## Read on demand

| Task touches | Read |
|---|---|
| Starting a session: what's done, what's next | [docs/status.md](docs/status.md) |
| Endpoints, domain functions, data model, caching | [docs/architecture.md](docs/architecture.md) |
| Auth, API keys, tenancy, webhooks, headers | [docs/security.md](docs/security.md) |
| Public server-rendered pages, sitemaps | [docs/seo.md](docs/seo.md) |
| Production image, Azure, domain, CD | [docs/deployment.md](docs/deployment.md) |
| What to build next, milestone scope | [docs/roadmap.md](docs/roadmap.md) |
| Milestone 1 API contracts and limits | [docs/design/m1-api.md](docs/design/m1-api.md) |
| Auth, orgs, roles, company calendars | [docs/design/m2-orgs.md](docs/design/m2-orgs.md) |
| UI, design system, i18n/RTL, calendar views | [docs/design/m3-ui.md](docs/design/m3-ui.md) |
| Celery tasks, iCal feeds, digests, webhooks | [docs/design/m4-subscriptions.md](docs/design/m4-subscriptions.md) |
| API keys, plans, quotas, usage | [docs/design/m5-api-keys.md](docs/design/m5-api-keys.md) |
| Showcase site, palette, motion, patterns | [docs/design/m6-showcase.md](docs/design/m6-showcase.md) |

## Stack

Python 3.12+, Django, DRF, drf-spectacular, `holidays` (exact pin), MySQL 8 (utf8mb4; no SQLite, even
in tests), Redis, Celery. Frontend: React + TypeScript (strict), Vite, Tailwind, TanStack Query,
React Router, i18next. Tests: pytest, pytest-django, factory_boy, Vitest. Lint: Ruff, mypy, ESLint,
Prettier. Dev: Docker Compose. CI: GitHub Actions.

## Layout

```
backend/config/          settings/{base,dev,test,prod}.py, urls.py, celery.py
backend/apps/core/       pure date logic: no Django imports, 100% branch coverage
backend/apps/api/        DRF views, serializers, throttles, API keys
backend/apps/{accounts,orgs,calendars,feeds,notifications,public}/
backend/tests/           mirrors apps/
frontend/src/            api/ (generated client), components/, features/, i18n/, pages/
docs/                    architecture, security, seo, roadmap, design notes
```

## Hard rules

- `apps/core` is plain Python. Views and serializers only call it. Use the library's own logic
  (`weekend`, `weekend_workdays`, `is_working_day`, `get_nth_working_day`,
  `get_working_days_count`); don't reimplement it. Never copy holiday data.
- Dates are `datetime.date`, never `datetime`; no timezone maths in the domain layer.
- `between` is inclusive of both ends.
- Every org-owned query is filtered by the current org (`OrgScopedMixin`); cross-org access returns
  404. Add each new org endpoint to `tests/test_isolation.py`.
- Validate country/subdiv/language/category against the library; cap years and `days`.
- Secrets come only from environment variables. Never commit `.env`, dumps or personal data.
- API changes update the OpenAPI schema and the frontend client in the same PR.
- No new dependency without a reason in the PR description. Pin exact versions.
- The maintainer must be able to explain every line; keep core logic small and readable.
- The footer's CSS is one `frame:footer` block pasted into both `site.css` and the app's
  `index.css`; change both (a test compares them). Same for the palette tokens.

## Comments

Few, short, written like a colleague's note. Names and structure explain *what*; a comment is
only for what the code can't say:

- why it's done this way (`# Signer, not signing.dumps: the link never expires`),
- a data or library quirk (`# The UAE moved from Fri-Sat to Sat-Sun in 2022`),
- a spec or source (`# RFC 5545 3.1: lines are at most 75 octets`),
- a trap for the next person (`# backdrop-filter makes the header the containing block…`).

Not: restating the line below, section banners in templates, "This function…" docstrings,
history ("changed from…", "new:"), TODOs without an owner, or filler words (simply, robust,
seamless, ensure, leverage, comprehensive). Delete a comment the code made obsolete in the same
change. Short docstrings are fine on public functions and classes when they add a fact the
signature doesn't.

## Workflow

- Branches `feat/…`, `fix/…`, `docs/…`, `chore/…`. `main` takes PRs only, squash-merged, linear
  history, no force-push.
- Commit messages: short, imperative, no prefixes (`Add business_days_between endpoint`).
- Every feature PR has tests.
- Before pushing, run what CI runs: backend ruff, ruff format, **mypy**, pytest; frontend lint,
  typecheck, Prettier, tests. If a template or `gettext` string changed, run `npm run messages`
  (reusing a string elsewhere reorders the catalog, and CI fails on that too).
- Check UI changes with screenshots at phone (390), tablet (820) and desktop (1440), light and
  dark, en and one RTL language.

## Commands

```
cp .env.example .env                         # once; fill in secrets
npm install && npm run setup                 # once
npm run dev                                  # Docker db+redis, Django :8000, Vite :5173, Celery
docker compose up -d db redis                # MySQL + Redis only
docker compose up -d                         # everything in containers (db, redis, backend, worker, beat, frontend)
docker compose -f docker-compose.prod.yml up --build   # production image locally, :8080
cd backend
uv sync                                      # install pinned deps into .venv
uv run --env-file ../.env python manage.py migrate
uv run --env-file ../.env pytest             # all tests (needs MySQL)
uv run pytest tests/core --cov=apps/core --cov-branch --cov-fail-under=100
uv run ruff check . && uv run ruff format --check . && uv run mypy .
uv run python manage.py spectacular --file schema.yml --validate   # commit schema.yml
cd ../frontend && npm run gen:api            # regenerate src/api/schema.d.ts
npm run lint && npm run typecheck && npm test
npm run seed                                 # (root) demo user, org and calendar; needs DEMO_PASSWORD
npm run messages                             # (root) refresh + compile backend ur/ar translations
```

## i18n rules

- Every user-facing string: `t("key")` in the frontend (en, ur, ar JSON must have the same keys;
  a test enforces it), `gettext` in Django. `apps/core` errors stay English and carry `params`;
  `apps/api/errors.py` translates them.
- Layout uses logical properties only (`ms-`, `ps-`, `text-start`, `rtl:` variants).
- Commit both `.po` and `.mo`; CI fails on untranslated or stale catalogs.
