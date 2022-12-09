# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, os.path.abspath('.'))


# -- Project information -----------------------------------------------------

import os
import sys

sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.abspath(f"..{os.sep}.."))

import core
project = core.__title__
copyright = core.__copyright__
author = core.__author__
version = core.__version__


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.todo",
    "sphinx.ext.autodoc",
    "sphinx.ext.extlinks",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon"
]

# Extension configuration.
autodoc_member_order = "bysource"

todo_include_todos = True
todo_link_only = True
todo_emit_warnings = False

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "wavelink": ("https://wavelink.readthedocs.io/en/latest/", None),
    "discord.py": ("https://discordpy.readthedocs.io/en/latest/", None),
    "asyncpg": ("https://magicstack.github.io/asyncpg/current/", None),
    "aiohttp": ("https://aiohttp.readthedocs.io/en/stable/", None),
}

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]


# The suffix of source filenames.
source_suffix = ".rst"

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages. See the documentation for
# a list of builtin themes.
html_theme = "sphinx_rtd_theme"

html_title = project
html_short_title = project

html_theme_options = {
    "logo_only": False,
    "display_version": True,
    "prev_next_buttons_location": "both",
    "style_nav_header_background": "#343131",
    "collapse_navigation": False,
    "sticky_navigation": False,
}

html_favicon = os.path.join("_images", "html_favicon.png")
html_logo = os.path.join("_images", "html_logo.png")

html_scaled_image_link = False

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]
