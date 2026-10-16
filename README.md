# HolidayOps

**Is this date a working day here, and in our other offices?**
HolidayOps answers that as an API and a web app, for every country and subdivision that the Python
[holidays](https://github.com/vacanza/holidays) library supports. It uses each country's own weekend
(Fri–Sat in Saudi Arabia, Sat–Sun in Pakistan) and moved working days, and lets a company add its own
closures on top.

Built for payroll, HR, logistics and finance teams.

> **Status:** Milestone 1 (public API) in progress. See the [roadmap](docs/roadmap.md).

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
GET /api/v1/business-days/check/?country=SA&date=2027-03-12
GET /api/v1/business-days/add/?country=PK&date=2027-03-20&days=5
GET /api/v1/business-days/between/?country=AE&start=2027-01-01&end=2027-01-31
```

```json
{"date": "2027-03-12", "is_business_day": false, "reason": "weekend", "holidays": []}
```

Interactive docs are served at `/api/v1/docs/`; the OpenAPI schema at `/api/v1/schema/`.
Full contracts and limits: [docs/design/m1-api.md](docs/design/m1-api.md).

## Quick start

Requirements: [uv](https://docs.astral.sh/uv/), Python 3.12+, and Docker (for MySQL and Redis).

```bash
git clone https://github.com/ahmershahdev/holidayops.git
cd holidayops
cp .env.example .env
docker compose up -d db redis

cd backend
uv sync
uv run python manage.py migrate
uv run python manage.py runserver
```

Open <http://localhost:8000/api/v1/docs/>. Or run everything in containers: `docker compose up -d`.

## Development

```bash
cd backend
uv run pytest                     # tests (the domain tests need no database)
uv run ruff check . && uv run ruff format --check .
uv run mypy .
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
- [Security design](docs/security.md)
- [Roadmap](docs/roadmap.md)
- [AGENTS.md](AGENTS.md): conventions for contributors and coding agents

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Wrong holiday dates usually come from the upstream
[holidays](https://github.com/vacanza/holidays) library; please report them there. To report a
vulnerability, see [SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE) © 2026 Syed Ahmer Shah
