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
