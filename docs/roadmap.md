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
| 7. Accounts and tools (#38 to #41) | Branded API 404s for browsers, password reset by email code (Resend), WebGL auth pages, two-factor, Google and Microsoft sign-in, data export and deletion, who-is-off-today pages, widget, overlap tool | [security](security.md), [seo](seo.md) |
| 6.5 Site upgrade (#36) | Live landing sections, about, contact, legal pages, breadcrumbs, JSON-LD, llms.txt, PWA | [seo](seo.md) |

## Open

| Item | Notes |
|---|---|
| Before hosting | Email verification, no email enumeration, encrypted TOTP secrets, signup bot check, sessions screen, simulated-users attack test: see [status.md](status.md), "Next session" |
| Hosting | Free: Oracle Cloud Always Free VM + Cloudflare; see [status.md](status.md) and [deployment.md](deployment.md) |
| Lighthouse re-run | On Linux against the production image, after #31 to #36 |
| Translation review | Native-speaker pass over every ur/ar string |
| Legal review | Privacy policy and terms were drafted from what the code does; have them reviewed before launch |

## Next (proposed, not scheduled)

| Idea | Why |
|---|---|
| Billing for Pro (Stripe or Paddle) | Pro is arranged by email |
| Official SDKs (Python, TypeScript) generated from `schema.yml` | Faster integration |
| Public status page and changelog | Trust for API users |
| Error monitoring and uptime alerts | Needed once hosted |
