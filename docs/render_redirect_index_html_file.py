from pathlib import Path
from packaging import version
from jinja2 import Template

HTML_INDEX_TEMPLATE = """\
<!DOCTYPE html>
<html>
  <head>
    <title>Redirecting to master branch</title>
    <meta charset="utf-8">
    <meta http-equiv="refresh" content="0; url=./{{ version }}/index.html">
    <link rel="canonical" href="https://vikinganalytics.github.io/daeploy-docs/{{ version }}/index.html">
  </head>
</html>
"""

## Get correct version
THIS_DIR = Path(__file__).parent
BUILD_DIR = (THIS_DIR / "build" / "html").resolve()


def _as_release(name):
    """Parse a build-dir name as a release version.

    Returns None for non-version dirs (e.g. ``develop``) and for
    pre-/dev-releases, so they are excluded from the redirect target.
    Newer ``packaging`` raises ``InvalidVersion`` instead of returning a
    legacy version, so the parse must be guarded.
    """
    try:
        parsed = version.parse(name)
    except version.InvalidVersion:
        return None
    if parsed.is_prerelease or parsed.is_devrelease:
        return None
    return parsed


dir_names = [p.name for p in BUILD_DIR.iterdir() if p.is_dir()]

versions = sorted(filter(None, (_as_release(name) for name in dir_names)), reverse=True)

the_version = str(versions[0])


# Render a nice index.html with the version
template = Template(HTML_INDEX_TEMPLATE)
rendered = template.render(version=the_version)

# Write to file
output_file = BUILD_DIR / "index.html"
output_file.write_text(rendered)
