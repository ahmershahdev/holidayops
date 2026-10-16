# Contributing to HolidayOps

Thanks for your interest. The project is in early development, so the setup steps below will grow as
the code lands.

## Before you start

- For a bug, open an issue with steps to reproduce.
- For a new feature or a bigger change, open an issue first so we can agree on the approach.
- Wrong holiday dates usually come from the [holidays](https://github.com/vacanza/holidays) library;
  please check there first.

## Workflow

1. Fork the repository and create a branch from `main` (`fix/short-name` or `feat/short-name`).
2. Keep each pull request to one change, with tests for new behaviour.
3. Run the tests and linters locally before pushing.
4. Open a pull request against `main` and fill in the template. Link the issue with `Fixes #123`.

`main` is protected: changes go in through pull requests, and pull requests are squash-merged.

## Local setup

Requirements: Python 3.12+, Node.js 22+, MySQL 8 and Redis (or Docker Compose).

Backend and frontend setup instructions will be added here with the first code.

## Code style

- Python: formatted and linted with Ruff, tested with pytest.
- TypeScript: ESLint and `tsc --noEmit`.
- Commit messages: short and in the imperative, e.g. `Add business_days_between endpoint`.

## License

By contributing, you agree that your contributions are licensed under the [MIT License](LICENSE).
