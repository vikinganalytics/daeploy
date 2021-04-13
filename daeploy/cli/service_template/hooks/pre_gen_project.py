import re
import sys

# Check project name
project_regex = r"^[_a-zA-Z][_a-zA-Z0-9]+$"

project_name = "{{ cookiecutter.project_name }}"

if not re.match(project_regex, project_name):
    print(
        f'"{project_name}" is not a valid Daeploy service name. '
        "Should contain only letters, numers and underscores."
    )

    # exits with status 1 to indicate failure
    sys.exit(1)
