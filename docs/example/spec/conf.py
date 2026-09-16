"""The UART architecture specification.

Its job here is twofold: publish ``needs.json``, which the plan project consumes
to resolve ``rule:`` citations, and be the page those citations actually land
on.  It is built by ``docs/build.sh`` into ``example/spec/`` of the published
site, so a ``rule:`` url in the extracted testplan resolves to a real document.
"""

project = "UART Specification"
author = "UART Working Group"
release = "1.0"

extensions = ["myst_parser", "sphinx_needs"]

myst_enable_extensions = ["colon_fence"]

# ``rule`` is the need type the plan cites.  Nothing else in this spec earns an
# id: explanation and examples are prose, normative statements are rules.
needs_types = [
    {
        "directive": "rule",
        "title": "Rule",
        "prefix": "UART_",
        "color": "#BFD8D2",
        "style": "node",
    },
]

# The default id charset.  Widening it breaks the {need} cross-reference role
# for ids containing '.', '-' or '/' — see docs/design/myst-authoring.md §6.
needs_id_regex = r"^[A-Za-z0-9_]{5,}"

needs_build_json = True
needs_reproducible_json = True

exclude_patterns = ["_build"]

# ── how this renders in the published site ───────────────────────────────────
#
# ``docs/build.sh`` builds this project into ``example/spec/``, two levels below
# the sphinx-covsight documentation root.  Readers arrive here by following a
# citation url out of the extracted testplan, so the announcement bar is load
# bearing: without it this looks like a real UART specification that happens to
# be hosted in someone else's doc set.
html_title = "UART Specification"

html_theme = "alabaster"
try:
    import furo  # noqa: F401

    html_theme = "furo"
    html_theme_options = {
        # Absolute, for the reason given in ../plan/conf.py.
        "announcement": (
            "The worked example that ships with "
            '<a href="https://dvkit.org/covsight/sphinx-covsight/">'
            "sphinx-covsight</a> &mdash; the specification the example plan cites."
        ),
    }
except ImportError:  # pragma: no cover - the example still builds unthemed
    pass
