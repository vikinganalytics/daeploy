# Daeploy UI Redesign — Design Spec

**Date:** 2026-06-21
**Branch:** `modernize-ui` (based on `updating-requirements`, so it builds on the upgraded Dash 4.1 / Pydantic v2 stack from PR #90)
**Status:** Approved design (mockup), pending spec review → implementation plan
**Mockup reference:** clickable mockup of all three screens (login, dashboard, logs) approved by the user.

## 1. Goal & scope

Modernize Daeploy's two web surfaces into one coherent, distinctive "control plane" UI.

- **In scope:** visual reskin of (a) the login page, (b) the dashboard, plus (c) a redesigned **logs view** with a streaming follow/auto-scroll toggle.
- **Pure reskin + one UX win:** same features and same stack (FastAPI-served Jinja login + Plotly **Dash** dashboard). The only new behavior is the logs **Follow** toggle (client-side auto-scroll control).
- **Out of scope:** backend/API changes, auth changes, new pages, framework replacement, light theme / theme toggle.

## 2. Constraints

- **Fully self-contained / offline-safe.** No external CDNs and no hot-linked images. Today `login.html` pulls Bootstrap 4.5 + jQuery from CDNs and hot-links the logo from `daeploy.com`; all of that must be replaced with local assets in `manager/assets/`. Daeploy is a deployment tool that may run air-gapped.
- **Keep the existing stack.** Login stays a Jinja2 template; the dashboard stays a Dash app whose layout is built in Python (`manager/routers/dashboard_api.py`) and styled by `manager/assets/dashboard_styles.css` (Dash auto-serves everything in `assets/`).
- **Preserve all current features & routes:** login form → `{{ ACTION }}`; dashboard service list (main/shadow, version, state, logs link, docs link); notifications (info/warning/critical); header actions (Logs, API Docs, Clear notifications, Log out); `v: <manager version>` indicator.

## 3. Design language

Direction: **modern dark "control plane"** for an audience of data scientists / algorithm engineers. Identity is grounded in the subject — Daeploy's whale mark and Viking Analytics' signal-analytics roots — via a sonar/waveform motif and a monospace data face for everything the machine reports.

### 3.1 Color tokens (CSS custom properties)

```
--ground:    #0E1320   /* deep navy-ink page background */
--surface:   #161C2C   /* panels/cards */
--surface-2: #1C2438   /* hover / inset */
--line:      #28324A   /* borders */
--line-soft: #1E2638   /* subtle dividers */
--text:      #E7ECF5   /* primary text (cool off-white) */
--muted:     #8B95AC   /* secondary text */
--faint:     #5C6680   /* tertiary / captions */
--accent:    #5EE6D0   /* teal — single vivid accent, brand-derived */
--accent-dim:#2E5A56   /* accent borders */
--accent-ink:#072019   /* text on accent fills */
--ok:        #3DDC97   /* running */
--warn:      #F4B740   /* warning */
--crit:      #F2585B   /* critical / stopped-error */
```

Teal is the **only** vivid accent. Status colors are functional signals, not decoration. Every color in CSS derives from these `:root` variables.

### 3.2 Typography

- **UI / display:** system sans stack — `"Segoe UI", system-ui, -apple-system, Roboto, Helvetica, Arial, sans-serif`. Personality comes from weight contrast, tight tracking on the wordmark, and uppercase letterspaced micro-labels.
- **Data / utility:** monospace — used for all machine-reported data (versions, timestamps, state, severity tags, log lines, micro-labels).
- **Self-contained fonts:** the production build **bundles** woff2 files in `manager/assets/fonts/` and references them via `@font-face` (no CDN). Recommended: **Inter** (UI) + **JetBrains Mono** (data). The mockup approximated these with system stacks because the preview sandbox blocks external fonts; the real build ships the woff2s. Final font choice can be confirmed at implementation time, but it MUST be bundled, not linked.

### 3.3 Layout & components

- **Wordmark/logo:** small inline SVG "sonar wave" glyph in teal + `dae**ploy**` wordmark (teal second syllable). Replaces the hot-linked PNG. Ship as a local SVG/PNG asset.
- **Login:** centered glass card on the dark ground over a subtle, looping **sonar/waveform canvas** backdrop (the one deliberate motion moment; `prefers-reduced-motion` respected). Card holds wordmark, heading, Username + Password fields (teal focus ring), teal primary "Log in" button, and a footer line ("manager online" status + "by Viking Analytics").
- **Dashboard:** top bar (wordmark, `manager v: latest` chip, actions). The **service list is the hero** — one row per service with: a status dot (running = pulsing green, shadow = teal, stopped = grey), name + monospace version, a teal ★ for the main version / `shadow` badge for shadow deployments, "Running since <ts>" in mono, and inline Logs/Docs links. A **notifications panel** on the right with a severity-coded left rule (info/warn/crit) and mono meta line. Responsive: collapses to a single column under ~760px.
- **Logs view:** top bar + a single console panel.
  - Streaming, monospace console with severity styling: `INFO` muted, `WARN` amber left-rule, `ERROR` red left-rule + tint. Each line: timestamp · level · source tag · message.
  - **Follow toggle** (switch styled checkbox, top-right): when ON, new lines append and the console auto-scrolls to the newest; a pulsing green **● Live** indicator shows.
  - **Smart pause:** scrolling up while following auto-disables Follow, flips the indicator to **Paused**, and reveals a **"Jump to latest ↓"** pill. Clicking it (or re-checking Follow) snaps to the bottom and resumes.
  - Line buffer capped (~400 lines) to keep the DOM light.

### 3.4 Copy

Written from the end user's side, sentence case, active voice. Examples: "Sign in to your control plane", "Mirroring traffic" for shadow services, actionable notification messages ("anomaly-detector stopped after 3 failed restarts"). Actions keep their names through the flow.

## 4. Implementation outline (for the plan; not the plan itself)

1. **Assets (`manager/assets/`):** add bundled font woff2s + `@font-face`; add a local logo SVG; (optionally) a shared `tokens.css` with the `:root` variables imported by both surfaces.
2. **Login (`manager/templates/login.html`):** drop Bootstrap/jQuery CDNs and the hot-linked logo; rebuild markup + inline (local) CSS per the design; keep the `{{ ACTION }}` POST form and field `name`s (`username`, `password`) intact; add the sonar canvas + reduced-motion guard.
3. **Dashboard (`manager/routers/dashboard_api.py` + `manager/assets/dashboard_styles.css`):** restyle and lightly restructure the Python-built layout (banner → top bar; services `html.Table` → row layout with status dots/badges; notifications panel). Preserve callbacks, tab/refresh interval, links, and the clear-notifications action.
4. **Logs view:** identify how logs are currently surfaced (the `/logs` and `/services/~logs` routes / Dash links) and render the streaming output in the new console with the client-side Follow/auto-scroll + jump-to-latest behavior. Backend already streams with `follow=true`; the toggle is presentation-only.
5. **Verification:** run the manager locally in Docker (build image, deploy a sample service) and visually confirm login, dashboard, and live logs; confirm no external network requests are made by the UI (offline check).

## 5. Risks & notes

- Dash builds HTML in Python, so dashboard restyling spans both the `.css` and the component tree in `dashboard_api.py`; keep changes scoped to layout/className, not callback logic.
- Bundled fonts add a few hundred KB to `manager/assets/` — acceptable for offline support; subset if size matters.
- The mockup's bottom screen-switcher is a mockup-only affordance and is NOT part of the product.
- Base branch builds on `updating-requirements`; if PR #90 merges first, rebase onto `develop`.
