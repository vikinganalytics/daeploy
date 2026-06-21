# tests/manager_test/test_ui_redesign.py
from pathlib import Path

ASSETS = Path("manager/assets")


def test_tokens_css_defines_palette():
    css = (ASSETS / "tokens.css").read_text()
    for var, val in [
        ("--ground", "#0E1320"),
        ("--accent", "#5EE6D0"),
        ("--text", "#E7ECF5"),
        ("--crit", "#F2585B"),
    ]:
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


from manager.templates import __file__ as _t  # noqa

TPL = Path("manager/templates")

FORBIDDEN = [
    "maxcdn",
    "bootstrapcdn",
    "googleapis",
    "cloudflare",
    "jquery",
    "daeploy.com/wp-content",
]


def test_login_html_is_self_contained():
    html = TPL.joinpath("login.html").read_text()
    low = html.lower()
    for bad in FORBIDDEN:
        assert bad not in low, f"login.html still references {bad}"
    # keep the working form contract
    assert 'action="{{ ACTION }}"' in html
    assert 'name="username"' in html and 'name="password"' in html
    assert "/assets/tokens.css" in html


def test_assets_mounted(test_client):
    r = test_client.get("/assets/tokens.css")
    assert r.status_code == 200
    assert "--accent" in r.text


def test_dashboard_css_uses_tokens():
    css = (ASSETS / "dashboard_styles.css").read_text()
    assert "var(--ground)" in css and "var(--accent)" in css
    assert "http://" not in css and "https://" not in css


def test_dashboard_layout_builds():
    # importing must not raise and layout must be present
    from manager.routers import dashboard_api

    assert dashboard_api.app.layout is not None
    # helper functions still exist with the same names
    for fn in [
        "generate_table_services",
        "generate_table_notifications",
        "build_banner",
        "build_user_section",
        "update_content",
    ]:
        assert hasattr(dashboard_api, fn)


def test_notifications_panel_is_live():
    from manager.routers import dashboard_api

    assert "notifications-content.children" in dashboard_api.app.callback_map
