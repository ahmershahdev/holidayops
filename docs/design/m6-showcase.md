# Milestone 6 design: showcase website

Owner decisions (2026-10-17): logo-led palette for the showcase **and** the web app, geometric
country patterns, **bold** motion, server-rendered landing page at `/` (the Playground moves to
`/playground` in the app).

Hard limits from the roadmap still hold for every part: Lighthouse ≥ 90, fully readable without
JavaScript, `prefers-reduced-motion` respected, correct in RTL (ur, ar).

## 6.1 Art direction

### Palette

From the logo (`docs/brand/holidayops-logo.png`): navy wordmark, bright teal "Ops" and swoosh.
Every text pair below is WCAG AA (4.5:1) or better; graphics need 3:1.

| Token | Hex | Use | Contrast |
|---|---|---|---|
| `paper` | `#f7fafc` | page background | |
| `surface` | `#ffffff` | cards, tables | |
| `ink` | `#0b1b3f` | text, headings (logo navy) | 16.1 on paper |
| `muted` | `#4a5874` | secondary text | 6.8 on paper |
| `line` | `#d5dde8` | borders (decorative) | |
| `accent` | `#0e7c76` | links, buttons, focus ring (teal-600) | 5.0 on surface; white on it 5.0 |
| `accent-strong` | `#0b6b66` | hover, text on `accent-soft` | 5.6 on accent-soft |
| `accent-soft` | `#e0f5f3` | selected states | |
| `glow` | `#00b3a6` | logo teal: patterns, fills, motion, accents on navy | **2.6 on white: never text or meaningful lines on light backgrounds**; navy on it 6.4; on navy 8.8 (as `#00d1c1`) |
| `night` | `#0b1b3f` | dark sections (with `#e8f1f8` text 14.8, `#9fb3c8` muted 7.9) | |
| `holiday` / `-soft` | `#b23c22` / `#fbe9e4` | public holidays | 5.0 |
| `closure` / `-soft` | `#8a2c5a` / `#f6e6ee` | company closures | 6.8 |
| `halfday` / `-soft` | `#8f5a0a` / `#f8eedb` | half days | 5.0 |
| `workday` / `-soft` | `#23704a` / `#e1f2e8` | working days | 5.2 |
| `weekend` / `-strong` | `#eef2f7` / `#c9d3e0` | weekend cells (text `#5b6b86`, 4.8) | |

The tokens are defined twice, in `frontend/src/index.css` (Tailwind `@theme`) and
`backend/apps/public/static/public/site.css`; `tests/public/test_tokens.py` fails if they drift.

### Type

- Display: **Outfit** (variable, OFL), the closest open match to the logo's rounded geometric
  wordmark. Headings, the wordmark, big numbers.
- Body: **IBM Plex Sans**, as before. Urdu: Noto Nastaliq Urdu; Arabic: IBM Plex Sans Arabic.
- All fonts self-hosted (`@fontsource`); the public pages preload one Outfit file and use
  `font-display: swap`, so text renders in the fallback first.
- Scale (rem): 0.875 · 1 · 1.25 · 1.5 · 2 · 3 · clamp(2.5, 6vw, 4.5) for the hero.

### Patterns (built in 6.3)

Each country gets a deterministic SVG banner generated server-side from its code: a grid of
simple geometric tiles (triangles, arcs, stars, bars) whose motif, rotation and density come from a
hash of the code, coloured with that country's flag colours where we have a curated list and the
brand palette otherwise. No image files, a few hundred bytes inline, crisp at any size, mirrored
in RTL.

### Motion (bold, but bounded)

| Rule | Detail |
|---|---|
| CSS only | Scroll-driven animations (`animation-timeline: view()` / `scroll()`), cross-document View Transitions (`@view-transition { navigation: auto }`), SVG stroke animation. No animation library, no JS required for any of it. |
| Signature | The logo's flight path: a teal line drawing across the hero and between sections. |
| Storytelling | Landing sections reveal, slide and pin with the scroll; a calendar demo animates its days. |
| Timing tokens | `--ease-out: cubic-bezier(.2,.8,.2,1)`, `--dur-fast: 150ms`, `--dur: 400ms`, `--dur-slow: 900ms`. |
| Only cheap properties | `transform`, `opacity`, `clip-path`, `stroke-dashoffset`; never layout properties. |
| Reduced motion | Under `prefers-reduced-motion: reduce` every animation and view transition is off and content is in its final state. |
| Unsupported browsers | Scroll-driven animations sit inside `@supports (animation-timeline: view())`; without support the page is simply static. |
| RTL | Horizontal motion uses logical directions (flips in ur/ar). |

A living style guide at `/style/` (noindex) shows the palette with contrast, the type scale and
the motion primitives, so every later part can be checked against it.

### Site frame (shared by the public pages and the web app)

- **Header**: sticky glass bar (blurred paper), logo mark + two-tone wordmark, nav with a teal
  underline that draws from the reading start, segmented language (EN · اردو · عربي) and theme
  (light · device · dark) switches, log in, "Start free". It settles (border, shadow, smaller mark)
  over the first 8rem of scroll via a scroll-driven animation. Below 56rem: a full-screen sheet with
  large display-type links (`<details>` on public pages, so no JavaScript; React state in the app).
  The header's `backdrop-filter` is dropped while the sheet is open: it would otherwise become the
  containing block of the fixed sheet.
- **Footer**: night panel with rounded top and a soft teal glow. A call-to-action band (the hero
  line "Every working day, in every country." with log in + start free, the same pair as the
  header), the logo's route drawn across the panel ending in a dot, four columns (brand, product,
  popular countries, developers), switches, credit, a round back-to-top button, and an oversized
  outlined "HolidayOps" that rises in. Footer links use the header's route underline. The styles
  are one `frame:footer` block pasted into both `site.css` and the app's `index.css`;
  `tests/public/test_frame_css.py` fails if the copies drift. On phones the product and developer
  columns sit side by side and the countries list wraps into two columns.
- **Mark**: a simplified logo (teal and navy bars, swoosh, plane) as inline SVG and
  `icon.svg` favicon that follows the device theme.
- **Scrollbar and selection**: thin teal thumb on the page colour (`scrollbar-color`, ≥ 3:1,
  `auto` in forced colours), stable gutter; selection is navy text on logo teal (7.1:1).

### Themes

- Light (above) and dark: dark uses lighter surfaces for depth (`#0a1428` page, `#111d36` cards),
  off-white text, a brighter teal with navy text on buttons (`on-accent`); every pair is AA,
  tested in `tests/public/test_tokens.py`.
- One `theme` cookie (`light` / `dark`; absent = follow the device) shared by both halves. The
  server writes it into `<html data-theme>` on public pages and into the web app's `index.html`,
  so there is no flash and no inline script; `system` uses `prefers-color-scheme`.
- No-JS switch: `/theme/<light|dark|system>/?next=` sets the cookie and redirects (same-site `next`
  only). The web app writes the same cookie from JavaScript.
- Public pages are cached server-side per theme; HTML is sent `no-cache` with `Vary: Cookie` so a
  switch shows at once, while static files keep long cache lifetimes.

### Error pages

Branded 404 ("This flight went off course", the route breaking into a dashed detour) on public
paths, in the URL's language; the web app has the same page for unknown client routes. `/api/`
and `/feeds/` keep JSON 404s. The 500 page is a static template with no database or request
context, so it renders even when those fail.

## 6.2 Landing page (next)

`/` (and `/ur/`, `/ar/`): hero with the flight-path animation, a no-JS "is it a working day?"
demo (a GET form answered by the server), product story (countries, company calendars, feeds,
webhooks, API keys), code sample, pricing summary, links into the country pages.

## 6.3 Country pages (done)

- **Banner** (`apps/public/patterns.py`, `_pattern.html`): 20×4 tiles of three motifs out of six
  (quarter, half circle, triangle, dot, bar, star), with turns and gaps from a SHA-256 seed of the
  country code. Colours are read from the country's own flag SVG: the most used ones that reach
  1.8:1 on the night panel, at most four, topped up with brand teal. Inline, `aria-hidden`, about
  4 KB, mirrored in RTL; alternate rows drift as it scrolls.
- **Year calendar**: twelve months from the same `month_grid` the landing hero uses, revealed on
  scroll, `aria-hidden` because the table below lists the same days. Phones: two months a row with
  CLDR narrow day names (M T W, ح ن ث); Urdu stays one a row with full names, because CLDR has no
  narrow Urdu names.
- **View Transitions** between years: banner and heading morph, the calendar rises in.
- **Language**: country names, day and month names and lists come from CLDR (Babel), the same data
  the web app gets from `Intl`. Lists use each language's own pattern ("Friday and Saturday",
  «الجمعة والسبت», «جمعہ اور ہفتہ», «ب، ج، اور د»), never a hard-coded ", ". Django's own Urdu
  and Arabic date names differ in places (Urdu Saturday ھفتہ instead of ہفتہ), so public pages
  use the `cldr` filter, keeping Latin digits.

## 6.4 Performance and accessibility

Lighthouse ≥ 90 measured from Linux (CI) for `/`, a country page and pricing; axe with no
violations; reduced-motion and RTL screenshots; the web app's bundle split (Lighthouse 47 on
throttled mobile today).
