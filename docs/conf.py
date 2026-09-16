"""Documentation for sphinx-covsight itself."""

import os
import sys

sys.path.insert(0, os.path.abspath("_ext"))

project = "sphinx-covsight"
author = "Matthew Ballance"
copyright = "2026, Matthew Ballance"

from sphinx_covsight import __version__ as release  # noqa: E402

version = release

extensions = ["covsight_docs"]

# The guides quote the example rather than restating it, so every snippet in
# these pages is executable and cannot drift.
#
# `example/` is not excluded wholesale: the pages directly in it are THIS
# project's tour of the example, while its sub-directories are the example's own
# Sphinx projects and their inputs. Those are built separately by docs/build.sh
# and nested under this build's output, so reading them here would both fail
# (the plan uses directives this project does not load) and produce a second,
# broken copy of pages that already exist.
exclude_patterns = [
    "_build",
    "design",
    "example/spec",
    "example/plan",
    "example/rtl",
    "example/verif",
    "example/_golden",
]

nitpicky = True

html_theme = "furo" if os.environ.get("COVSIGHT_DOCS_THEME") != "alabaster" else "alabaster"
try:
    import furo  # noqa: F401
except ImportError:  # pragma: no cover
    html_theme = "alabaster"

html_title = f"sphinx-covsight {release}"
