# Contributing to HolidayOps

Thank you for helping. This guide covers how to report problems, set up the project, and get a pull
request merged. The conventions that code must follow are in [AGENTS.md](AGENTS.md); read it before
your first change.

Everyone taking part is expected to follow the [Code of Conduct](CODE_OF_CONDUCT.md).

## Contents

- [Ways to contribute](#ways-to-contribute)
- [Before you start](#before-you-start)
- [Local setup](#local-setup)
- [Making a change](#making-a-change)
- [Checks to run](#checks-to-run)
- [Pull requests](#pull-requests)
- [Style](#style)
- [Translations](#translations)
- [Getting help](#getting-help)

## Ways to contribute

| You want to | Do this |
|---|---|
| Report a bug | Open an issue with the bug template: what you did, what you expected, what happened |
| Suggest a feature | Open an issue with the feature template before writing code, so we can agree on the approach |
| Fix a wrong holiday date | Report it to the [holidays](https://github.com/vacanza/holidays) library; a fix there reaches everyone |
| Review a translation | Native Urdu and Arabic speakers are very welcome: see [Translations](#translations) |
| Report a security problem | Don't open an issue. Follow [SECURITY.md](SECURITY.md) |

## Before you start

- Look for an existing issue first, and comment on it to say you're working on it.
- Keep each pull request to one change. Small pull requests get reviewed quickly.
- New dependencies need a reason in the pull request description and an exact version pin.

## Local setup

Requirements:

- [uv](https://docs.astral.sh/uv/) (installs Python 3.12 for you)
- Node.js 22.22 or newer
- Docker Desktop, running (MySQL 8 and Redis)

```bash
git clone https://github.com/<your-username>/holidayops.git
cd holidayops
cp .env.example .env    # fill in DJANGO_SECRET_KEY, FIELD_ENCRYPTION_KEYS, the MySQL passwords and DEMO_PASSWORD
npm install
npm run setup
npm run dev             # Django :8000, Vite :5173, Celery worker and Beat
npm run seed            # optional demo data
```

Open <http://localhost:5173>. The tests use MySQL too (never SQLite), so keep Docker running.

## Making a change

1. Create a branch from `main`: `feat/short-name`, `fix/short-name`, `docs/short-name` or
   `chore/short-name`.
2. Write the change with tests. Every feature and bug fix needs a test that fails without it.
3. If you change the API, regenerate the schema and the frontend client in the same pull request:

   ```bash
   cd backend && uv run python manage.py spectacular --file schema.yml --validate
   cd ../frontend && npm run gen:api
   ```

4. If you change a template or a `gettext` string, run `npm run messages` from the root and fill
   in the Urdu and Arabic entries (see [Translations](#translations)).
5. If a decision changes, update the matching file in `docs/` in the same pull request.
6. If the change is security-relevant and can be tested over HTTP, add a check to
   `scripts/attack_simulation.py` and run it against the production image (commands in
   [AGENTS.md](AGENTS.md#commands)).

## Checks to run

CI runs these on every pull request, plus the OpenAPI schema and translation checks, pip-audit and
a production image build; run them locally first.

```bash
# Backend
cd backend
uv run ruff check .
uv run ruff format --check .
uv run mypy .
uv run --env-file ../.env pytest
uv run pytest tests/core --cov=apps/core --cov-branch --cov-fail-under=100

# Frontend
cd frontend
npm run lint
npm run typecheck
npm test
```

For UI changes, also check the page at phone (390 px), tablet (820 px) and desktop (1440 px)
widths, in light and dark themes, in English and in Arabic or Urdu, and attach screenshots to the
pull request.

## Pull requests

- Fill in the template and link the issue (`Fixes #123`).
- Commit messages are short and in the imperative, without prefixes: `Add business_days_between endpoint`.
- `main` is protected. Pull requests need the `backend`, `frontend` and `codeql` checks to pass and
  are squash-merged, so the history stays linear.

## Style

- **Python:** Ruff for linting and formatting, mypy in strict mode, type hints everywhere.
- **TypeScript:** strict mode, ESLint and Prettier.
- **Domain logic** lives in `backend/apps/core`, as plain Python with no Django imports and 100%
  branch coverage. Use the `holidays` library's own logic; don't reimplement it.
- **Layouts** use logical properties only (`ms-`, `ps-`, `text-start`, `inset-inline-*`) so they
  work right to left.
- **Comments** are few and explain why, not what. See the comment rules in [AGENTS.md](AGENTS.md).

## Translations

All user-facing text is translated into Urdu and Arabic.

- Frontend: `frontend/src/i18n/{en,ur,ar}.json` must have the same keys (a test checks this).
- Backend: `backend/locale/{ur,ar}/LC_MESSAGES/django.po`. Commit both the `.po` and the compiled
  `.mo` files. CI fails on untranslated, fuzzy or stale entries.
- After `npm run messages`, search for `#, fuzzy`: gettext sometimes matches a new string to an
  unrelated old translation. Fix those by hand.

The current Urdu and Arabic text was drafted by AI and hasn't been checked by native speakers yet.
If you are one, corrections are one of the most useful contributions you can make.

## Getting help

Ask in an issue, or write to [support@ahmershah.dev](mailto:support@ahmershah.dev).

By contributing, you agree that your contributions are licensed under the [MIT License](LICENSE).
