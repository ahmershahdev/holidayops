# AGENTS.md — HolidayOps

Working guide for coding agents and contributors. Keep it short: details live in `docs/` and are read
only when a task needs them. When a decision changes, update the matching doc in the same PR.

HolidayOps is a business-day and holiday calendar platform (REST API, company calendars, iCal feeds,
web UI in en/ur/ar) built on the Python [holidays](https://github.com/vacanza/holidays) library.

## Read on demand

| Task touches | Read |
|---|---|
| Endpoints, domain functions, data model, caching | [docs/architecture.md](docs/architecture.md) |
| Auth, API keys, tenancy, webhooks, headers | [docs/security.md](docs/security.md) |
| Public server-rendered pages, sitemaps | [docs/seo.md](docs/seo.md) |
| What to build next, milestone scope | [docs/roadmap.md](docs/roadmap.md) |
| Milestone 1 API contracts and limits | [docs/design/m1-api.md](docs/design/m1-api.md) |

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
- Every org-owned query is filtered by the current org; cross-org access returns 404.
- Validate country/subdiv/language/category against the library; cap years and `days`.
- Secrets come only from environment variables. Never commit `.env`, dumps or personal data.
- API changes update the OpenAPI schema and the frontend client in the same PR.
- No new dependency without a reason in the PR description. Pin exact versions.
- Code is comment-free by default; comment only a non-obvious why, a data quirk or a source URL.
- The maintainer must be able to explain every line; keep core logic small and readable.

## Workflow

- Branches `feat/…`, `fix/…`, `docs/…`, `chore/…`. `main` takes PRs only, squash-merged, linear
  history, no force-push.
- Commit messages: short, imperative, no prefixes (`Add business_days_between endpoint`).
- Every feature PR has tests.

## Commands

```
docker compose up -d                         # MySQL, Redis, backend
cd backend
uv sync                                      # install pinned deps into .venv
uv run pytest                                # all tests (DB tests need MySQL)
uv run pytest tests/core                     # domain tests, no DB needed
uv run ruff check . && uv run ruff format --check . && uv run mypy .
uv run python manage.py spectacular --file schema.yml --validate
```
