"""The documentation itself builds clean, and its reference tables come from the code."""

from __future__ import annotations

import json
import re
import subprocess
import textwrap
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
DOCS = REPO / "docs"

pytest.importorskip("myst_parser")
pytest.importorskip("sphinx_needs")


@pytest.fixture(scope="module")
def built_docs(tmp_path_factory) -> Path:
    from sphinx.application import Sphinx

    tmp = tmp_path_factory.mktemp("docs")
    out = tmp / "out"
    app = Sphinx(
        srcdir=str(DOCS),
        confdir=str(DOCS),
        outdir=str(out),
        doctreedir=str(tmp / "doctrees"),
        buildername="html",
        freshenv=True,
        warningiserror=True,
        status=None,
    )
    app.build()
    return out


def test_docs_build_clean_under_W_and_nitpicky(built_docs):
    assert (built_docs / "index.html").is_file()


def test_configuration_reference_lists_every_config_value(built_docs):
    from sphinx_covsight import CONFIG_VALUES

    html = (built_docs / "reference" / "configuration.html").read_text(encoding="utf-8")
    for name, _default, _rebuild, _doc in CONFIG_VALUES:
        assert name in html, f"{name} missing from the generated configuration reference"


def test_directive_reference_lists_every_directive_and_option(built_docs):
    from sphinx_covsight.directives import DIRECTIVES

    html = (built_docs / "reference" / "directives.html").read_text(encoding="utf-8")
    for name, directive in DIRECTIVES.items():
        assert f'<span class="pre">{name}</span>' in html or name in html
        for option in directive.option_spec or {}:
            assert f":{option}:" in re.sub("<[^>]+>", "", html)


def test_warning_reference_lists_every_subtype(built_docs):
    from sphinx_covsight.logging import SUBTYPES

    text = re.sub("<[^>]+>", "", (built_docs / "reference" / "directives.html").read_text())
    for subtype in SUBTYPES:
        assert f"covsight.{subtype}" in text


def test_guides_quote_the_example_rather_than_restating_it(built_docs):
    """Every code block in a guide is a literalinclude from docs/example."""
    for guide in (DOCS / "guide").glob("*.rst"):
        source = guide.read_text(encoding="utf-8")
        includes = re.findall(r"\.\. literalinclude:: (\S+)", source)
        for target in includes:
            assert (guide.parent / target).resolve().is_file(), f"{guide.name}: {target}"


def test_index_links_every_guide():
    index = (DOCS / "index.rst").read_text(encoding="utf-8")
    for guide in (DOCS / "guide").glob("*.rst"):
        assert f"guide/{guide.stem}" in index


# ── the published site: three projects, nested ───────────────────────────────


@pytest.fixture(scope="module")
def built_site(tmp_path_factory) -> Path:
    """The whole published doc set, built the way CI builds it.

    Runs ``docs/build.sh`` rather than reimplementing it, because the script is
    the thing both workflows invoke: a test that built the three projects itself
    would pass while the script consumers actually run was broken.
    """
    pytest.importorskip("sphinx_systemverilog")
    pytest.importorskip("sphinx_peakrdl")

    out = tmp_path_factory.mktemp("site") / "html"
    subprocess.run(
        ["bash", str(DOCS / "build.sh"), str(out)],
        check=True,
        capture_output=True,
        text=True,
        cwd=REPO,
    )
    return out


def test_the_site_nests_both_example_projects(built_site):
    for page in (
        "index.html",
        "example/spec/index.html",
        "example/plan/index.html",
        "example/plan/testplan.json",
    ):
        assert (built_site / page).is_file(), f"{page} missing from the built site"


def test_every_relative_link_in_the_site_resolves(built_site):
    """The three projects reach each other with hrefs Sphinx never checks.

    ``example/index.html`` links to ``spec/index.html`` and
    ``plan/registers.html``; ``traceability.html`` links to a rule anchor in the
    specification; the plan's ``design`` page links back up to the
    walkthrough. None of those are Sphinx cross-references -- the targets belong
    to different projects, so to the build that emits them they are opaque
    strings. This is the only thing standing behind them.

    The sub-builds are walked too, rather than trusted to their own strict
    builds, because the links that cross a project boundary are exactly the ones
    a strict build cannot see. That is not hypothetical: it is how the theme
    announcement was found to be linking with a relative href that was correct
    on most pages and broken on the generated source listings.
    """
    dangling, checked = [], 0
    for page in built_site.rglob("*.html"):
        for href in re.findall(r'href="([^"]+)"', page.read_text(encoding="utf-8")):
            if href.startswith(("http://", "https://", "mailto:", "#")):
                continue
            # Sphinx cache-busts its own assets with ?v=<hash>, and an anchor
            # into another project is not a file either.
            target = href.split("#")[0].split("?")[0]
            if not target:
                continue
            checked += 1
            if not (page.parent / target).resolve().exists():
                dangling.append(f"{page.relative_to(built_site)} -> {href}")
    assert dangling == []
    assert checked, "no relative links found at all; did the build produce anything?"


def test_the_tour_links_into_both_sub_builds(built_site):
    """Guards the above against passing on a doc set that stopped linking out.

    A resolve-everything test is happiest when there is nothing to resolve, so
    the cross-project links are asserted to exist by name.
    """
    tour = (built_site / "example" / "index.html").read_text(encoding="utf-8")
    for href in ("spec/index.html", "plan/index.html", "plan/design.html", "plan/testplan.json"):
        assert f'href="{href}"' in tour, f"the tour no longer links to {href}"

    # The traceability page opens on a rule and links straight at it.
    trace = (built_site / "example" / "traceability.html").read_text(encoding="utf-8")
    assert 'href="spec/uart.html#UART_3_2_1"' in trace
    spec = (built_site / "example" / "spec" / "uart.html").read_text(encoding="utf-8")
    assert 'id="UART_3_2_1"' in spec


def test_the_traceability_page_quotes_the_artifact_accurately():
    """The two JSON blocks on the tour are hand-written; keep them true.

    They cannot be ``literalinclude`` excerpts: the artifact's keys are sorted at
    emit, so the fields the narrative needs are not contiguous, and an anchored
    slice of them is not valid JSON to highlight. Written out instead, and
    checked here against the committed artifact field by field.
    """
    golden = json.loads((DOCS / "example" / "_golden" / "testplan.json").read_text())
    page = (DOCS / "example" / "traceability.rst").read_text(encoding="utf-8")

    testpoints = {}

    def walk(goals):
        for goal in goals:
            testpoints.update({tp["name"]: tp for tp in goal.get("testpoints", [])})
            walk(goal.get("goals", []))

    walk(golden["goals"])
    actual = testpoints["FEAT-002.tp_divisors"]

    blocks = [
        json.loads(textwrap.dedent(body))
        for body in re.findall(r"\.\. code-block:: json\n\n((?:   [^\n]*\n|\n)+)", page)
    ]
    assert blocks, "no JSON blocks found; did the directive or its indent change?"

    for block in blocks:
        for key, quoted in block.items():
            if key == "requirements":
                for requirement in quoted:
                    assert requirement in actual["requirements"], requirement
            else:
                assert actual[key] == quoted, f"{key}: page says {quoted!r}"


def test_published_citation_urls_point_into_the_published_site(built_site):
    """A rule: citation resolves to a page this build actually produced.

    ``covsight_spec_base_url`` is an absolute url, so the artifact cannot be
    checked against the filesystem directly -- map it back onto the site root
    and confirm the target is there. A renamed spec page would otherwise break
    every published citation silently.
    """
    plan = json.loads((built_site / "example" / "plan" / "testplan.json").read_text())
    base = "https://dvkit.org/covsight/sphinx-covsight/"
    checked = 0

    def walk(goals):
        nonlocal checked
        for goal in goals:
            requirements = list(goal.get("custom", {}).get("covsight", {}).get("requirements", []))
            for tp in goal.get("testpoints", []):
                requirements += tp.get("requirements", [])
            for requirement in requirements:
                url = requirement.get("url")
                if url is None or not url.startswith(base):
                    continue
                target, _, fragment = url[len(base) :].partition("#")
                page = built_site / target
                assert page.is_file(), f"{requirement['item_id']} -> {url}"
                # The fragment is the half that actually rots: a sphinx-needs
                # version bump or a renumbered rule leaves the page in place and
                # the anchor gone, so the link still 200s at the wrong content.
                if fragment:
                    assert f'id="{fragment}"' in page.read_text(encoding="utf-8"), (
                        f"{requirement['item_id']}: {target} has no anchor #{fragment}"
                    )
                checked += 1
            walk(goal.get("goals", []))

    walk(plan["goals"])
    assert checked, "no absolute citation urls were checked; did the base url change?"
