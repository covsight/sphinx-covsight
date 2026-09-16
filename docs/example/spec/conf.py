"""The UART architecture specification.

Its only job here is to publish ``needs.json``, which the plan project consumes
to resolve ``rule:`` citations.
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
html_theme = "alabaster"
