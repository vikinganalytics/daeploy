# Daeploy UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reskin Daeploy's login page and Dash dashboard into a modern-dark "control plane" UI, and add a streaming logs view with a Follow/auto-scroll toggle — fully self-contained (no CDNs).

**Architecture:** Keep the existing stack. Login and the new logs view are FastAPI-served Jinja2 templates; the dashboard stays a Plotly Dash app whose layout is built in Python (`manager/routers/dashboard_api.py`) and styled by CSS in `manager/assets/` (Dash auto-loads `assets/*.css`). A shared `manager/assets/tokens.css` (color/type tokens + bundled `@font-face`) is loaded by all three surfaces. A new `/assets` static mount serves tokens, fonts, and the logo SVG to the Jinja pages. The logs view is a thin HTML shell that `fetch`-streams the existing `GET /services/~logs?...&follow=true` `text/plain` endpoint and renders lines client-side.

**Tech Stack:** FastAPI, Jinja2, Plotly Dash 4.1, Starlette `StaticFiles`, vanilla CSS + JS (no build step, no external libraries).

**Canonical visual reference:** `docs/superpowers/specs/2026-06-21-ui-redesign.mockup.html` (the approved mockup, committed). All exact CSS rules, markup structure, the sonar-canvas script, and the logs streaming/Follow JS are taken **verbatim** from it; this plan says which slice of the mockup goes into which file and supplies all the FastAPI/Dash integration code that the mockup (a single static file) doesn't contain. When a step says "copy from the mockup", open that file and copy the named block exactly.

**Design spec:** `docs/superpowers/specs/2026-06-21-ui-redesign-design.md`.

## Global Constraints

- **No external network dependencies in the UI.** No CDN `<link>`/`<script>`, no hot-linked images. Forbidden substrings in shipped templates/CSS: `maxcdn`, `bootstrapcdn`, `googleapis`, `cloudflare`, `jquery`, `daeploy.com/wp-content`, `http://`, `https://` in asset URLs. All assets load from `/assets/...` (relative).
- **Keep the stack:** Jinja2 login (`manager/templates/login.html`), Dash dashboard (`manager/routers/dashboard_api.py` + `manager/assets/dashboard_styles.css`). No framework swap.
- **Preserve behavior:** login POST form must keep `action="{{ ACTION }}"`, `method="POST"`, and input `name="username"` / `name="password"`. Dashboard must keep its services list (main/shadow, version, state, logs+docs links), notifications (severity 0/1/2 = info/warning/critical), header actions (Logs, API Docs, Clear notifications, Log out), `v:<manager version>` indicator, the 5s `dcc.Interval` refresh, and the clear-notifications callback.
- **Color tokens (exact):** `--ground:#0E1320 --surface:#161C2C --surface-2:#1C2438 --line:#28324A --line-soft:#1E2638 --text:#E7ECF5 --muted:#8B95AC --faint:#5C6680 --accent:#5EE6D0 --accent-dim:#2E5A56 --accent-ink:#072019 --ok:#3DDC97 --warn:#F4B740 --crit:#F2585B`. Every color derives from these.
- **Fonts:** bundled woff2 in `manager/assets/fonts/` (Inter for UI, JetBrains Mono for data), referenced by `@font-face` with **relative** `url(fonts/...)` so they resolve under both `/assets/tokens.css` and Dash's `/dashboard/assets/tokens.css`.
- **Accessibility:** visible keyboard focus, `prefers-reduced-motion` respected (sonar + status pulse), `role="log"` on the console.
- **Branch:** `modernize-ui`.

---

## File Structure

- `manager/assets/tokens.css` — **(create)** `:root` color/type custom properties + `@font-face` declarations. Loaded by all three surfaces.
- `manager/assets/fonts/*.woff2` — **(create)** bundled Inter (400/500/600) + JetBrains Mono (400/500).
- `manager/assets/daeploy_mark.svg` — **(create)** the inline sonar-wave logo glyph (replaces the hot-linked PNG).
- `manager/app.py` — **(modify)** mount `StaticFiles` at `/assets`.
- `manager/templates/login.html` — **(rewrite)** self-contained login page.
- `manager/templates/logs.html` — **(create)** streaming logs view shell.
- `manager/routers/service_api.py` — **(modify)** add `GET /~logs/view` HTML route; add `Jinja2Templates`.
- `manager/routers/dashboard_api.py` — **(modify)** restyle/restructure layout helpers; point service "Logs" link at the new view.
- `manager/assets/dashboard_styles.css` — **(rewrite)** dashboard styles using the tokens.
- `tests/manager_test/test_ui_redesign.py` — **(create)** automated guardrail tests.

---

## Task 1: Design tokens, bundled fonts, and logo asset

**Files:**
- Create: `manager/assets/tokens.css`
- Create: `manager/assets/fonts/` (woff2 files)
- Create: `manager/assets/daeploy_mark.svg`
- Test: `tests/manager_test/test_ui_redesign.py`

**Interfaces:**
- Produces: `manager/assets/tokens.css` defining `:root` vars listed in Global Constraints, plus `@font-face` for families `Inter` and `JetBrains Mono`. Consumed by Tasks 2–4 via `<link rel="stylesheet" href="/assets/tokens.css">` (Jinja) and Dash auto-load.

- [ ] **Step 1: Write the failing test**

```python
# tests/manager_test/test_ui_redesign.py
from pathlib import Path

ASSETS = Path("manager/assets")

def test_tokens_css_defines_palette():
    css = (ASSETS / "tokens.css").read_text()
    for var, val in [("--ground", "#0E1320"), ("--accent", "#5EE6D0"),
                     ("--text", "#E7ECF5"), ("--crit", "#F2585B")]:
        assert f"{var}:{val}" in css.replace(" ", ""), f"missing {var}"
    assert "@font-face" in css
    assert "url(fonts/" in css.replace(" ", ""), "fonts must be referenced relatively"
    assert "http://" not in css and "https://" not in css

def test_fonts_bundled():
    woff2 = list((ASSETS / "fonts").glob("*.woff2"))
    assert len(woff2) >= 4, "expected Inter + JetBrains Mono weights"
    assert all(f.stat().st_size > 5000 for f in woff2), "woff2 files look empty"

def test_logo_is_local_svg():
    svg = (ASSETS / "daeploy_mark.svg").read_text()
    assert "<svg" in svg and "5EE6D0" in svg
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/bin/python -m pytest tests/manager_test/test_ui_redesign.py -v`
Expected: FAIL (files do not exist yet).

- [ ] **Step 3: Download bundled fonts**

Run (build-time vendoring into the repo; these are stable Fontsource woff2 endpoints):
```bash
mkdir -p manager/assets/fonts
base="https://cdn.jsdelivr.net/fontsource/fonts"
curl -fsSL "$base/inter@latest/latin-400-normal.woff2" -o manager/assets/fonts/inter-400.woff2
curl -fsSL "$base/inter@latest/latin-500-normal.woff2" -o manager/assets/fonts/inter-500.woff2
curl -fsSL "$base/inter@latest/latin-600-normal.woff2" -o manager/assets/fonts/inter-600.woff2
curl -fsSL "$base/jetbrains-mono@latest/latin-400-normal.woff2" -o manager/assets/fonts/jbmono-400.woff2
curl -fsSL "$base/jetbrains-mono@latest/latin-500-normal.woff2" -o manager/assets/fonts/jbmono-500.woff2
ls -l manager/assets/fonts
```
Expected: five non-empty `.woff2` files. (If the CDN is unreachable in your environment, vendor the same families' woff2 by any means; the only requirement is local `.woff2` files with these names.)

- [ ] **Step 4: Create `manager/assets/tokens.css`**

```css
/* Daeploy design tokens — single source of truth for color + type. */
@font-face{font-family:"Inter";font-weight:400;font-display:swap;src:url(fonts/inter-400.woff2) format("woff2");}
@font-face{font-family:"Inter";font-weight:500;font-display:swap;src:url(fonts/inter-500.woff2) format("woff2");}
@font-face{font-family:"Inter";font-weight:600;font-display:swap;src:url(fonts/inter-600.woff2) format("woff2");}
@font-face{font-family:"JetBrains Mono";font-weight:400;font-display:swap;src:url(fonts/jbmono-400.woff2) format("woff2");}
@font-face{font-family:"JetBrains Mono";font-weight:500;font-display:swap;src:url(fonts/jbmono-500.woff2) format("woff2");}

:root{
  --ground:#0E1320; --surface:#161C2C; --surface-2:#1C2438;
  --line:#28324A; --line-soft:#1E2638;
  --text:#E7ECF5; --muted:#8B95AC; --faint:#5C6680;
  --accent:#5EE6D0; --accent-dim:#2E5A56; --accent-ink:#072019;
  --ok:#3DDC97; --warn:#F4B740; --crit:#F2585B;
  --shadow:0 24px 60px -24px rgba(0,0,0,.7);
  --sans:"Inter","Segoe UI",system-ui,-apple-system,Roboto,Helvetica,Arial,sans-serif;
  --mono:"JetBrains Mono",ui-monospace,"SF Mono",Menlo,Consolas,monospace;
}
```

- [ ] **Step 5: Create `manager/assets/daeploy_mark.svg`**

Copy the inline `<svg ...>...</svg>` mark from the mockup's login card (the `<svg width="30" height="30" viewBox="0 0 32 32">…</svg>` block) into a standalone file, changing the root `<svg>` to `width="32" height="32"`:
```xml
<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32">
  <circle cx="16" cy="16" r="15" fill="none" stroke="#28324A" stroke-width="1"/>
  <path d="M5 19 C10 19 11 12 16 12 C21 12 22 19 27 19" fill="none" stroke="#5EE6D0" stroke-width="2.1" stroke-linecap="round"/>
  <circle cx="16" cy="12" r="1.7" fill="#5EE6D0"/>
</svg>
```
(The `xmlns` is required for a standalone SVG file and is not a network reference.)

- [ ] **Step 6: Run tests to verify they pass**

Run: `./venv/bin/python -m pytest tests/manager_test/test_ui_redesign.py -v`
Expected: the three Task-1 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add manager/assets/tokens.css manager/assets/fonts manager/assets/daeploy_mark.svg tests/manager_test/test_ui_redesign.py
git commit -m "Add UI design tokens, bundled fonts, and local logo mark"
```

---

## Task 2: Serve assets statically + reskin the login page

**Files:**
- Modify: `manager/app.py`
- Rewrite: `manager/templates/login.html`
- Test: `tests/manager_test/test_ui_redesign.py`

**Interfaces:**
- Consumes: `manager/assets/tokens.css` (Task 1) at `/assets/tokens.css`; `/assets/daeploy_mark.svg`.
- Produces: a `/assets` static route; a self-contained `login.html` that still posts to `{{ ACTION }}`.

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/manager_test/test_ui_redesign.py
from manager.templates import __file__ as _t  # noqa
TPL = Path("manager/templates")

FORBIDDEN = ["maxcdn", "bootstrapcdn", "googleapis", "cloudflare",
             "jquery", "daeploy.com/wp-content"]

def test_login_html_is_self_contained():
    html = TPL.joinpath("login.html").read_text()
    low = html.lower()
    for bad in FORBIDDEN:
        assert bad not in low, f"login.html still references {bad}"
    # keep the working form contract
    assert 'action="{{ ACTION }}"' in html
    assert 'name="username"' in html and 'name="password"' in html
    assert '/assets/tokens.css' in html

def test_assets_mounted(test_client):
    r = test_client.get("/assets/tokens.css")
    assert r.status_code == 200
    assert "--accent" in r.text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./venv/bin/python -m pytest tests/manager_test/test_ui_redesign.py -k "login or assets" -v`
Expected: FAIL (`/assets` not mounted; login.html still has CDNs).

- [ ] **Step 3: Mount the assets directory in `manager/app.py`**

Add the import near the other Starlette imports and mount it **before** the `/dashboard` mount:
```python
from starlette.staticfiles import StaticFiles
# ... after `app = FastAPI(...)` and other mounts:
app.mount("/assets", StaticFiles(directory="manager/assets"), name="assets")
```

- [ ] **Step 4: Rewrite `manager/templates/login.html`**

Replace the entire file. Use the mockup's **LOGIN** section as the source of truth: copy the login-related CSS (the `:root` reset is now in tokens.css — keep only login-specific rules: `.login-wrap`, `#sonar`, `.card*`, `.field*`, `.btn-primary`, `.mark`, `.wordmark`, `.dot-ok`, the reduced-motion block) into a `<style>` block, and copy the sonar `<canvas>` + card markup and the sonar `<script>`. Wire it to the template + local assets:

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Daeploy — Sign in</title>
  <link rel="icon" href="/assets/favicon.ico">
  <link rel="stylesheet" href="/assets/tokens.css">
  <style>
    /* paste the login-specific rules from the mockup here, unchanged.
       Replace the hard-coded --mono/--sans :root block — those now come
       from tokens.css. body uses var(--ground)/var(--text)/var(--sans). */
  </style>
</head>
<body>
  <div class="login-wrap">
    <canvas id="sonar"></canvas>
    <div class="card">
      <div class="mark">
        <img src="/assets/daeploy_mark.svg" width="30" height="30" alt="">
        <span class="wordmark">dae<b>ploy</b></span>
      </div>
      <h1>Sign in to your control plane</h1>
      <p class="sub">Deploy and manage your services from one place.</p>
      <form action="{{ ACTION }}" method="POST">
        <div class="field">
          <label for="u">Username</label>
          <input id="u" name="username" type="text" placeholder="admin" autocomplete="username">
        </div>
        <div class="field">
          <label for="p">Password</label>
          <input id="p" name="password" type="password" placeholder="••••••••" autocomplete="current-password">
        </div>
        <button class="btn-primary" type="submit">Log in</button>
      </form>
      <div class="foot">
        <span><span class="dot-ok"></span>&nbsp;&nbsp;manager online</span>
        <span>by Viking Analytics</span>
      </div>
    </div>
  </div>
  <script>
    /* paste the sonar <script> body from the mockup verbatim, but delete the
       startLogs/stopLogs and screen-switcher lines — keep only size()/draw()/
       startSonar()/stopSonar()/draw_once(), the reduce check, the resize
       listener, and a final startSonar(); call. */
  </script>
</body>
</html>
```
Keep the `{{ ACTION }}` form exactly. The mark is now `<img src="/assets/daeploy_mark.svg">` (the mockup used inline SVG; either is fine — use the img so it shares the asset).

- [ ] **Step 5: Run tests to verify they pass**

Run: `./venv/bin/python -m pytest tests/manager_test/test_ui_redesign.py -k "login or assets" -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add manager/app.py manager/templates/login.html tests/manager_test/test_ui_redesign.py
git commit -m "Reskin login page; serve bundled assets via /assets static mount"
```

---

## Task 3: Reskin the dashboard (CSS + Dash layout)

**Files:**
- Rewrite: `manager/assets/dashboard_styles.css`
- Modify: `manager/routers/dashboard_api.py` (layout-building functions only — NOT callbacks)
- Test: `tests/manager_test/test_ui_redesign.py`

**Interfaces:**
- Consumes: tokens.css (auto-loaded by Dash from `assets_folder="../assets"`).
- Produces: restyled dashboard. `generate_table_services`, `generate_table_notifications`, `build_banner`, `build_user_section` keep their **names and call signatures**; only the returned component tree + classNames change. `update_content` and the clear-notifications callback are unchanged.

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/manager_test/test_ui_redesign.py
def test_dashboard_css_uses_tokens():
    css = (ASSETS / "dashboard_styles.css").read_text()
    assert "var(--ground)" in css and "var(--accent)" in css
    assert "http://" not in css and "https://" not in css

def test_dashboard_layout_builds():
    # importing must not raise and layout must be present
    from manager.routers import dashboard_api
    assert dashboard_api.app.layout is not None
    # helper functions still exist with the same names
    for fn in ["generate_table_services", "generate_table_notifications",
               "build_banner", "build_user_section", "update_content"]:
        assert hasattr(dashboard_api, fn)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./venv/bin/python -m pytest tests/manager_test/test_ui_redesign.py -k dashboard -v`
Expected: `test_dashboard_css_uses_tokens` FAILS (old CSS has hard-coded hex, no `var(--…)`); `test_dashboard_layout_builds` may already pass (acceptable — it guards the refactor in Step 4).

- [ ] **Step 3: Rewrite `manager/assets/dashboard_styles.css`**

Replace the whole file. Port the mockup's **DASHBOARD** CSS section (`.top`, `.vchip`, `.actions`, `.act`, `.page`, `.grid`, `.panel*`, `.svc*`, `.pin*`, `.state*`, `.sdot*`, `.badge*`, `.lnk`, `.note*`, `.sev*`, `.empty`, `@keyframes pulse`, the responsive `@media` block) verbatim, plus a `body`/links base that uses the tokens:
```css
body{background:var(--ground);color:var(--text);font-family:var(--sans);margin:0;overflow-x:hidden;}
a{color:inherit;text-decoration:none;}
/* …then the ported dashboard rules from the mockup, unchanged… */
```
Delete the old `.banner`, `#big-app-container`, `#app-container`, `.daeploy_custom-tab*`, `tr:nth-child`, `.logout`, `.severity-*`, `.user-actions` rules (their roles are replaced below).

- [ ] **Step 4: Rewrite the layout helpers in `manager/routers/dashboard_api.py`**

Keep all imports, `app = dash.Dash(...)`, callbacks, and `read_services`/`inspect_service` usage. Replace the component-building functions so the tree matches the mockup's dashboard markup. Concretely:

`build_banner()` → returns the top bar (mockup `.top`): logo `html.Img(src=app.get_asset_url("daeploy_mark.svg"))` + wordmark + `html.Span("manager v: <ver>", className="vchip")`.

`build_user_section()` → returns the `.actions` nav: `html.A("Logs", …, className="act")`, `html.A("API Docs", …, className="act")`, `html.Button("Clear notifications", id="clear-notifications-button", n_clicks=0, className="act")`, `html.A("Log out", …, className="act danger")`. **Keep `id="clear-notifications-button"`** (the callback depends on it).

`generate_table_services()` → for each service, build a `.svc` row Div with: status `.sdot` (`run`/`run live` if main running, `shadow`, or `stop`), name + `.ver` version (mono), `.pin main` ★ for main else `.pin` ○/↗, state label + `.since` (reuse `get_service_state`), and a `.svc-actions` Div with the Logs link (Task 4 view URL) + Docs link.

`generate_table_notifications()` → for each notification build a `.note` row: `.sev info|warn|crit` rule (map severity 0/1/2), `.msg` message, `.meta` with severity tag + timestamp. Reuse the existing severity mapping in `get_severity_colors` (0=Info,1=Warning,2=Critical).

`app.layout` → wrap in the page structure: keep `dcc.Interval(id="interval1", interval=5*1000, n_intervals=0)`; render `build_banner()`, `build_user_section()`, then a `.page` > `.grid` containing a Services `.panel` (header "Services" + `html.Div(id="app-content")`) and a Notifications `.panel`. **Keep `id="app-content"`** (the `update_content` callback targets it). Wrap classNames per the mockup.

Use exact classNames from the mockup so the new CSS applies. Do not change `update_content`, the `@app.callback` decorators, or the clear-notifications logic.

- [ ] **Step 5: Run tests to verify they pass**

Run: `./venv/bin/python -m pytest tests/manager_test/test_ui_redesign.py -k dashboard -v`
Expected: PASS. Also run the existing dashboard guard:
Run: `./venv/bin/python -m pytest tests/manager_test -k "dashboard or endpoint" -v`
Expected: no new failures vs. baseline (pre-existing env failures from [[daeploy-local-test-env-caveats]] excepted).

- [ ] **Step 6: Commit**

```bash
git add manager/assets/dashboard_styles.css manager/routers/dashboard_api.py tests/manager_test/test_ui_redesign.py
git commit -m "Reskin dashboard: token-based styles and control-plane layout"
```

---

## Task 4: Streaming logs view with Follow toggle

**Files:**
- Create: `manager/templates/logs.html`
- Modify: `manager/routers/service_api.py` (add HTML view route)
- Modify: `manager/routers/dashboard_api.py` (`get_service_log_link` → point at the view)
- Test: `tests/manager_test/test_ui_redesign.py`

**Interfaces:**
- Consumes: existing `GET /services/~logs?name&version&tail&follow&since` (`StreamingResponse`, `text/plain`); tokens.css at `/assets/tokens.css`.
- Produces: `GET /services/~logs/view?name=<n>&version=<v>` → HTML page (status 200) that streams the above endpoint. The dashboard service "Logs" link now points here.

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/manager_test/test_ui_redesign.py
def test_logs_view_route_returns_page(test_client_logged_in):
    r = test_client_logged_in.get("/services/~logs/view?name=demo&version=0.1.0")
    assert r.status_code == 200
    body = r.text
    assert 'id="console"' in body
    assert 'id="followBox"' in body          # the Follow checkbox
    assert "/services/~logs?" in body         # streams the real endpoint
    assert "name=demo" in body and "version=0.1.0" in body

def test_logs_view_template_self_contained():
    html = TPL.joinpath("logs.html").read_text()
    low = html.lower()
    for bad in FORBIDDEN:
        assert bad not in low
    assert "/assets/tokens.css" in html
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./venv/bin/python -m pytest tests/manager_test/test_ui_redesign.py -k logs_view -v`
Expected: FAIL (route + template do not exist).

- [ ] **Step 3: Create `manager/templates/logs.html`**

Self-contained shell. Port the mockup's **LOGS** CSS (`.logs-head`, `.live-tag*`, `.follow*`, `.track`, `.console*`, `.logline*`, `.jump*`) and the logs markup (`.panel` with `.logs-head` + `.console-wrap` > `#console` + `#jumpBtn`). Replace the mockup's fake `POOL`/`appendLine` generator with a **real fetch-stream reader** of the `~logs` endpoint, keeping the same Follow/auto-scroll/jump logic verbatim. Read the target from template context:

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Daeploy — {{ name }} logs</title>
  <link rel="icon" href="/assets/favicon.ico">
  <link rel="stylesheet" href="/assets/tokens.css">
  <style>
    body{background:var(--ground);color:var(--text);font-family:var(--sans);margin:0;}
    /* paste the LOGS + top-bar rules from the mockup here (unchanged) */
  </style>
</head>
<body>
  <header class="top"><!-- copy the logs top-bar markup from the mockup; logo via /assets/daeploy_mark.svg --></header>
  <div class="page">
    <section class="panel">
      <div class="logs-head">
        <div class="ctx"><span class="sdot run live"></span>
          <span class="name">{{ name }}</span><span class="ver">v{{ version }}</span></div>
        <div class="logs-tools">
          <span class="live-tag" id="liveTag"><span class="d"></span>Live</span>
          <label class="follow" title="Auto-scroll to newest logs">
            <input type="checkbox" id="followBox" checked>
            <span class="track" aria-hidden="true"></span><span class="flabel">Follow</span>
          </label>
        </div>
      </div>
      <div class="console-wrap">
        <div class="console" id="console" tabindex="0" role="log" aria-live="off"></div>
        <button class="jump" id="jumpBtn" onclick="jumpToLatest()">Jump to latest &darr;</button>
      </div>
    </section>
  </div>
  <script>
    var STREAM_URL = "/services/~logs?name={{ name|urlencode }}&version={{ version|urlencode }}&follow=true&tail=200";
    var consoleEl=document.getElementById('console'),
        followBox=document.getElementById('followBox'),
        jumpBtn=document.getElementById('jumpBtn'),
        liveTag=document.getElementById('liveTag');
    function nearBottom(){return consoleEl.scrollHeight-consoleEl.scrollTop-consoleEl.clientHeight<24;}
    function setLive(on){liveTag.classList.toggle('paused',!on);liveTag.childNodes[1].textContent=on?'Live':'Paused';}
    function classify(line){var u=line.toUpperCase();
      if(u.indexOf('ERROR')>-1||u.indexOf('CRITICAL')>-1)return'err';
      if(u.indexOf('WARN')>-1)return'warn';return'info';}
    function appendLine(text){
      if(!text)return;
      var lvl=classify(text), row=document.createElement('div');
      row.className='logline'+(lvl==='err'?' err':lvl==='warn'?' warn':'');
      row.textContent=text;            // textContent = safe, no XSS from log content
      consoleEl.appendChild(row);
      while(consoleEl.childElementCount>400)consoleEl.removeChild(consoleEl.firstChild);
      if(followBox.checked)consoleEl.scrollTop=consoleEl.scrollHeight; else jumpBtn.classList.add('show');
    }
    function jumpToLatest(){followBox.checked=true;setLive(true);consoleEl.scrollTop=consoleEl.scrollHeight;jumpBtn.classList.remove('show');}
    followBox.addEventListener('change',function(){setLive(followBox.checked);
      if(followBox.checked){consoleEl.scrollTop=consoleEl.scrollHeight;jumpBtn.classList.remove('show');}});
    consoleEl.addEventListener('scroll',function(){
      if(followBox.checked&&!nearBottom()){followBox.checked=false;setLive(false);jumpBtn.classList.add('show');}
      else if(!followBox.checked&&nearBottom()){jumpBtn.classList.remove('show');}});
    // stream the real endpoint
    (async function(){
      try{
        var resp=await fetch(STREAM_URL,{headers:{'Accept':'text/plain'}});
        var reader=resp.body.getReader(), dec=new TextDecoder(), buf='';
        while(true){
          var r=await reader.read(); if(r.done)break;
          buf+=dec.decode(r.value,{stream:true});
          var lines=buf.split('\n'); buf=lines.pop();
          lines.forEach(appendLine);
        }
        if(buf)appendLine(buf);
        setLive(false);
      }catch(e){appendLine('— log stream ended —');setLive(false);}
    })();
  </script>
</body>
</html>
```

- [ ] **Step 4: Add the HTML view route in `manager/routers/service_api.py`**

Add near the top (after the existing imports):
```python
from fastapi import Request
from fastapi.templating import Jinja2Templates
TEMPLATES = Jinja2Templates(directory="manager/templates")
```
Add the route (place it just above the existing `@ROUTER.get("/~logs", ...)`):
```python
@ROUTER.get("/~logs/view", response_class=HTMLResponse)
def service_logs_view(request: Request, name: str, version: str):
    """HTML view that streams a service's logs with a follow/auto-scroll toggle."""
    return TEMPLATES.TemplateResponse(
        "logs.html", {"request": request, "name": name, "version": version}
    )
```
Ensure `HTMLResponse` is imported (`from fastapi.responses import HTMLResponse, StreamingResponse`). This route deliberately does **not** use the `@async_check_service_exists_query_parameters` decorator — it only renders the shell; the `~logs` stream it calls already enforces existence.

- [ ] **Step 5: Point the dashboard "Logs" link at the view**

In `manager/routers/dashboard_api.py`, change `get_service_log_link` to:
```python
def get_service_log_link(service):
    proxy_url = get_external_proxy_url()
    return html.A(
        "Logs",
        href=f"{proxy_url}/services/~logs/view"
             f"?name={service['name']}&version={service['version']}",
        className="lnk",
    )
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `./venv/bin/python -m pytest tests/manager_test/test_ui_redesign.py -k logs_view -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add manager/templates/logs.html manager/routers/service_api.py manager/routers/dashboard_api.py tests/manager_test/test_ui_redesign.py
git commit -m "Add streaming logs view with Follow/auto-scroll toggle"
```

---

## Task 5: Offline + visual verification in the running manager

**Files:** none (verification task).

- [ ] **Step 1: Run the full new test module**

Run: `./venv/bin/python -m pytest tests/manager_test/test_ui_redesign.py -v`
Expected: all PASS.

- [ ] **Step 2: Lint the changed files (CI gates)**

Run: `/home/kaveh/miniconda3/bin/python -m black --check manager/ tests/manager_test/test_ui_redesign.py`
Run: `/home/kaveh/miniconda3/bin/python -m flake8 manager/routers/service_api.py manager/routers/dashboard_api.py`
Expected: black clean; no *new* flake8 findings.

- [ ] **Step 3: Build and run the manager from this branch**

```bash
docker build -t daeploy/manager:latest .
docker rm -f daeploy-manager 2>/dev/null
docker run -d --name daeploy-manager -v /var/run/docker.sock:/var/run/docker.sock \
  -p 80:80 -p 443:443 -e DAEPLOY_AUTH_ENABLED=True -e DAEPLOY_HOST_NAME=localhost \
  -e DAEPLOY_ADMIN_PASSWORD=admin123 daeploy/manager:latest
```

- [ ] **Step 4: Visually verify (browser at http://localhost)**

- Login renders dark with the sonar backdrop, teal "Log in"; logging in with `admin`/`admin123` works.
- Dashboard shows the restyled top bar, service rows with status dots/badges, and the notifications panel.
- Deploy a sample service and open its **Logs** link → the logs view streams; toggling **Follow** off lets you scroll history and shows **Jump to latest**; toggling on resumes auto-scroll.

- [ ] **Step 5: Confirm no external requests (offline guarantee)**

In the browser DevTools Network tab, reload login and the dashboard and confirm **every** request is same-origin (`localhost`) — no fonts/CSS/JS/images from any CDN or `daeploy.com`.

- [ ] **Step 6: Tear down**

```bash
docker rm -f daeploy-manager
```

- [ ] **Step 7: Commit any verification-driven fixes**

```bash
git add -A && git commit -m "UI redesign: verification fixes"   # only if changes were needed
```

---

## Self-Review

**Spec coverage:** self-contained/no-CDN → Task 1 (tokens/fonts), Task 2 (login + `/assets` mount), Task 5 Step 5 (offline check). Login reskin → Task 2. Dashboard reskin (top bar, service rows, notifications) → Task 3. Logs view + Follow/pause/jump → Task 4. Bundled fonts → Task 1. Logo de-hotlink → Task 1 + Tasks 2/4. Color tokens verbatim → Global Constraints + Task 1. Keep stack/behavior → enforced in Tasks 2–4 (form contract, callback ids, helper names). Verification → Task 5.

**Placeholder scan:** the "copy from the mockup" instructions point to a committed, complete reference file with named blocks — not vague TODOs. All integration code (static mount, routes, fonts, streaming JS, link change) is given in full. No "add error handling"/"TBD" left.

**Type/name consistency:** callback-critical ids preserved exactly — `clear-notifications-button`, `app-content`, `interval1`. Helper functions keep names (`generate_table_services`, `generate_table_notifications`, `build_banner`, `build_user_section`, `get_service_state`, `get_service_log_link`). New route `GET /services/~logs/view?name&version` matches the link built in Task 4 Step 5 and the test in Step 1. Stream URL params (`name`, `version`, `follow`, `tail`) match the existing `read_service_logs` signature.
