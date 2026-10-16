# Milestone 3 design: the app UI

Logged-in React app at `/app` plus the public playground at `/`. It must be fully usable in English,
Urdu and Arabic (RTL), on a phone, and with a keyboard or screen reader.

## Design system: "calm editorial"

A trustworthy almanac rather than a dashboard: warm paper, ink text, one deep teal accent, colour used
only to carry meaning. Tokens live in `frontend/src/index.css` (`@theme`); components use tokens only.

| Token | Value | Use |
|---|---|---|
| `paper` | `#FBF8F3` | page background |
| `surface` | `#FFFFFF` | cards |
| `ink` | `#1C1917` | text |
| `muted` | `#6B635A` | secondary text (AA on paper) |
| `line` | `#E7E1D8` | borders, rules |
| `accent` | `#0F5E5A` | links, primary buttons, focus ring |
| `holiday` | `#B4432B` | public holidays |
| `closure` | `#7A2E4D` | company closures |
| `halfday` | `#9A6412` | half days |
| `weekend` | `#F1EBE1` | weekend cell tint |
| `workday` | `#2F6B3F` | "business day" status |

Type: Fraunces (display, Latin), IBM Plex Sans (UI, Latin), IBM Plex Sans Arabic (Arabic UI and
display), Noto Nastaliq Urdu (Urdu, line-height 2.2). All self-hosted through `@fontsource`, so the
CSP needs no font CDN. Scale: 12/14/16/20/28/40 px. Radius 10 px, hairline borders, no heavy shadows.

Status is never colour alone: every marked day also has a text label or symbol and an `aria-label`.

## Day-range endpoint

`GET /api/v1/business-days/range/?country=PK|calendar=<uuid>&start=&end=` (≤ 366 days) returns one
`CheckResult` per day. The month and year views draw exactly this, so weekend rules that change by
date and company weekends stay in the backend (`apps/core.describe_days`).

Holiday lists for a company calendar gain `sources`: the source country codes that contribute each
holiday, which powers the per-source filter.

## Views

| Route | Content |
|---|---|
| `/app/:org/calendars/:id` | Month view (default), year view, list view; source filter; click a day to add, edit or remove a custom day |
| `/app/:org/calendars/:id/settings` | Name, sources (country, subdivision, categories), weekend, language, public, delete |
| `/app/:org/settings` | Rename org, members: change role, remove (admins) |

Week rows start on the day after the calendar's weekend ends (Monday for Sat–Sun, Sunday for
Fri–Sat). Months are in the UI language via `Intl.DateTimeFormat`.

## i18n and RTL

- i18next with `en`, `ur`, `ar` JSON in `frontend/src/i18n/`; choice saved in `localStorage`,
  default from the browser.
- `<html lang dir>` follows the language. Layout uses logical properties only (`ms-`, `ps-`,
  `text-start`), so mirroring is automatic; arrows and chevrons flip with `rtl:` variants.
- Requests send `Accept-Language`; Django's `LocaleMiddleware` translates API error messages from
  `backend/locale/{ur,ar}` (compiled in CI and in the Docker image).
- Holiday names in country mode use the matching library language when the country supports it
  (`ur_PK`, `ar`).
- Urdu and Arabic strings need a native-speaker review before launch.

## Accessibility

Month grid is a `role="grid"` with arrow-key navigation (roving tabindex), Home/End, PageUp/PageDown
for months. Visible focus ring, AA contrast, `prefers-reduced-motion` respected.
