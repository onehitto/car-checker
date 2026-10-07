# Web frontend

Single-page application in `frontend/`, consuming the versioned REST API. It is
developed and built entirely in Docker (no local Node.js needed).

## Stack

| Concern        | Choice                                                        |
|----------------|---------------------------------------------------------------|
| Language       | TypeScript 5.9 (strict)                                       |
| Build / dev    | Vite 8, React 19                                              |
| Routing        | React Router 7 (data router, one route per screen and tab)    |
| Server state   | TanStack Query 5 (cache, retries, invalidation after writes)  |
| API client     | `openapi-fetch` with types generated from `/openapi.json` (`openapi-typescript`) |
| Forms          | react-hook-form + zod; API `fields` errors mapped onto inputs |
| Styling        | Tailwind CSS 4 with design tokens as CSS variables, logical properties for RTL |
| Primitives     | Radix Dialog and Dropdown menu (focus management, a11y)       |
| i18n           | i18next: English, French, Arabic (right-to-left)              |
| Charts         | Recharts                                                      |
| Tests          | Vitest + Testing Library (units), Playwright in Docker (end to end) |

## Docker workflow

| Command                     | What it does                                           |
|-----------------------------|--------------------------------------------------------|
| `docker compose up frontend`| Vite dev server on <http://localhost:5173> with hot reload; `/api` is proxied to the `api` service |
| `make fe-npm c="install x"` | Run any npm command in the container                   |
| `make fe-types`             | Regenerate `src/api/schema.d.ts` from the running API  |
| `make fe-check`             | Type check, lint, format check and unit tests          |
| `make fe-e2e`               | Playwright end-to-end tests against the running stack  |
| `make fe-build`             | Build the production image (`car-checker-web`)         |
| `docker compose --profile production up web` | Production image on <http://localhost:8080> |

The container runs as the `node` user (uid 1000), so files created inside
belong to the host user; `node_modules` lives in the project folder so the IDE
resolves types. Production: a multi-stage image builds static files served by
an unprivileged nginx that also proxies `/api` to the backend (same origin, no
CORS, strict CSP). Fonts are always emitted as files because the CSP refuses
`data:` fonts.

## Code layout

```
frontend/src/
  api/           openapi-fetch client (token refresh), generated schema, enum lists, file upload/download
  app/           query client (automatic refresh after writes)
  components/ui/ design system: buttons, fields, dialogs, logbook rows, odometer, plate, tabs, toasts
  components/charts/ chart theme (RTL-aware)
  features/<area>/   one folder per area: pages, tabs, form dialogs, queries
  i18n/          i18next setup and en/fr/ar catalogs
  lib/           formatting, form schemas and hooks, URL filters
  router.tsx     routes, every screen lazily loaded
e2e/             Playwright specs
```

## Screens

| Route | Screen |
|-------|--------|
| `/login`, `/register`, `/forgot-password`, `/reset-password` | Sign-in flows |
| `/` | Garage dashboard: warning lamps, vehicles with condition and next service, coming up, documents to renew, spending, latest alerts |
| `/vehicles`, `/vehicles/new`, `/vehicles/:id/edit` | Vehicle list (search, status), vehicle form, photo, deletion |
| `/vehicles/:id` | Overview: needs attention, condition gauge, service history, documents, costs, alerts |
| `/vehicles/:id/timeline` | Everything that happened, grouped by year, filterable by kind |
| `/vehicles/:id/maintenance[/schedules\|/oil-changes\|/parts\|/tires]` | Service history, maintenance schedules, oil changes, parts, tires (wheel layout, rotation, history) |
| `/vehicles/:id/mileage[/fuel]` | Odometer readings and chart; fill-ups, consumption and fuel spending |
| `/vehicles/:id/expenses[/statistics]` | Expenses; statistics by month, category, year, service frequency |
| `/vehicles/:id/documents[/files]` | Papers with expiry and reminders; every file of the vehicle |
| `/vehicles/:id/reminders[/notes]` | Reminders by date and/or mileage; notes |
| `/vehicles/:id/sharing` | Owner only: people with access and their role |
| `/alerts` | Alerts inbox: filters, read, dismiss, go to the source |
| `/statistics` | Spending across vehicles, per currency |
| `/garages` | Garages and mechanics |
| `/settings[/security\|/notifications\|/types\|/account]` | Profile and units, password and devices, notification channels, custom types, account deletion |

Tabs and sections are routes, and list filters live in the URL, so every view
can be bookmarked. Viewers see no editing controls; the API enforces the roles
anyway.

## Data and forms

* **Server state** is TanStack Query. Mileage, due dates, alerts, health scores
  and statistics are derived by the API, so a targeted cache invalidation would
  miss some: every successful write refreshes the queries on screen (a mutation
  can opt out, e.g. deleting a vehicle or the account). Stored files are fetched
  once as object URLs, released when they leave the cache.
* **Forms** are react-hook-form + zod. Inputs hold strings; field schemas trim
  them, turn blanks into `null` and parse numbers, keeping decimals as exact
  strings. Messages are translated when validation runs. API field errors land
  on their input, other errors above the form; business rules with a known code
  (e.g. `MILEAGE_DECREASE`) are shown in the user's language.
* **Units**: distances are stored in kilometres and typed and shown in the
  user's unit (km or mi); consumption is shown in L/100 km, km/L or mpg; money
  uses the vehicle's currency.

## Authentication

The access token stays in memory; the refresh token is stored in
`localStorage` to keep the user signed in. On a `401`, the client refreshes once
(single in-flight refresh shared by concurrent requests) and replays the
request; if refreshing fails the user is sent to the sign-in page. Because the
refresh token is readable by scripts, the production nginx sends a strict
Content-Security-Policy (no inline scripts, no third-party origins).

## Design plan

**Subject.** A personal vehicle logbook: the digital version of the service
booklet a garage stamps, for car owners who want to know what is due and keep
proof of what was done. Audience: individual owners and families, sometimes a
mechanic with read access.

**Color.**

| Token          | Hex       | Role                                                   |
|----------------|-----------|--------------------------------------------------------|
| `ink`          | `#17212B` | Text, primary buttons, instrument-cluster sidebar     |
| `paper`        | `#F2F4F5` | App background (cool grey)                             |
| `sheet`        | `#FFFFFF` | Panels, tables                                         |
| `rule`         | `#D5DBE0` | Borders and dividers                                   |
| `steel`        | `#5E6B78` | Secondary text                                         |
| `petrol`       | `#0B6E75` | Links, active navigation, focus ring                   |

Status colors are the warning lamps of a dashboard and are always paired with a
text label: ok `#2F7D4F`, upcoming `#2B6CB0`, due soon amber `#B7791F`, due
orange `#C2410C`, overdue / expired / critical red `#B42318`.

**Type.** Barlow, a grotesk drawn from highway signage and license plates, for
body text; Barlow Condensed for headings and numbers, always with tabular
figures. IBM Plex Sans Arabic replaces both when the interface is in Arabic.
Scale (px): 13 · 15 · 18 · 24 · 36, odometer 44–56.

**Layout.** A dark instrument-cluster sidebar holds the navigation and the
user's garage (each vehicle with its plate and mileage). Content is left-aligned
in a 1200 px column. A vehicle page opens with a header band — name, plate,
odometer — then one tab per area (overview, timeline, maintenance...).

```
+------------+-----------------------------------------------------------+
| Car Checker|  Family Logan                       [0][9][8][8][0][0] km |
|            |  Dacia Logan 2019   (12345-A-6)                           |
| Dashboard  |  Overview  Timeline  Maintenance  Schedules  Fuel ...     |
| Alerts (5) |-----------------------------------------------------------|
| Statistics |  Needs attention           | Documents                    |
| Garages    |  Brake fluid  overdue 70 d | Road tax   expired           |
| Settings   |  Inspection   due in 15 d  | Insurance  20 days left      |
|------------|-----------------------------------------------------------|
| My garage  |  Logbook                                                  |
|  Logan     |  12 Mar 2026  92 300 km  Oil change   Garage Atlas  420.00|
|  Clio      |  ...                                                      |
+------------+-----------------------------------------------------------+
```

On phones the sidebar becomes a drawer and tabs scroll horizontally.

**Principles.**
1. The odometer is the one bold element: mechanical drums with tabular
   digits, the last drum inverted like the tenths drum of a real odometer. The
   drums roll when a new reading is saved (the only orchestrated motion;
   disabled with `prefers-reduced-motion`).
2. History reads like a logbook — rows of date, mileage, what, where, cost —
   not grids of identical cards. Panels use 1 px rules, no decorative shadows.
3. Status uses the dashboard-lamp colors everywhere, never color alone.
4. Plain, active copy in sentence case; an action keeps its name from button to
   confirmation ("Record service" → "Service recorded").
5. Right-to-left ready: logical CSS properties only; dates and numbers formatted
   with `en-GB`, `fr-FR` and `ar-MA` (Latin digits, as used in Morocco).

**Review against generic defaults.** A light grey dashboard with a teal accent
alone would be the standard SaaS kit; what makes this one specific is the
signage typeface, the odometer and plate, the dashboard-lamp vocabulary and the
logbook rows. Cream backgrounds, serif display type, all-caps eyebrow labels,
gradient washes and card grids were deliberately left out.

## Internationalisation

English, French and Arabic. The language is applied to `<html lang dir>`,
saved in the profile (alerts, e-mails and catalog names come translated from
the API) and in the browser for the sign-in pages. Arabic uses all six plural
forms (a test checks every plural key) and IBM Plex Sans Arabic; numbers and
dates use `ar-MA` (Latin digits) and units are written the local way. Layout uses
logical properties only; the odometer, plates and charts stay left to right,
with the chart time axis reversed in Arabic.

## Tests

* Unit and component tests (Vitest + Testing Library, `make fe-check`):
  formatting, form schemas and server-error mapping, translations parity, UI
  components, due texts, the lower-odometer confirmation, fill-up price editing.
* End-to-end tests (Playwright, `make fe-e2e`, needs the stack running): sign
  in and out, add a vehicle, update the mileage and record a service, overdue
  schedule and its alert, switching to Arabic. One account is registered per
  run because registration is rate limited (10 per minute).

## Not covered yet

* Push and SMS notifications have no provider: their settings are hidden.
* Changing the sign-in e-mail and e-mail verification have no API yet.
* Notification preferences per alert type exist in the API; the settings page
  sets one rule per channel.

