# SEO and public pages (Milestone 5)

The app UI is a logged-in SPA and is not indexed. Public pages are server-rendered Django templates
(`apps/public`), so search engines get full HTML and no JavaScript is needed to read them.

## Pages (5.2)

| Path | Page |
|---|---|
| `/holidays/` | Every supported country |
| `/holidays/<cc>/` | Redirects to the current year |
| `/holidays/<cc>/<year>/` | Holidays, working days and weekend for a country and year |
| `/holidays/<cc>/<subdiv>/<year>/` | The same for a subdivision (codes are case-insensitive) |
| `/pricing/` | Plans, read from `settings.PLANS` |

- Each path also exists under `/ur/` and `/ar/`. The prefix is a URL converter, not
  `i18n_patterns`: with an unprefixed English default, `i18n_patterns` would force English on every
  unprefixed path, including `/api/`, which relies on `Accept-Language`.
- Years: the current year ± 5 are served; others are `404`. The sitemap lists the previous year
  through two years ahead.
- Holiday names come from the library in the page language when the country has it (`ur_PK`,
  `ar`…), otherwise the country's English or default names. Country names are English only: the
  library has no translations and adding Babel isn't worth it yet.
- Pages are cached for 6 hours (`cache_page`) and sent with `Cache-Control: public, max-age=3600`.
- The landing page is Milestone 6.2; the optional page for `is_public` calendars is not built yet.

## Every page has

- a unique `<title>`, meta description and canonical URL,
- `hreflang` links for en, ur and ar plus `x-default` (the English page),
- Open Graph and Twitter card tags,
- on year pages, JSON-LD: one `Event` per holiday and a `BreadcrumbList`. JSON-LD is escaped like
  Django's `json_script`, so a holiday name can't close the `<script>` element.

## No JavaScript

The pages ship one stylesheet (`apps/public/static/public/site.css`, the web app's colour tokens,
system fonts, logical properties for RTL) and no script. Their CSP is `default-src 'none';
style-src 'self'; img-src 'self' data:; script-src 'none'`; JSON-LD blocks are data, not script.

## Crawling

- `/sitemap.xml` is an index; each country has its own section (`/sitemap-pk.xml`) and `pages`
  holds the index and pricing. Every URL carries its `hreflang` alternates. Cached for a day.
- `/robots.txt` disallows `/app/`, `/api/`, `/feeds/`, `/invite` and `/unsubscribe`, and points to
  the sitemap.
- In development, Vite proxies these paths to Django, so they work on port 5173 as well.

## Targets

Lighthouse ≥ 90 on public pages (checked as part of 5.3 deployment and Milestone 6.4).
