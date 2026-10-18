# Changelog

What changed in HolidayOps, newest first. The site renders this file at `/changelog/`: keep the
format (`## YYYY-MM-DD: Title`, then `- ` items) when you add an entry.

## 2026-10-18: Status page, changelog and SDKs

- A public status page with live checks of the API, database, cache, background jobs and holiday data.
- This changelog, on the site and in the repository.
- Python and TypeScript SDKs generated from the public part of the OpenAPI schema.

## 2026-10-18: Who is off today, widget and overlap tool

- A "who is off today" page for the whole world, each country on its own local date.
- A "today" page per country with this week, the next holiday and the next working day.
- An embeddable widget any site can place with one line of HTML.
- A working-day overlap tool: up to four countries, the days everyone works.

## 2026-10-18: Account security

- Two-factor sign-in with an authenticator app and single-use recovery codes.
- Sign in with Google or Microsoft.
- Download all your data, or delete your account, from account settings.
- Password reset by a 6-digit emailed code that expires in 10 minutes.
- New log in, sign up and reset pages with a 3D globe of flight routes.

## 2026-10-18: New landing page and site pages

- A landing page with live data: who is off today, weekend patterns and upcoming holidays.
- About, contact, privacy and terms pages.
- Breadcrumbs, structured data, llms.txt, and an installable web app with an offline page.

## 2026-10-17: Showcase site

- Art direction from the logo, a light and dark theme, and branded error pages.
- Country pages with flags, flag-coloured patterns and full-year calendars.
- Country, day and month names from CLDR in English, Urdu and Arabic.

## 2026-10-17: Plans, public pages and production image

- API keys with per-key rate limits, monthly quotas and a usage chart.
- Server-rendered public holiday pages and sitemaps for every country.
- A production Docker image with a health check and a deployment pipeline.

## 2026-10-17: Subscriptions

- Private iCal feeds for Google Calendar, Outlook and Apple Calendar.
- A monthly email digest of the next 30 days of holidays.
- HMAC-signed webhooks with retries and a delivery log.
- Organization invites by email.

## 2026-10-16: First release

- The public API: countries, holidays, and business-day check, add and between.
- Accounts, organizations with roles, and company calendars that merge countries with your own days.
- The web app in English, Urdu and Arabic, with month, year and list views.
