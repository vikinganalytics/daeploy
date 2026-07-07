# Logs Viewer Enhancements + Responsive Layout — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the logs view a full-screen responsive console with log export and in-log search (over full history), and let the dashboard use more of the screen.

**Architecture:** Pure front-end + two tiny route-context additions; no backend changes. The shared `manager/templates/logs.html` (serves both per-service `/services/~logs/view` and manager `/logs/view`) gains a responsive flex layout, an Export button, and a Search box. Export/search fetch the full log via the existing endpoints with `tail=all`. Dashboard width is a one-line CSS change.

**Tech Stack:** FastAPI + Jinja2 templates, Plotly Dash dashboard, vanilla JS + CSS (no build step, no libraries).

**Spec:** `docs/superpowers/specs/2026-06-29-logs-viewer-enhancements-design.md`

## Global Constraints

- **No backend changes.** Export/search use existing endpoints: service `GET /services/~logs?name=&version=&tail=all`; manager `GET /logs/stream?tail=all`. The live tail keeps `tail=200`/`tail=400` + `follow=true`.
- **Reuse the shared `manager/templates/logs.html`** — both log views get every feature.
- **Self-contained** (no CDNs); use the existing design tokens (`var(--accent)`, `var(--ground)`, etc.).
- **XSS-safe log rendering**: insert log text via `textContent` / `createTextNode` — never `innerHTML` on log content (search highlight uses `<mark>` element nodes around text nodes).
- **Preserve the live tail**: streaming + Follow/auto-scroll/Jump-to-latest stay; new features layer on top.
- **Dashboard width:** `max-width: 1600px` centered (not fully fluid).

## File Structure

- `manager/assets/dashboard_styles.css` — **(modify)** `.page` max-width 1180 → 1600.
- `manager/templates/logs.html` — **(modify)** responsive flex layout CSS; toolbar gains Search + Export; JS for cancellable live stream, search (filter/highlight/count), export (download).
- `manager/routers/service_api.py` — **(modify)** `service_logs_view`: add `full_url` + `export_basename` to context.
- `manager/routers/logging_api.py` — **(modify)** `manager_logs_view`: add `full_url` + `export_basename` to context.
- `tests/manager_test/test_ui_redesign.py` — **(modify)** add guard tests.

Run tests with `./venv/bin/python -m pytest tests/manager_test/test_ui_redesign.py -v` from the repo root. Lint with `/home/kaveh/miniconda3/bin/python -m black --check <files>` and `/home/kaveh/miniconda3/bin/python -m pylint manager daeploy`.

---

## Task 1: Widen the dashboard

**Files:**
- Modify: `manager/assets/dashboard_styles.css:32`
- Test: `tests/manager_test/test_ui_redesign.py`

- [ ] **Step 1: Write the failing test** (append to `tests/manager_test/test_ui_redesign.py`)

```python
def test_dashboard_page_width_widened():
    css = (ASSETS / "dashboard_styles.css").read_text().replace(" ", "")
    assert "max-width:1600px" in css
    assert "max-width:1180px" not in css
```

- [ ] **Step 2: Run it, expect FAIL**

Run: `./venv/bin/python -m pytest tests/manager_test/test_ui_redesign.py::test_dashboard_page_width_widened -v`
Expected: FAIL (current value is `1180px`).

- [ ] **Step 3: Make the change** — in `manager/assets/dashboard_styles.css`, replace line 32:

```css
.page{max-width:1180px;margin:0 auto;padding:1.8rem 1.6rem 4rem}
```
with:
```css
.page{max-width:1600px;margin:0 auto;padding:1.8rem 1.6rem 4rem}
```

- [ ] **Step 4: Run it, expect PASS**

Run: `./venv/bin/python -m pytest tests/manager_test/test_ui_redesign.py::test_dashboard_page_width_widened -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add manager/assets/dashboard_styles.css tests/manager_test/test_ui_redesign.py
git commit -m "Widen dashboard page to 1600px"
```

---

## Task 2: Responsive full-screen logs layout

**Files:**
- Modify: `manager/templates/logs.html` (CSS in the `<style>` block only)
- Test: `tests/manager_test/test_ui_redesign.py`

Make the page a flex column filling the viewport so the console grows/shrinks with the window instead of a fixed `60vh` card capped at `1180px`.

- [ ] **Step 1: Write the failing test** (append)

```python
def test_logs_view_is_full_bleed():
    html = TPL.joinpath("logs.html").read_text().replace(" ", "")
    assert "max-width:1180px" not in html   # logs page no longer capped
    assert "height:60vh" not in html         # console no longer fixed-height
    assert "min-height:100vh" in html        # body fills viewport
    assert "flex:1" in html                  # console/panel flex-fill
```

- [ ] **Step 2: Run it, expect FAIL**

Run: `./venv/bin/python -m pytest tests/manager_test/test_ui_redesign.py::test_logs_view_is_full_bleed -v`
Expected: FAIL.

- [ ] **Step 3: Edit the CSS in `manager/templates/logs.html`.** Make these exact replacements inside `<style>`:

(a) Replace:
```css
    body{background:var(--ground);color:var(--text);font-family:var(--sans);margin:0;}
```
with:
```css
    html,body{height:100%;}
    body{background:var(--ground);color:var(--text);font-family:var(--sans);margin:0;
      display:flex;flex-direction:column;min-height:100vh;}
```

(b) Replace:
```css
    .page{max-width:1180px;margin:0 auto;padding:1.8rem 1.6rem 4rem}

    .panel{
      background:var(--surface);border:1px solid var(--line-soft);border-radius:16px;
      overflow:hidden;
    }
```
with:
```css
    .page{flex:1;min-height:0;display:flex;padding:1.2rem 1.6rem 1.6rem;}

    .panel{
      background:var(--surface);border:1px solid var(--line-soft);border-radius:16px;
      overflow:hidden;flex:1;display:flex;flex-direction:column;min-height:0;width:100%;
    }
```

(c) Replace:
```css
    .console-wrap{position:relative}
    .console{
      height:60vh;min-height:320px;overflow-y:auto;overflow-x:hidden;
```
with:
```css
    .console-wrap{position:relative;flex:1;min-height:0;display:flex;}
    .console{
      flex:1;min-height:0;overflow-y:auto;overflow-x:hidden;
```

- [ ] **Step 4: Run it, expect PASS**

Run: `./venv/bin/python -m pytest tests/manager_test/test_ui_redesign.py::test_logs_view_is_full_bleed -v`
Expected: PASS. Also confirm the page still renders:
Run: `./venv/bin/python -m pytest tests/manager_test/test_ui_redesign.py -k "logs_view or manager_logs_view" -v`
Expected: PASS (existing render tests still green).

- [ ] **Step 5: Commit**

```bash
git add manager/templates/logs.html tests/manager_test/test_ui_redesign.py
git commit -m "Make the logs view a full-screen responsive console"
```

---

## Task 3: Pass `full_url` + `export_basename` to both log views (and expose them in the template)

**Files:**
- Modify: `manager/routers/service_api.py` (`service_logs_view`)
- Modify: `manager/routers/logging_api.py` (`manager_logs_view`)
- Modify: `manager/templates/logs.html` (declare the two JS vars so the values render; Task 4 uses them)
- Test: `tests/manager_test/test_ui_redesign.py`

**Interfaces:**
- Produces: two new template context values + JS globals consumed by Task 4 — `full_url` → `var FULL_URL` (the log endpoint with `tail=all`, for export/search) and `export_basename` → `var EXPORT_BASENAME` (download filename stem).

- [ ] **Step 1: Write the failing tests** (append)

```python
def test_service_logs_view_full_url_and_basename(test_client_logged_in):
    r = test_client_logged_in.get("/services/~logs/view?name=demo&version=0.1.0")
    assert r.status_code == 200
    assert "/services/~logs?name=demo&version=0.1.0&tail=all" in r.text
    assert 'EXPORT_BASENAME = "demo_v0.1.0"' in r.text


def test_manager_logs_view_full_url_and_basename(test_client):
    r = test_client.get("/logs/view")
    assert r.status_code == 200
    assert "/logs/stream?tail=all" in r.text
    assert 'EXPORT_BASENAME = "manager"' in r.text
```

- [ ] **Step 2: Run them, expect FAIL**

Run: `./venv/bin/python -m pytest tests/manager_test/test_ui_redesign.py -k "full_url_and_basename" -v`
Expected: FAIL (neither the context values nor the `FULL_URL`/`EXPORT_BASENAME` JS vars exist yet).

- [ ] **Step 3: Edit `manager/routers/service_api.py`** — replace the body of `service_logs_view`:

```python
@ROUTER.get("/~logs/view", response_class=HTMLResponse)
def service_logs_view(request: Request, name: str, version: str):
    """HTML view that streams a service's logs with a follow/auto-scroll toggle."""
    base = f"/services/~logs?name={quote(name)}&version={quote(version)}"
    return TEMPLATES.TemplateResponse(
        request=request,
        name="logs.html",
        context={
            "title": name,
            "subtitle": f"v{version}",
            "stream_url": f"{base}&follow=true&tail=200",
            "full_url": f"{base}&tail=all",
            "export_basename": f"{name}_v{version}",
            "manager_version": get_manager_version(),
        },
    )
```

- [ ] **Step 4: Edit `manager/routers/logging_api.py`** — replace the body of `manager_logs_view`:

```python
@ROUTER.get("/view", response_class=HTMLResponse)
def manager_logs_view(request: Request):
    """HTML view that streams the manager logs with a follow/auto-scroll toggle.

    \f
    # noqa: DAR101,DAR201
    """
    return TEMPLATES.TemplateResponse(
        request=request,
        name="logs.html",
        context={
            "title": "manager",
            "subtitle": f"v: {get_manager_version()}",
            "stream_url": "/logs/stream?follow=true&tail=400",
            "full_url": "/logs/stream?tail=all",
            "export_basename": "manager",
            "manager_version": get_manager_version(),
        },
    )
```

- [ ] **Step 5: Expose the values in `manager/templates/logs.html`.** In the `<script>` block, replace this single line:

```html
    var STREAM_URL = "{{ stream_url|safe }}";
```
with:
```html
    var STREAM_URL = "{{ stream_url|safe }}";
    var FULL_URL   = "{{ full_url|safe }}";
    var EXPORT_BASENAME = "{{ export_basename }}";
```
(These declarations are unused until Task 4 wires up export/search — harmless for now, and they make the rendered values testable.)

- [ ] **Step 6: Run the tests, expect PASS**

Run: `./venv/bin/python -m pytest tests/manager_test/test_ui_redesign.py -k "full_url_and_basename" -v`
Expected: PASS. Also confirm existing render tests still pass:
Run: `./venv/bin/python -m pytest tests/manager_test/test_ui_redesign.py -k "logs_view or manager_logs_view" -v`
Expected: PASS.

- [ ] **Step 7: Black + commit**

```bash
/home/kaveh/miniconda3/bin/python -m black manager/routers/service_api.py manager/routers/logging_api.py
git add manager/routers/service_api.py manager/routers/logging_api.py manager/templates/logs.html tests/manager_test/test_ui_redesign.py
git commit -m "Pass full_url + export_basename to the log views"
```

---

## Task 4: Logs toolbar — export + search

**Files:**
- Modify: `manager/templates/logs.html` (toolbar markup, CSS for search/mark, and the `<script>`)
- Test: `tests/manager_test/test_ui_redesign.py`

**Interfaces:**
- Consumes: `stream_url`, `full_url`, `export_basename` (Task 3).

- [ ] **Step 1: Write the failing tests** (append)

```python
def test_logs_toolbar_has_search_and_export():
    html = TPL.joinpath("logs.html").read_text()
    assert 'id="searchBox"' in html
    assert 'id="matchCount"' in html
    assert 'id="exportBtn"' in html
    assert "function runSearch" in html
    assert "function startStream" in html        # cancellable live tail
    assert "EXPORT_BASENAME" in html and "FULL_URL" in html
    assert "a.download" in html                  # triggers a file download
    assert "createTextNode" in html              # XSS-safe highlight
```

- [ ] **Step 2: Run it, expect FAIL**

Run: `./venv/bin/python -m pytest tests/manager_test/test_ui_redesign.py::test_logs_toolbar_has_search_and_export -v`
Expected: FAIL.

- [ ] **Step 3: Add the search/export CSS.** In `manager/templates/logs.html`, immediately after the `.logs-tools{...}` rule, add:

```css
    .searchbox{
      background:var(--ground);border:1px solid var(--line);border-radius:8px;
      color:var(--text);font-family:var(--mono);font-size:12px;padding:.35rem .6rem;width:210px;
    }
    .searchbox::placeholder{color:var(--faint)}
    .searchbox:focus{outline:none;border-color:var(--accent-dim);box-shadow:0 0 0 3px rgba(94,230,208,.14)}
    .match-count{font-family:var(--mono);font-size:10.5px;letter-spacing:.08em;color:var(--faint);min-width:64px}
    .console mark{background:rgba(94,230,208,.28);color:var(--text);border-radius:2px;padding:0 1px}
```

- [ ] **Step 4: Replace the toolbar markup.** Replace this block:

```html
        <div class="logs-tools">
          <span class="live-tag" id="liveTag"><span class="d"></span><span id="liveLabel">Live</span></span>
          <label class="follow" title="Auto-scroll to newest logs">
            <input type="checkbox" id="followBox" checked>
            <span class="track" aria-hidden="true"></span><span class="flabel">Follow</span>
          </label>
        </div>
```
with:
```html
        <div class="logs-tools">
          <input type="search" id="searchBox" class="searchbox" placeholder="Search logs…" autocomplete="off" aria-label="Search logs">
          <span class="match-count" id="matchCount"></span>
          <button class="act" id="exportBtn" type="button">Export</button>
          <span class="live-tag" id="liveTag"><span class="d"></span><span id="liveLabel">Live</span></span>
          <label class="follow" title="Auto-scroll to newest logs">
            <input type="checkbox" id="followBox" checked>
            <span class="track" aria-hidden="true"></span><span class="flabel">Follow</span>
          </label>
        </div>
```

- [ ] **Step 5: Replace the entire `<script> … </script>` block** (currently lines ~160–201) with:

```html
  <script>
    var STREAM_URL = "{{ stream_url|safe }}";
    var FULL_URL   = "{{ full_url|safe }}";
    var EXPORT_BASENAME = "{{ export_basename }}";

    var consoleEl=document.getElementById('console'),
        followBox=document.getElementById('followBox'),
        jumpBtn=document.getElementById('jumpBtn'),
        liveTag=document.getElementById('liveTag'),
        searchBox=document.getElementById('searchBox'),
        matchCount=document.getElementById('matchCount'),
        exportBtn=document.getElementById('exportBtn');

    var searchActive=false, streamCtrl=null, searchTimer=null;

    function nearBottom(){return consoleEl.scrollHeight-consoleEl.scrollTop-consoleEl.clientHeight<24;}
    function setLive(on){liveTag.classList.toggle('paused',!on);document.getElementById('liveLabel').textContent=on?'Live':'Paused';}
    function classify(line){var u=line.toUpperCase();
      if(u.indexOf('ERROR')>-1||u.indexOf('CRITICAL')>-1)return'err';
      if(u.indexOf('WARN')>-1)return'warn';return'info';}
    function newRow(text){
      var lvl=classify(text), row=document.createElement('div');
      row.className='logline'+(lvl==='err'?' err':lvl==='warn'?' warn':'');
      return row;
    }
    function appendLine(text){
      if(!text)return;
      var row=newRow(text);
      row.textContent=text;            // textContent = safe, no XSS from log content
      consoleEl.appendChild(row);
      while(consoleEl.childElementCount>400)consoleEl.removeChild(consoleEl.firstChild);
      if(followBox.checked)consoleEl.scrollTop=consoleEl.scrollHeight; else jumpBtn.classList.add('show');
    }
    function jumpToLatest(){followBox.checked=true;setLive(true);consoleEl.scrollTop=consoleEl.scrollHeight;jumpBtn.classList.remove('show');}

    followBox.addEventListener('change',function(){setLive(followBox.checked);
      if(followBox.checked){consoleEl.scrollTop=consoleEl.scrollHeight;jumpBtn.classList.remove('show');}});
    consoleEl.addEventListener('scroll',function(){
      if(searchActive)return;
      if(followBox.checked&&!nearBottom()){followBox.checked=false;setLive(false);jumpBtn.classList.add('show');}
      else if(!followBox.checked&&nearBottom()){jumpBtn.classList.remove('show');}});

    // ---- live tail (cancellable) ----
    async function startStream(){
      if(streamCtrl)streamCtrl.abort();
      streamCtrl=new AbortController();
      consoleEl.textContent='';
      followBox.checked=true; setLive(true); jumpBtn.classList.remove('show');
      try{
        var resp=await fetch(STREAM_URL,{headers:{'Accept':'text/plain'},signal:streamCtrl.signal});
        var reader=resp.body.getReader(), dec=new TextDecoder(), buf='';
        while(true){
          var r=await reader.read(); if(r.done)break;
          buf+=dec.decode(r.value,{stream:true});
          var lines=buf.split('\n'); buf=lines.pop();
          lines.forEach(appendLine);
        }
        if(buf)appendLine(buf);
        setLive(false);
      }catch(e){ if(e.name!=='AbortError'){appendLine('— log stream ended —');setLive(false);} }
    }

    // ---- search: filter to matching lines over full history ----
    function appendMatch(text,term){
      var row=newRow(text), lc=text.toLowerCase(), q=term.toLowerCase(), i=0, idx;
      while((idx=lc.indexOf(q,i))>-1){
        if(idx>i)row.appendChild(document.createTextNode(text.slice(i,idx)));
        var m=document.createElement('mark'); m.textContent=text.slice(idx,idx+term.length); row.appendChild(m);
        i=idx+term.length;
      }
      if(i<text.length)row.appendChild(document.createTextNode(text.slice(i)));
      consoleEl.appendChild(row);
    }
    async function runSearch(term){
      searchActive=true;
      if(streamCtrl)streamCtrl.abort();
      setLive(false); jumpBtn.classList.remove('show'); matchCount.textContent='…';
      try{
        var resp=await fetch(FULL_URL,{headers:{'Accept':'text/plain'}});
        var text=await resp.text(), q=term.toLowerCase(), matches=0;
        consoleEl.textContent='';
        text.split('\n').forEach(function(line){
          if(line && line.toLowerCase().indexOf(q)>-1){matches++; appendMatch(line,term);}
        });
        matchCount.textContent=matches+' match'+(matches===1?'':'es');
      }catch(e){ matchCount.textContent='search failed'; }
    }
    function clearSearch(){ searchActive=false; matchCount.textContent=''; startStream(); }

    searchBox.addEventListener('input',function(){
      clearTimeout(searchTimer);
      var term=searchBox.value;
      searchTimer=setTimeout(function(){ if(term.trim()==='')clearSearch(); else runSearch(term); },250);
    });

    // ---- export: download full history as a .log file ----
    exportBtn.addEventListener('click',async function(){
      var old=exportBtn.textContent; exportBtn.textContent='…'; exportBtn.disabled=true;
      try{
        var resp=await fetch(FULL_URL,{headers:{'Accept':'text/plain'}});
        var text=await resp.text();
        var d=new Date(), p=function(n){return String(n).padStart(2,'0');};
        var ts=''+d.getUTCFullYear()+p(d.getUTCMonth()+1)+p(d.getUTCDate())+'-'+p(d.getUTCHours())+p(d.getUTCMinutes())+p(d.getUTCSeconds());
        var a=document.createElement('a');
        a.href=URL.createObjectURL(new Blob([text],{type:'text/plain'}));
        a.download=EXPORT_BASENAME+'_'+ts+'.log';
        document.body.appendChild(a); a.click(); a.remove();
        setTimeout(function(){URL.revokeObjectURL(a.href);},1000);
      }catch(e){ alert('Export failed: '+e); }
      finally{ exportBtn.textContent=old; exportBtn.disabled=false; }
    });

    startStream();
  </script>
```

- [ ] **Step 6: Run the full UI test module, expect PASS** (this also greens the Task 3 tests)

Run: `./venv/bin/python -m pytest tests/manager_test/test_ui_redesign.py -v`
Expected: all PASS (including `test_logs_toolbar_has_search_and_export`, `test_*_passes_full_url_and_basename`, and the pre-existing logs render tests).

- [ ] **Step 7: Commit**

```bash
git add manager/templates/logs.html tests/manager_test/test_ui_redesign.py
git commit -m "Add log export + search to the logs view toolbar"
```

---

## Task 5: Verify live in the running manager

**Files:** none (verification).

- [ ] **Step 1: Lint gates**

Run: `/home/kaveh/miniconda3/bin/python -m black --check manager/ tests/manager_test/test_ui_redesign.py`
Run: `/home/kaveh/miniconda3/bin/python -m pylint manager daeploy`
Expected: black clean; pylint 10.00/10 (no new findings).

- [ ] **Step 2: Build + run the manager from this branch**

```bash
docker build -t daeploy/manager:logsui .
docker rm -f daeploy-manager 2>/dev/null
docker run -d --name daeploy-manager -v /var/run/docker.sock:/var/run/docker.sock \
  -v daeploy_data:/data -p 80:80 -p 443:443 -e DAEPLOY_AUTH_ENABLED=True \
  -e DAEPLOY_HOST_NAME=localhost -e DAEPLOY_ADMIN_PASSWORD=admin123 daeploy/manager:logsui
```

- [ ] **Step 3: Visually verify** (browser at http://localhost, login admin/admin123)

- Dashboard uses the wider layout (≈1600px).
- Open a service's **Logs** (or `/logs/view`): the console **fills the window**; resize the browser and confirm it grows/shrinks.
- **Export** downloads a `‹name›_v‹version›_‹timestamp›.log` (manager → `manager_‹timestamp›.log`) containing the full log.
- **Search**: type a term → only matching lines show, term highlighted, count shown ("N matches"), Live flips to Paused. Clear the box → live tail resumes (Live, auto-scroll).

- [ ] **Step 4: Tear down**

```bash
docker rm -f daeploy-manager
```

- [ ] **Step 5: Commit any verification fixes** (only if needed)

```bash
git add -A && git commit -m "Logs viewer: verification fixes"
```

---

## Self-Review

**Spec coverage:** A responsive logs view → Task 2. B responsive dashboard → Task 1. C export (full history, `.log`, per-view) → Task 3 (`full_url`/`export_basename`) + Task 4 (button + JS). D search (full history, filter-to-matches, highlight, count, pause Follow, clear-resumes) → Task 3 + Task 4. No-backend-changes → only routes (context) + template + CSS touched. Reuse shared `logs.html` → yes. XSS-safe → `textContent`/`createTextNode` asserted in Task 4. Toolbar layout → Task 4 markup. Verify live → Task 5.

**Placeholder scan:** every code step shows complete code; commands have expected output; no TBD/TODO. Task 3's tests intentionally green after Task 4 — called out explicitly, not a hidden gap.

**Type/name consistency:** context keys `stream_url`/`full_url`/`export_basename`/`title`/`subtitle`/`manager_version` match between the routes (Task 3) and the template `{{ }}` + JS vars `STREAM_URL`/`FULL_URL`/`EXPORT_BASENAME` (Task 4). Element ids `searchBox`/`matchCount`/`exportBtn`/`console`/`followBox`/`liveTag`/`liveLabel`/`jumpBtn` are consistent between the markup (Step 4) and the script (Step 5). `startStream`/`runSearch`/`clearSearch`/`appendMatch`/`appendLine`/`jumpToLatest` defined and referenced consistently; `jumpToLatest` stays a global (used by inline `onclick`).
