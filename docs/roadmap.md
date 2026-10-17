# Roadmap and delivery plan

Each milestone is split into parts that can each ship as one PR (or a few small ones). A part is done
when its tests pass in CI and the docs it touches are updated.

"Done" for the project: live demo URL, README with setup, tests in CI, seed data, screenshots.

## Milestone 1 — API over `holidays` with business-day maths ✅

| Part | Scope | Done when |
|---|---|---|
| 1.1 Scaffold | `backend/` with uv, pinned deps, settings split, Ruff, mypy, pytest config, Docker Compose (MySQL, Redis, backend), `.env.example` | `pytest` runs; `ruff` and `mypy` are clean |
| 1.2 Core domain | `apps/core`: `get_calendar` (LRU), `is_business_day`, `add_business_days`, `business_days_between`, country metadata, validation errors | 100% branch coverage, no Django imports |
| 1.3 API | DRF views + serializers for countries, holidays, check, add, between; input limits; OpenAPI + Swagger | API tests cover happy paths, limits and bad input |
| 1.4 Hardening | Anonymous per-IP throttle (Redis in prod), security headers incl. CSP | Throttle and header tests pass |
| 1.5 CI | GitHub Actions: Ruff, mypy, pytest with MySQL service, pip-audit, CodeQL | Workflow green on a PR |

Deferred on purpose: the Redis cache for serialized holiday lists. The in-process LRU already serves
a country-year in well under a millisecond; Redis is added in 5.3 when there are several workers.

## Milestone 2 — Organizations, company calendars, auth ✅

Design: [design/m2-orgs.md](design/m2-orgs.md). Parts 2.1–2.5 are implemented; invites by email
shipped after Milestone 4.3 (email sending).

| Part | Scope |
|---|---|
| 2.1 Accounts | Custom user model, Argon2, sign-up, login/logout (session + CSRF) |
| 2.2 Orgs | `Organization`, `Membership` with roles, invites, `AuditLog`, org-scoped querysets |
| 2.3 Calendars | `Calendar`, `CalendarSource`, `CustomDay`; `merge_calendars` in core (half-days flagged) |
| 2.4 Calendar API | CRUD endpoints, `calendar=<id>` on the business-day endpoints, role permissions |
| 2.5 Isolation suite | Cross-org access test on every endpoint, expecting `404` |

## Milestone 3 — React UI ✅

Design: [design/m3-ui.md](design/m3-ui.md).

| Part | Scope |
|---|---|
| 3.1 Frontend scaffold ✅ | Vite, React, TS strict, Tailwind, ESLint/Prettier, Vitest, generated API client; playground, auth, orgs, calendar and custom-day pages |
| 3.2 Design system ✅ | "Calm editorial" tokens, self-hosted fonts, shared components |
| 3.3 i18n + RTL ✅ | i18next en/ur/ar, `dir` switching, logical properties, Django `.po` files |
| 3.4 Calendar views ✅ | Day-range endpoint, month/year/list views, per-source filter, keyboard grid |
| 3.5 Custom days ✅ | Add, edit and remove closures, half-days and extra working days from the calendar |
| 3.6 Settings ✅ | Calendar settings (sources, weekend, language, public, delete); org settings and members |

API keys and the usage chart move to Milestone 5, where keys are created.

## Milestone 4 — Subscriptions ✅

Design: [design/m4-subscriptions.md](design/m4-subscriptions.md).

| Part | Scope |
|---|---|
| 4.1 Celery ✅ | Worker + Beat in Compose, task conventions |
| 4.2 iCal feeds ✅ | `FeedToken`, hashed and rotatable, cached `.ics` |
| 4.3 Digests ✅ | Monthly email "holidays in the next 30 days" |
| 4.4 Webhooks ✅ | HMAC signing, SSRF guard, retries with backoff |

## Milestone 5 — Plans, limits, launch (code done; hosting deferred to launch)

Design: [design/m5-api-keys.md](design/m5-api-keys.md) (5.1).

| Part | Scope |
|---|---|
| 5.1 API keys ✅ | `hops_<prefix>_<secret>`, hashed, per-key throttles, quotas, `UsageEvent` |
| 5.2 Public SEO pages ✅ | See [seo.md](seo.md) |
| 5.3 Deployment ✅ (host setup pending) | Production settings, HTTPS, health endpoint, Redis list cache, CD pipeline, demo URL, seed data |
| 5.4 Docs (at launch) | README setup, API examples, screenshots |

## Milestone 6 — Showcase website ← in progress

Design: [design/m6-showcase.md](design/m6-showcase.md).

Award-level public site built on Milestone 5's server-rendered pages and the Milestone 3 design
system. Art-directed landing page, illustrated country and year pages, motion through CSS scroll-driven
animations and View Transitions. Must keep Lighthouse ≥ 90, readable without JavaScript, respect
`prefers-reduced-motion`, and work in RTL.

| Part | Scope |
|---|---|
| 6.1 Art direction ✅ | Moodboard, illustration system, motion principles |
| 6.2 Landing page | Hero, product story, live API demo, pricing |
| 6.3 Country pages | Illustrated holiday pages per country and year |
| 6.4 Performance and a11y pass | Lighthouse, axe, reduced-motion and RTL checks |
