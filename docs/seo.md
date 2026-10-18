# SEO, public pages and discovery files

The web app is a logged-in SPA and is not indexed. Public pages are server-rendered Django
templates (`apps/public`): full HTML, one stylesheet, no JavaScript.

## Pages

| Path | Page | Languages |
|---|---|---|
| `/` | Landing: live "who is off today", weekend patterns, upcoming holidays, demo, FAQ | en, ur, ar |
| `/holidays/` | Every supported country | en, ur, ar |
| `/holidays/<cc>/<year>/` | Holidays, working days and weekend for a country and year | en, ur, ar |
| `/holidays/<cc>/<subdiv>/<year>/` | The same for a subdivision (codes are case-insensitive) | en, ur, ar |
| `/holidays/<cc>/today/` | Is today a working day there: verdict, next 7 days, next holiday, embed code | en, ur, ar |
| `/today/` | Every country on its own local date: on a holiday, on the weekend, at work | en, ur, ar |
| `/tools/overlap/` | Up to four countries, one month: days everyone works and who is off (GET form) | en, ur, ar |
| `/widget/<cc>/` | Embeddable widget (`?lang=`, `?theme=dark`), framable anywhere, noindex | en, ur, ar |
| `/pricing/` | Plans, read from `settings.PLANS` | en, ur, ar |
| `/about/`, `/contact/` | Project, owner, support channels | en, ur, ar |
| `/privacy/`, `/terms/` | Legal pages | en only |
| `/offline/` | Service worker fallback (noindex) | en |

- ur/ar live under `/ur/` and `/ar/` through a URL converter, not `i18n_patterns` (which would force
  English on unprefixed `/api/`).
- Legal pages are English only: an unreviewed translation would promise things the English text
  doesn't. Their language switch links to the ur/ar home page.
- Years: current year ± 5; the sitemap lists last year through two years ahead.
- "Today" is the country's local date (`apps/public/today.py`: CLDR zones, capital's zone for
  countries spanning several). The page cache key includes the hour, and `/today/` rebuilds hourly.
- The widget's CSP allows `frame-ancestors *` and it sends no `X-Frame-Options`; it has no forms or
  script. Its links open the country's today page in a new tab.
- Pages are cached 6 hours per theme; the landing's live data is cached per day and language
  (`apps/public/world.py`, about 1.5 s cold for all countries).

## Every page has

- `<title>` ≤ 60 characters and meta description ≤ 150 (`apps/public/seo.py`, `fit_title`;
  `tests/public/test_seo.py` checks every page and every country/region title in all languages),
- canonical, `hreflang` (en, ur, ar, `x-default`), Open Graph with a 1200×630 image, Twitter
  `summary_large_image`,
- visible breadcrumbs (Home first) with matching `BreadcrumbList` JSON-LD, except on the landing.

## Structured data

| Page | JSON-LD |
|---|---|
| Landing | `@graph`: `Organization` (owner, support email), `WebSite`, `WebApplication` with the free `Offer`, `FAQPage` |
| Year pages | One `Event` per holiday, `BreadcrumbList` |
| Others | `BreadcrumbList` |

JSON-LD is escaped like Django's `json_script` (`seo.ld_json`), so data can't close the element.

## Discovery files (`apps/public/discovery.py`)

| Path | Content |
|---|---|
| `/robots.txt` | Disallows `/app/`, `/api/` (docs and schema allowed), `/feeds/`, `/invite`, `/unsubscribe`, `/theme/`, `/offline/`; points to the sitemap |
| `/sitemap.xml` | Index: `pages` (with hreflang), `legal`, one section per country |
| `/llms.txt` | llmstxt.org summary with links |
| `/llms-full.txt` | Product, API reference, plans, every country with its weekend |
| `/manifest.webmanifest` | PWA manifest; icons in `public/static/public/` |
| `/sw.js` | Service worker: network-first pages with the offline fallback, cache-first hashed static files, nothing from `/api/`, `/app`, `/feeds/` |

The web app registers `/sw.js` in production; its scope covers the public pages, which stay free of
script. In development Vite proxies all of these paths to Django.

## Targets

Lighthouse ≥ 90 on public pages.
