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

versions = filter(lambda x: x.is_dir(), BUILD_DIR.iterdir())

versions = map(lambda x: version.parse(x.name), versions)

versions = filter(lambda v: not (v.is_prerelease or v.is_devrelease), versions)

versions = sorted(versions, reverse=True)

the_version = str(versions[0])


# Render a nice index.html with the version
template = Template(HTML_INDEX_TEMPLATE)
rendered = template.render(version=the_version)

# Write to file
output_file = BUILD_DIR / "index.html"
output_file.write_text(rendered)
