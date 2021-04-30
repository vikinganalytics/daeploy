import os
import setuptools
from packaging.version import Version

with open("daeploy_package_front.md", "r") as fh:
    long_description = fh.read()

with open("requirements_sdk.txt") as f:
    required = f.read().splitlines()

version_string = os.environ.get("DAEPLOY_RELEASE_VERSION", "")

if version_string:
    # Parse release version from env variable.
    # This will only happen if we are running as part of the pypi workflow
    # Will throw an error if version string is not valid
    version = Version(version_string)
else:
    # Allow for dev environment installation through pip install -e .
    version = Version("0.0.0.dev0")

setuptools.setup(
    name="daeploy",
    version=str(version),
    author="Viking Analytics",
    author_email="info@daeploy.com",
    description="Daeploy SDK and command-line interface",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://daeploy.com",
    packages=["daeploy"] + setuptools.find_namespace_packages(include=("daeploy.*",)),
    include_package_data=True,
    license="GNU General Public License v3 (GPLv3)",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    install_requires=required,
    entry_points={
        "console_scripts": ["daeploy=daeploy.cli.cli:app"],
    },
)
