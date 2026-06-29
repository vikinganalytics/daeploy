# Dashboard Main-Page Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Polish the manager dashboard so Services is the clear hero, Notifications is a slim self-explanatory rail, LOGS/DOCS read as buttons, and short content no longer leaves a top-heavy void.

**Architecture:** Frontend-only. Two files: `manager/routers/dashboard_api.py` (Dash layout markup — one added subtitle element) and `manager/assets/dashboard_styles.css` (all styling). Guard tests are string-assert checks in `tests/manager_test/test_ui_redesign.py`, matching the existing pattern (read the CSS file / `str(app.layout)` and assert substrings).

**Tech Stack:** Dash (Plotly) layout in Python, plain CSS with design tokens from `tokens.css`, pytest guard tests via `test_client` fixtures in `tests/conftest.py`.

## Global Constraints

- No backend, API, endpoint, or data-model changes. CSS + one markup element only.
- No external resources: CSS must contain no `http://` or `https://` (enforced by `test_dashboard_css_uses_tokens`).
- Reuse existing design tokens from `tokens.css` (`var(--muted)`, `var(--line)`, `var(--accent)`, etc.) — introduce no new colors.
- The logs view page (`logs.html`), login, and `max-width:1600px` on `.page` stay as-is. Do not reintroduce `max-width:1180px` (guarded by `test_dashboard_page_width_widened`).
- Run before pushing: `/home/kaveh/miniconda3/bin/python -m black --check`, `... -m flake8`, `... -m pylint manager`, and `./venv/bin/python -m pytest tests/manager_test/test_ui_redesign.py`.
- Mobile rule `@media (max-width:760px){ .grid{grid-template-columns:1fr} ... }` must keep collapsing the grid to one column.

---

### Task 1: Widen Services / slim sidebar + vertical fill

**Files:**
- Modify: `manager/assets/dashboard_styles.css` (the `.page` rule at line 32 and the `.grid` rule at line 33)
- Test: `tests/manager_test/test_ui_redesign.py`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: the `.grid` / `.page` CSS shape that Task 2 and Task 3 visually sit inside; no code symbols.

Current CSS (lines 31-33):

```css
/* ---------- page / grid ---------- */
.page{max-width:1600px;margin:0 auto;padding:1.8rem 1.6rem 4rem}
.grid{display:grid;grid-template-columns:1.85fr 1fr;gap:1.4rem;align-items:start}
```

- [ ] **Step 1: Write the failing test**

Add to `tests/manager_test/test_ui_redesign.py`:

```python
def test_dashboard_grid_widens_services_and_fills_viewport():
    css = (ASSETS / "dashboard_styles.css").read_text().replace(" ", "")
    # Services hero is wider than the slim Notifications rail
    assert "grid-template-columns:2.6fr0.9fr" in css
    assert "grid-template-columns:1.85fr1fr" not in css
    # Page fills the viewport height (minus the banner) and centers when short
    assert "min-height:calc(100vh-4rem)" in css
    assert "margin-block:auto" in css
    assert "box-sizing:border-box" in css
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/bin/python -m pytest "tests/manager_test/test_ui_redesign.py::test_dashboard_grid_widens_services_and_fills_viewport" -v`
Expected: FAIL (`assert "grid-template-columns:2.6fr0.9fr" in css` is False — file still has `1.85fr 1fr`).

- [ ] **Step 3: Write minimal implementation**

Replace lines 31-33 of `manager/assets/dashboard_styles.css` with:

```css
/* ---------- page / grid ---------- */
.page{
  max-width:1600px;margin:0 auto;padding:1.8rem 1.6rem 4rem;
  box-sizing:border-box;min-height:calc(100vh - 4rem);
  display:flex;flex-direction:column;
}
.grid{
  display:grid;grid-template-columns:2.6fr 0.9fr;gap:1.4rem;align-items:start;
  margin-block:auto;width:100%;
}
```

Notes for the implementer:
- `vh` is viewport-relative, so `min-height:calc(100vh - 4rem)` makes `.page` nearly fill the screen without touching `body` or Dash's wrapper divs. The `4rem` budgets for the top banner.
- `box-sizing:border-box` is required because there is no global reset and `.page` has padding; without it the padding would add to the `100vh` height and force a scrollbar.
- `margin-block:auto` on `.grid` centers it vertically inside the tall `.page` when there is spare room; when the grid is taller than the page the auto margins collapse to 0 and the page grows/scrolls normally.
- `width:100%` keeps the grid full-width inside the flex column (a flex item would otherwise shrink to content width).

- [ ] **Step 4: Run test to verify it passes**

Run: `./venv/bin/python -m pytest "tests/manager_test/test_ui_redesign.py::test_dashboard_grid_widens_services_and_fills_viewport" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add manager/assets/dashboard_styles.css tests/manager_test/test_ui_redesign.py
git commit -m "Dashboard: widen Services, slim sidebar, fill viewport height"
```

---

### Task 2: Explain the Notifications panel

**Files:**
- Modify: `manager/routers/dashboard_api.py` (the Notifications panel head in `app.layout`, around lines 334-340)
- Modify: `manager/assets/dashboard_styles.css` (add `.panel-sub` near the `.panel-head` rules, ~line 44)
- Test: `tests/manager_test/test_ui_redesign.py`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: a `<p class="panel-sub">` element with the literal subtitle text below; relied on only by its own test.

Current markup (lines 334-345 of `dashboard_api.py`):

```python
        # Notifications panel
        html.Section(
            className="panel",
            children=[
                html.Div(
                    className="panel-head",
                    children=[html.H2("Notifications")],
                ),
                html.Div(
                    id="notifications-content",
                    children=[generate_table_notifications()],
                ),
            ],
        ),
```

- [ ] **Step 1: Write the failing test**

Add to `tests/manager_test/test_ui_redesign.py`:

```python
def test_notifications_panel_has_explanation():
    from manager.routers import dashboard_api

    layout = str(dashboard_api.app.layout)
    assert "Alerts services raise" in layout  # one-line description of the panel
    css = (ASSETS / "dashboard_styles.css").read_text()
    assert ".panel-sub" in css
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/bin/python -m pytest "tests/manager_test/test_ui_redesign.py::test_notifications_panel_has_explanation" -v`
Expected: FAIL (`assert "Alerts services raise" in layout` is False — no subtitle yet).

- [ ] **Step 3: Write minimal implementation**

In `manager/routers/dashboard_api.py`, change the Notifications `panel-head` children to include a subtitle (replace the single-child `panel-head` Div shown above):

```python
                html.Div(
                    className="panel-head",
                    children=[
                        html.Div(
                            [
                                html.H2("Notifications"),
                                html.P(
                                    "Alerts services raise via the SDK"
                                    " notify() — info, warnings, critical.",
                                    className="panel-sub",
                                ),
                            ]
                        )
                    ],
                ),
```

Then add the `.panel-sub` style to `manager/assets/dashboard_styles.css` immediately after the `.panel-head h2` rule (line 44):

```css
.panel-sub{margin:.25rem 0 0;font-size:11px;line-height:1.4;color:var(--muted)}
```

Note: keep the `()` in `notify()` but do not include any URL — the CSS/markup must stay free of `http(s)://` (Task constraint). The text uses a plain hyphen.

- [ ] **Step 4: Run test to verify it passes**

Run: `./venv/bin/python -m pytest "tests/manager_test/test_ui_redesign.py::test_notifications_panel_has_explanation" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add manager/routers/dashboard_api.py manager/assets/dashboard_styles.css tests/manager_test/test_ui_redesign.py
git commit -m "Dashboard: explain the Notifications panel with a subtitle"
```

---

### Task 3: Make LOGS / DOCS read as buttons

**Files:**
- Modify: `manager/assets/dashboard_styles.css` (the `.lnk` rules at lines 90-95)
- Test: `tests/manager_test/test_ui_redesign.py`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: restyled `.lnk` (markup unchanged — `get_service_log_link` / `get_service_docs_link` still emit `<a class="lnk">`).

Current CSS (lines 88-95):

```css
/* ---------- service actions ---------- */
.svc-actions{grid-area:actions;display:flex;gap:.4rem}
.lnk{
  font-family:var(--mono);font-size:10.5px;letter-spacing:.08em;text-transform:uppercase;
  color:var(--muted);text-decoration:none;border-bottom:1px solid transparent;padding:.1rem 0;
  transition:color .15s,border-color .15s;
}
.lnk:hover{color:var(--accent);border-color:var(--accent)}
```

- [ ] **Step 1: Write the failing test**

Add to `tests/manager_test/test_ui_redesign.py`:

```python
def test_service_links_look_like_buttons():
    css = (ASSETS / "dashboard_styles.css").read_text().replace(" ", "")
    # .lnk is now a bordered pill, not underline-on-hover text
    assert ".lnk{" in css
    lnk_block = css.split(".lnk{", 1)[1].split("}", 1)[0]
    assert "border:1px solid" in lnk_block
    assert "border-radius:" in lnk_block
    # keyboard focus ring, matching .act
    assert ".lnk:focus-visible{" in css
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/bin/python -m pytest "tests/manager_test/test_ui_redesign.py::test_service_links_look_like_buttons" -v`
Expected: FAIL (the current `.lnk` block has `border-bottom`, not `border:1px solid`, and no `:focus-visible`).

- [ ] **Step 3: Write minimal implementation**

Replace lines 90-95 of `manager/assets/dashboard_styles.css` with:

```css
.lnk{
  font-family:var(--mono);font-size:10px;letter-spacing:.1em;text-transform:uppercase;
  color:var(--muted);text-decoration:none;
  border:1px solid var(--line);border-radius:7px;padding:.34rem .6rem;
  transition:color .15s,border-color .15s,background .15s;
}
.lnk:hover{color:var(--accent);border-color:var(--accent-dim);background:rgba(94,230,208,.06)}
.lnk:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
```

Note: this mirrors the existing `.act` button look (border + rounded + accent hover + focus ring) so the two LOGS/DOCS controls clearly read as clickable. `.svc-actions` already has `gap:.4rem`, which spaces the two pills correctly — no change needed there.

- [ ] **Step 4: Run test to verify it passes**

Run: `./venv/bin/python -m pytest "tests/manager_test/test_ui_redesign.py::test_service_links_look_like_buttons" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add manager/assets/dashboard_styles.css tests/manager_test/test_ui_redesign.py
git commit -m "Dashboard: style LOGS/DOCS as buttons with focus ring"
```

---

### Task 4: Full guard-suite + lint pass

**Files:**
- No new code. Verification only.

- [ ] **Step 1: Run the full UI guard suite**

Run: `./venv/bin/python -m pytest tests/manager_test/test_ui_redesign.py -v`
Expected: PASS (all existing tests + the three new ones). Confirms no earlier guard (e.g. `test_dashboard_layout_builds`, `test_dashboard_page_width_widened`, `test_notifications_panel_is_live`) regressed.

- [ ] **Step 2: Lint the changed files**

Run:
```bash
/home/kaveh/miniconda3/bin/python -m black --check manager/routers/dashboard_api.py tests/manager_test/test_ui_redesign.py
/home/kaveh/miniconda3/bin/python -m flake8 manager/routers/dashboard_api.py tests/manager_test/test_ui_redesign.py
/home/kaveh/miniconda3/bin/python -m pylint manager
```
Expected: black "would be left unchanged", flake8 no output, pylint 10.00/10. (CSS is not linted.) If black reports a reformat on `dashboard_api.py`, run it without `--check` to apply, then re-commit.

- [ ] **Step 3: Commit any formatting fixup (only if Step 2 changed files)**

```bash
git add -A
git commit -m "Dashboard polish: black formatting"
```

---

## Self-Review

**Spec coverage:**
- Widen Services / slim sidebar → Task 1 (`2.6fr 0.9fr`). ✓
- Explain Notifications → Task 2 (`panel-sub` subtitle). ✓
- LOGS/DOCS obvious → Task 3 (bordered buttons + focus ring). ✓
- Fix top-heavy emptiness → Task 1 (`min-height:calc(100vh - 4rem)` + `margin-block:auto`). ✓
- Testing section (guard-test asserts) → Tasks 1-3 each add one test; Task 4 runs the full suite + lint. ✓
- Non-goals (no stats bar, no badges, no logs-view change, no backend) → respected; no task touches them. ✓

**Placeholder scan:** No TBD/TODO; every code step shows full CSS/markup and exact commands. ✓

**Type/string consistency:** The subtitle literal "Alerts services raise via the SDK notify() — info, warnings, critical." in Task 2's implementation matches the test's substring "Alerts services raise". The class names `.panel-sub`, `.lnk`, `.grid`, `.page` are used identically across implementation and tests. The `2.6fr 0.9fr` value (space-stripped to `2.6fr0.9fr` in tests) is consistent. ✓
