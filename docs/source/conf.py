# SPDX-FileCopyrightText: 2020-2025 Efabless Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# SPDX-License-Identifier: Apache-2.0

# Configuration file for the Sphinx documentation builder.
# Yes, it needs to be in this directory. Don't try to move it.
# Yes, it needs to be called conf.py


# -- Path setup --------------------------------------------------------------
import os
import sys

sys.path.insert(0, os.path.abspath("../_ext"))
sys.path.insert(0, os.path.abspath("../../"))

# -- Project information -----------------------------------------------------
project = "LibreLane"
copyright = "2020-2025 Efabless Corporation and contributors"
author = "Efabless Corporation"
repo = "https://github.com/librelane/librelane"
branch = "main"


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
custom_extensions = [
    "flow_step_var_directives",
    "generate_module_autodocs",
    "generate_configvar_docs",
    "migration_comparison",
]
third_party_extensions = [
    "myst_parser",
    "sphinx.ext.todo",
    "sphinx.ext.autodoc",
    "sphinx.ext.graphviz",
    "sphinx.ext.mathjax",
    "sphinxcontrib.bibtex",
    "sphinx_design",
    "sphinx_tippy",
    "sphinx_copybutton",
    "sphinx_subfigure",
]
extensions = third_party_extensions + custom_extensions
try:
    import sphinxcontrib.spelling  # noqa: F401

    try:
        import enchant  # noqa: F401

        extensions += [
            "sphinxcontrib.spelling",
        ]

        spelling_lang = "en_US"
        tokenizer_lang = "en_US"
    except ImportError:
        print("Failed to import 'enchant'- spellchecker cannot run", file=sys.stderr)
except ImportError:
    pass

source_suffix = {
    ".md": "markdown",
    ".rst": "restructuredtext",
}

root_doc = "index"

# Templates
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
    "venv",
    "install",
    "pdks",
    ".github",
    # Files included in other rst files.
]


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_title = "LibreLane Documentation"
html_theme = "furo"
# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
html_theme_options = {
    "source_repository": repo,
    "source_branch": branch,
    "source_directory": "docs/source",
    "footer_icons": [
        {
            "name": "GitHub",
            "url": repo,
            "html": """
                <svg stroke="currentColor" fill="currentColor" stroke-width="0" viewBox="0 0 16 16">
                    <path fill-rule="evenodd" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8z"></path>
                </svg>
            """,
            "class": "",
        },
    ],
}

html_static_path = ["../_static"]
html_css_files = [
    "css/custom.css",
]

numfig = True

# Bibtex
bibtex_bibfiles = ["refs.bib"]
bibtex_default_style = "unsrt"

# Autodoc
generate_module_autodocs = [("librelane", "reference/api")]
autodoc_typehints = "both"
autodoc_member_order = "bysource"
autosectionlabel_prefix_document = True

# MyST
myst_heading_anchors = 4
myst_enable_extensions = [
    "colon_fence",
    "attrs_block",
    "attrs_inline",
    "dollarmath",
]
myst_url_schemes = {
    "http": None,
    "https": None,
    "doi": "https://doi.org/{{path}}",
}

# GraphViz
graphviz_output_format = "svg"

# sphinx_copybutton
copybutton_exclude = ".linenos, .gp"

# sphinx_tippy
tippy_enable_wikitips = False

spelling_show_suggestions = True
spelling_suggestion_limit = 1
