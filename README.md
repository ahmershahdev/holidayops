# HolidayOps

Business-day and holiday calendars as an API and a web app, built on the Python
[holidays](https://github.com/vacanza/holidays) library.

Payroll, HR, logistics and finance teams keep asking the same question: is this date a working day,
here and in our other offices? HolidayOps answers it for any country or subdivision that `holidays`
supports, using each country's own weekend, and lets a company add its own closures on top.

> Status: early development. Nothing is ready to run yet. The roadmap below shows what comes next.

## Planned features

- REST API: holidays by country, subdivision, year and language; `is_business_day`,
  `add_business_days` and `business_days_between`, with each country's weekend rules.
- Company calendars: pick base countries, add your own closures and half-days, and get one merged
  calendar.
- Subscriptions: an iCal feed per calendar, plus a monthly email or webhook digest of upcoming holidays.
- API keys, per-plan rate limits and usage charts.
- UI in English, Urdu and Arabic (right-to-left), with holiday names from the library's translations.

## Stack

| Part | Tools |
|---|---|
| Backend | Python 3.12+, Django, Django REST Framework, `holidays`, MySQL 8 |
| Cache and jobs | Redis, Celery |
| Frontend | React, TypeScript, Vite, Tailwind CSS, TanStack Query |
| API docs | OpenAPI via drf-spectacular |
| Tooling | pytest, Ruff, ESLint, Docker Compose, GitHub Actions |

## Planned layout

```
backend/    Django project and REST API
frontend/   React + TypeScript app
docs/       Design notes and API examples
```

## Roadmap

1. API over `holidays` with business-day maths, fully tested
2. Organizations, company calendars and auth
3. React UI with a calendar view
4. iCal feeds and digests
5. Deployment and docs

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). To report a vulnerability, see [SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE) © 2026 Syed Ahmer Shah
