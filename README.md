# HolidayOps

**Is this date a working day here, and in our other offices?**
HolidayOps answers that as an API and a web app, for every country and subdivision that the Python
[holidays](https://github.com/vacanza/holidays) library supports. It uses each country's own weekend
(Fri–Sat in Saudi Arabia, Sat–Sun in Pakistan) and moved working days, and lets a company add its own
closures on top.

Built for payroll, HR, logistics and finance teams.

> **Status:** Milestone 1 (public API) done, Milestone 2 (accounts, organizations, company
> calendars) in review. See the [roadmap](docs/roadmap.md).

## Features

| | Feature | Milestone |
|---|---|---|
| 🌍 | REST API: holidays by country, subdivision, year, language and category | 1 |
| 📅 | Business-day maths: check a date, add/subtract N working days, count working days | 1 |
| 🏢 | Company calendars: merge countries, add closures, half-days and extra working days | 2 |
| 🖥️ | Web UI in English, Urdu and Arabic (RTL), mobile friendly | 3 |
| 🔔 | iCal feeds, monthly email digests, signed webhooks | 4 |
| 🔑 | API keys, per-plan rate limits, usage charts | 5 |

## API at a glance

```http
GET /api/v1/countries/
GET /api/v1/holidays/?country=PK&year=2027&language=ur_PK
GET /api/v1/business-days/check/?country=SA&date=2027-04-02
GET /api/v1/business-days/add/?country=PK&date=2027-03-20&days=5
GET /api/v1/business-days/between/?country=AE&start=2027-01-01&end=2027-01-31
```

```json
{"date": "2027-04-02", "is_business_day": false, "reason": "weekend", "holidays": []}
```

Interactive docs are served at `/api/v1/docs/`; the OpenAPI schema at `/api/v1/schema/`.
Full contracts and limits: [docs/design/m1-api.md](docs/design/m1-api.md).

## Quick start

Requirements: [uv](https://docs.astral.sh/uv/), Node.js 22.22+, and Docker Desktop (running).

```bash
git clone https://github.com/ahmershahdev/holidayops.git
cd holidayops
cp .env.example .env        # then set DJANGO_SECRET_KEY and the MySQL passwords
npm install                 # root tools (concurrently)
npm run setup               # frontend packages + Python packages
npm run dev                 # MySQL + Redis in Docker, Django on :8000, Vite on :5173
```

Open <http://localhost:5173>: the playground answers business-day questions live; sign up to create
an organization and a company calendar. API docs: <http://localhost:5173/api/v1/docs/>.

## Development

```bash
npm test                          # backend (pytest, needs MySQL) + frontend (Vitest)
cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy .
cd frontend && npm run lint && npm run typecheck
```

After changing the API, regenerate the schema and the typed client:

```bash
cd backend && uv run python manage.py spectacular --file schema.yml --validate
cd ../frontend && npm run gen:api
```

## Stack

| Part | Tools |
|---|---|
| Backend | Python 3.12+, Django 5.2 LTS, Django REST Framework, drf-spectacular, `holidays` |
| Data | MySQL 8, Redis |
| Jobs | Celery + Celery Beat |
| Frontend | React, TypeScript, Vite, Tailwind CSS, TanStack Query |
| Quality | pytest, Ruff, mypy, ESLint, GitHub Actions, CodeQL |

## Project docs

- [Architecture](docs/architecture.md): domain layer, endpoints, data model
- [Accounts, orgs and company calendars](docs/design/m2-orgs.md)
- [Security design](docs/security.md)
- [Roadmap](docs/roadmap.md)
- [AGENTS.md](AGENTS.md): conventions for contributors and coding agents

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Wrong holiday dates usually come from the upstream
[holidays](https://github.com/vacanza/holidays) library; please report them there. To report a
vulnerability, see [SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE) © 2026 Syed Ahmer Shah
