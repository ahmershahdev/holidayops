# Roadmap

A part is done when its tests pass in CI and the docs it touches are updated. Design notes for
each milestone are in [design/](design/).

## Done

| Milestone | Scope | Design |
|---|---|---|
| 1. Public API | `apps/core` domain layer, countries, holidays, check, add, between, OpenAPI, throttles, CSP, CI | [m1-api](design/m1-api.md) |
| 2. Organizations | Accounts (Argon2, sessions), orgs and roles, invites, audit log, company calendars, isolation suite | [m2-orgs](design/m2-orgs.md) |
| 3. Web app | React + TS, design system, en/ur/ar with RTL, month/year/list views, custom days, settings | [m3-ui](design/m3-ui.md) |
| 4. Subscriptions | Celery and Beat, iCal feeds, monthly digests, signed webhooks | [m4-subscriptions](design/m4-subscriptions.md) |
| 5. Plans and launch prep | API keys, quotas, usage chart, public SEO pages, production image, CD pipeline | [m5-api-keys](design/m5-api-keys.md) |
| 6. Showcase site | Art direction, site frame, landing page, country pages, performance pass | [m6-showcase](design/m6-showcase.md) |
| 6.5 Site upgrade (#36) | Live landing sections, about, contact, legal pages, breadcrumbs, JSON-LD, llms.txt, PWA | [seo](seo.md) |

## Open

| Item | Notes |
|---|---|
| Hosting | Deferred by the owner to launch (around GSoC 2027); Azure likely. Follow [deployment.md](deployment.md) |
| Lighthouse re-run | On Linux against the production image, after #31 to #36 |
| Translation review | Native-speaker pass over every ur/ar string |
| Legal review | Privacy policy and terms were drafted from what the code does; have them reviewed before launch |

## Next (proposed, not scheduled)

| Idea | Why |
|---|---|
| Self-serve account and data deletion, data export | The privacy policy promises it by email today |
| Billing for Pro (Stripe or Paddle) | Pro is arranged by email |
| Embeddable widget and a "today" page per country | Shareable, link-earning pages |
| Official SDKs (Python, TypeScript) generated from `schema.yml` | Faster integration |
| Public status page and changelog | Trust for API users |
| Two-factor authentication and SSO for organizations | Expected by larger teams |
| Error monitoring and uptime alerts | Needed once hosted |
| Calendar-to-calendar comparison ("overlap of working days in PK and SA") | A question teams ask often |
