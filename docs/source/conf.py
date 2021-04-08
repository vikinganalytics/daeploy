# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.

import sys
from pathlib import Path

THIS_DIR = Path(__file__).parent
sys.path.insert(0, str(THIS_DIR.resolve()))


# -- Project information -----------------------------------------------------

project = "Daeploy"
copyright = "2021, Viking Analytics AB"
author = "Viking Analytics AB"


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx_rtd_theme",
    "sphinx.ext.doctest",
    "sphinx_multiversion",
    "sphinx_copybutton",
    "nbsphinx",
    "sphinx_click",
]

# The master toctree document.
master_doc = "index"

# Theme

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []

# -- Options for API Documentation -------------------------------------------

add_module_names = False

# -- Options for HTML output -------------------------------------------------

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]


# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = "sphinx_rtd_theme"
html_theme_options = {
    "logo_only": True,
}
html_logo = "content/img/VA_Symbol_DarkBlue.png"


# -- Options for Sphinx-multiversion -----------------------------------------
# See here: https://holzhaus.github.io/sphinx-multiversion

smv_branch_whitelist = r"^(develop)$"
smv_remote_whitelist = r"^(origin|upstream)$"

templates_path = [
    "_templates",
]

# Running pip-licenses here in a subprocess to get around trouble with sphinx-multiversion
# only handling commited files
import subprocess

subprocess.check_call(
    [
        "pip-licenses",
        "--format=plain-vertical",
        "--with-license-file",
        "--no-license-path",
        "--with-urls",
        "--with-description",
        "--output-file=content/3rd_party_licenses.txt",
    ]
)

# Copybutton options
copybutton_prompt_text = ">>> "
