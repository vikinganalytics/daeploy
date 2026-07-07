# Logs Viewer Enhancements + Responsive Layout — Design Spec

**Date:** 2026-06-29
**Branch:** `logs-viewer-enhancements` (off `develop`)
**Status:** Approved design, pending spec review → implementation plan
**Builds on:** the 1.4.0 UI redesign ([[daeploy-ui-redesign]]); same FastAPI + Dash + self-contained-assets stack.

## Goal

Make the redesigned UI use the screen better and turn the logs view into a real log console:

- **A. Responsive logs view** — fills the viewport (height + width) instead of a fixed `60vh` / `1180px` card.
- **B. Responsive dashboard** — uses much more of the screen instead of a `1180px` centered column.
- **C. Export logs** — download a service's (or the manager's) full log as a file.
- **D. Search logs** — find text across the full log, filtered to matching lines.

## Constraints

- **Reuse the shared `manager/templates/logs.html`** — it already serves both per-service (`/services/~logs/view`) and manager (`/logs/view`) logs, so both get every feature here.
- **No backend changes.** The existing endpoints already support what's needed: `/services/~logs?...&tail=all&follow=false` and `/logs/stream?tail=all&follow=false` return the full log. Export and search are client-side fetches against these.
- **Self-contained** (no CDNs), consistent with the redesign tokens/theme.
- **Preserve the live tail** — streaming + the Follow/auto-scroll/jump behavior stay; the new features layer on top.

## A. Responsive logs view

- Drop `.page { max-width:1180px }` for the logs page → full width with modest side padding.
- Lay the page out as a **flex column filling the viewport**: top bar + `.logs-head` toolbar take natural height; `.console` gets `flex:1` (and `min-height:0`) so it grows/shrinks with the window and screen resolution. Remove the fixed `height:60vh`.
- Buffer cap stays for the *live tail* (keep DOM light); search/export bypass it by fetching the full log.

## B. Responsive dashboard

- In `manager/assets/dashboard_styles.css`, change `.page { max-width:1180px }` → `max-width:1600px` (still centered, generous side padding). The services/notifications `.grid` then uses far more width. (Decision: capped 1600px centered, not fully fluid — avoids absurd line lengths on ultrawide.)

## C. Export logs to a file

- An **Export** button in the logs toolbar (`.logs-tools`).
- On click: fetch the **full** log (`full_url`, i.e. the endpoint with `tail=all&follow=false`), build a `Blob`, and trigger a download.
- **Filename:** `‹title›_‹subtitle›_‹UTC-timestamp›.log` for services (e.g. `status_code_v0.1.0_20260629-153012.log`); `manager_‹UTC-timestamp›.log` for manager logs. Plain text, `.log`.
- Pure client-side (`fetch` → `Blob` → object URL → `<a download>`). Works on both views.

## D. Search (filter to matches)

- A **search input** in the toolbar, with a **match-count** label.
- On input (debounced ~250 ms) with a non-empty term: fetch the full log once (`full_url`), render **only lines containing the term** (case-insensitive substring), **highlight** the matched substring, and show the count (e.g. `37 matches` / `No matches`).
- **Follow auto-pauses** while a search is active (you're viewing history, not the tail).
- **Clearing** the box restores the **live tail** by clearing the console and restarting the live-tail stream (re-fetch `stream_url`, `tail=200&follow=true`), with Follow re-enabled.
- Highlighting uses DOM text nodes + a `<mark>`-style span (never `innerHTML` on log content — XSS-safe, consistent with the existing `textContent` rendering).
- No regex / no case toggle for now (YAGNI); case-insensitive substring only.

## Toolbar layout

`[🔍 search…] [37 matches] · [Export] · [● Live] [Follow ▢]` — search + count on the left of the tools group, Export next, then the existing Live indicator + Follow toggle.

## Implementation outline (for the plan)

1. **Routes** (`manager/routers/service_api.py::service_logs_view`, `manager/routers/logging_api.py::manager_logs_view`): pass one extra context value, **`full_url`** (the same endpoint as `stream_url` but `tail=all&follow=false`), e.g. service `/services/~logs?name=..&version=..&tail=all`; manager `/logs/stream?tail=all`.
2. **`manager/templates/logs.html`**: add the search input + match-count + Export button to `.logs-tools`; CSS for the full-bleed flex layout, the search box, and `<mark>` highlight; JS for export (fetch full → download), search (fetch full → filter/highlight/count, pause follow), and clear-search (resume tail).
3. **`manager/assets/dashboard_styles.css`**: `.page` max-width 1180 → 1600.
4. **Tests** (`tests/manager_test/test_ui_redesign.py`): assert `logs.html` has the search input, match-count, and Export elements; assert the view routes include `full_url` (tail=all); assert the logs `.page` is no longer capped at 1180 and the dashboard `.page` is 1600.
5. **Verify** live in the running manager: resize (console fills viewport), export downloads a `.log`, search filters with a count, clear resumes the tail; dashboard uses the wider layout.

## Risks / notes

- Fetching `tail=all` on a very large log transfers the whole thing for export/search — acceptable and expected per the "full history" decision; the live tail still uses `tail=200`.
- Search refetches the full log on each new term (debounced); fine for typical logs. Could cache the fetched full log per session as a later optimization (not now).
- This is a separate feature branch off `develop`; ships in a later release (e.g. 1.4.1 / 1.5.0), independent of the in-flight 1.4.0 PyPI publish.
