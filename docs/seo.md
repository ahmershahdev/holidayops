# SEO and public pages (Milestone 5)

The app UI is a logged-in SPA and is not indexed. Public pages are server-rendered Django templates, so
search engines get full HTML and no JavaScript is needed to read them.

## Pages

- Landing, pricing and API docs.
- One page per country and year, e.g. `/holidays/pk/2027/`, plus per-subdivision pages, generated from
  the same core functions and cached.
- Optional indexable page for calendars marked `is_public`.

## Every page has

- a unique `<title>` and meta description, and a canonical URL,
- `hreflang` for en/ur/ar (`/ur/holidays/pk/2027/`),
- Open Graph tags,
- JSON-LD: an `Event` per holiday and a `BreadcrumbList`.

## Crawling

- `sitemap.xml` via the Django sitemaps framework, split per country.
- `robots.txt` disallows `/app/` and `/api/`.

## Targets

Lighthouse ≥ 90 on public pages.
