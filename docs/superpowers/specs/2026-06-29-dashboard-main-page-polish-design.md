# Dashboard main-page polish — design

**Date:** 2026-06-29
**Branch:** `dashboard-main-page-polish` → `develop`
**Scope:** Frontend-only polish of the manager dashboard (the Dash "main page"). No backend, no API, no new data. The logs *view* page is explicitly out of scope (unchanged).

## Problem

On a wide monitor the dashboard reads top-heavy and sparse: content hugs the top with a large empty void below. Secondary issues raised by the user:

1. The **Services** panel feels too narrow relative to its importance.
2. The **Notifications** panel is unexplained — an empty "No notifications." reads as "what is this section?" rather than "nothing wrong."
3. The per-service **LOGS / DOCS** links are not obviously clickable (tiny uppercase text, underline only on hover).

## Goals

- Make Services the clear hero (wider) and Notifications a slim, self-explanatory right rail.
- Remove the top-heavy empty void without inventing new content.
- Make LOGS / DOCS read as actionable controls.

## Non-goals (YAGNI)

- No new stats/summary bar, service counts, or notification badges.
- No structural rewrite of the Dash layout or callbacks.
- No change to the logs view page, login, or any backend/endpoint.

## Design

All changes are in `manager/routers/dashboard_api.py` (layout markup) and
`manager/assets/dashboard_styles.css` (styling). The design tokens in
`tokens.css` are reused; no new colors.

### 1. Widen Services, slim the sidebar
`.grid` columns change from `1.85fr 1fr` to **`2.6fr 0.9fr`**. Services gets
the dominant width; Notifications becomes a narrow rail. The existing
`@media (max-width:760px)` rule already collapses to a single column, so the
mobile path is unchanged.

### 2. Explain Notifications
Add a one-line muted subtitle beneath the "Notifications" heading in the panel
head, e.g.:

> Alerts services raise via the SDK `notify()` — info, warnings, critical.

Implemented as a small `<p class="panel-sub">` element in the Notifications
panel head. A new `.panel-sub` style (muted, ~11px) renders it quietly. The
Services panel head is left as-is (no subtitle needed).

### 3. Make LOGS / DOCS obvious
Restyle the per-service `.lnk` links to small bordered pill buttons that reuse
the look of the existing `.act` controls (1px border, rounded, accent on
hover) instead of underline-on-hover text. Keep them compact so the row height
is unchanged. Markup stays the same (`<a class="lnk">`); only CSS changes,
plus an accessible `:focus-visible` ring to match `.act`.

### 4. Fix top-heavy emptiness
Vertically center the page content when it is shorter than the viewport, while
falling back to normal top-aligned scrolling once there are enough services to
fill the screen. Implemented with flex auto-margins (which center but never
clip):

- The body becomes a flex column filling `min-height:100vh` (banner + page).
- `.page` becomes a flex child with `flex:1` and `display:flex;
  flex-direction:column`.
- The inner `.grid` gets `margin-block:auto`. Auto margins center the grid
  vertically when there is spare room; when the grid is taller than the
  available space the margins collapse to zero and the page scrolls normally —
  no overflow clipping.

This removes the void below the cards on a tall screen without adding content.

## Testing

Extend the existing guard tests in `tests/manager_test/test_ui_redesign.py`
(asset/markup string asserts, consistent with the current approach):

- Notifications subtitle text (`panel-sub`) is present in the rendered layout.
- `.panel-sub` style exists in `dashboard_styles.css`.
- `.lnk` is styled as a bordered button (border + border-radius) and has a
  `:focus-visible` rule.
- `.grid` uses the new `2.6fr 0.9fr` template.
- Vertical-fill rule present (`min-height:100vh` on body, `flex:1` on `.page`).

Run locally before pushing: `black --check`, `flake8`, `pylint manager`, and
`pytest tests/manager_test/test_ui_redesign.py`.

## Rollout

Frontend-only; ships in the next `develop` → `master` release alongside the
logs-viewer work. The live server picks it up on the next manager image build
(connectors untouched).
