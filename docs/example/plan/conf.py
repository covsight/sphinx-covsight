"""The UART verification plan.

One documentation set holds the plan, the register map and the testbench
source, and they cross-reference each other.  The specification is a separate
build (``../spec``); this project consumes its published ``needs.json``.
"""

import os

project = "UART Verification Plan"
author = "UART Verification Team"
release = "1.0"

extensions = [
    "myst_parser",
    "sphinx_covsight",
    "sphinx_systemverilog",
    "sphinx_peakrdl",
]

myst_enable_extensions = ["colon_fence"]

_here = os.path.dirname(__file__)

# ── the register map and the testbench source ────────────────────────────────

# peakrdl_input_files are resolved against the working directory, not conf.py.
peakrdl_input_files = [os.path.join(_here, "..", "rtl", "uart_regs.rdl")]
peakrdl_default_link_to = "doc"

# The design and the testbench are both parsed, because the plan refers to
# both: `sv:` citations name testbench declarations, and the design pages are
# what a reviewer follows a rule down into.
sv_source_dirs = ["../rtl", "../verif"]
sv_doc_style = "native"

# ── the plan ─────────────────────────────────────────────────────────────────

covsight_plan_name = "uart"
covsight_plan_description = "Verification plan for the example UART."
covsight_plan_owner = "uart-verification"

# A pinned copy of the specification's published needs.json.  Pinning rather
# than fetching is the trade-off discussed in docs/guide/extracting-rules.rst.
covsight_needs_json = "_spec/needs.json"

# Where the specification is PUBLISHED, which is not where it is built.  Both
# projects are built by docs/build.sh into the sphinx-covsight documentation, so
# this is a real location and every rule: citation in the extracted testplan
# resolves to a live page.  Point it at your own published specification.
covsight_spec_base_url = "https://dvkit.org/covsight/sphinx-covsight/example/spec/"

covsight_substitutions = {"baud": ["9600", "115200", "460800"]}

covsight_env_policy = {
    "ip_simulation": {
        "title": "IP Simulation",
        "approach": (
            "Boundary UVCs, directed sequences, constrained-random stimulus, "
            "assertions, and a reference model targeting {feature}."
        ),
        "reasoning": (
            "Provides controllability and observability for timing and data bug "
            "classes at practical regression run time."
        ),
        "exit_criteria": [
            "100% regression pass for all planned tests",
            "95%+ functional coverage for implemented scope",
            "100% assertion pass",
        ],
    },
    "formal": {
        "title": "Formal",
        "approach": (
            "Bounded and unbounded property proofs over {feature}, with "
            "assumptions reviewed against the specification."
        ),
        "reasoning": (
            "Exhaustive over the property's cone of influence, which simulation "
            "cannot be for control-path corner cases."
        ),
        "exit_criteria": [
            "All properties proven or bounded to a justified depth",
            "No unreviewed assumptions",
        ],
    },
}

# Policy is data, so the provenance sidecar can record which policy produced the
# derived scores.  A lambda could not be hashed.
covsight_score = "(11 - difficulty) * coverage"

covsight_output = "testplan.json"
covsight_output_format = "both"

exclude_patterns = ["_build", "_spec"]

# ── how this renders in the published site ───────────────────────────────────
#
# See the matching block in ../spec/conf.py.  This project is built into
# ``example/plan/``, and the extracted artifact lands beside it as
# ``testplan.json`` -- the plan you read and the plan a tool consumes, at two
# urls one directory apart.
html_title = "UART Verification Plan"

html_theme = "alabaster"
try:
    import furo  # noqa: F401

    html_theme = "furo"
    # ABSOLUTE urls, not relative ones.  The announcement is injected into
    # every page of the build, including the generated source-listing pages,
    # which sit a directory deeper than the rest -- a relative href is correct
    # on some pages and broken on others, and Sphinx checks neither.
    html_theme_options = {
        "announcement": (
            "The worked example that ships with "
            '<a href="https://dvkit.org/covsight/sphinx-covsight/">'
            "sphinx-covsight</a> &mdash; extracted to "
            '<a href="https://dvkit.org/covsight/sphinx-covsight/example/plan/'
            'testplan.json">testplan.json</a> by this very build.'
        ),
    }
except ImportError:  # pragma: no cover - the example still builds unthemed
    pass
