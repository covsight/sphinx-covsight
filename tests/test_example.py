"""The shipped example is also the test fixture.

Every guide quotes the example by ``literalinclude``, so a golden diff here is
what keeps the documentation honest.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
EXAMPLE = REPO / "docs" / "example"
PLAN = EXAMPLE / "plan"
SPEC = EXAMPLE / "spec"
GOLDEN = EXAMPLE / "_golden" / "testplan.json"

pytest.importorskip("myst_parser")
pytest.importorskip("sphinx_needs")
pytest.importorskip("sphinx_systemverilog")
pytest.importorskip("sphinx_peakrdl")


def build_plan(tmp_path: Path, *, strict: bool = True, **confoverrides) -> dict:
    from sphinx.application import Sphinx

    out = tmp_path / "out"
    app = Sphinx(
        srcdir=str(PLAN),
        confdir=str(PLAN),
        outdir=str(out),
        doctreedir=str(tmp_path / "doctrees"),
        buildername="html",
        confoverrides=confoverrides,
        freshenv=True,
        warningiserror=strict,
        status=None,
    )
    app.build()
    return json.loads((out / "testplan.json").read_text(encoding="utf-8"))


def test_example_plan_builds_clean_and_matches_the_golden(tmp_path):
    from sphinx_covsight.cli import diff_plans

    plan = build_plan(tmp_path)
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert diff_plans(golden, plan) == []


def test_example_spec_builds_clean_and_publishes_needs(tmp_path):
    from sphinx.application import Sphinx

    out = tmp_path / "spec-out"
    app = Sphinx(
        srcdir=str(SPEC),
        confdir=str(SPEC),
        outdir=str(out),
        doctreedir=str(tmp_path / "spec-doctrees"),
        buildername="html",
        freshenv=True,
        warningiserror=True,
        status=None,
    )
    app.build()
    needs = json.loads((out / "needs.json").read_text(encoding="utf-8"))
    published = needs["versions"][needs["current_version"]]["needs"]
    assert len(published) == 8
    assert set(published) >= {"UART_1_1_1", "UART_3_2_4"}


def test_pinned_needs_json_matches_the_spec(tmp_path):
    """The pinned copy is the cross-repo risk made visible; keep it current."""
    from sphinx.application import Sphinx

    out = tmp_path / "spec-out"
    app = Sphinx(
        srcdir=str(SPEC),
        confdir=str(SPEC),
        outdir=str(out),
        doctreedir=str(tmp_path / "spec-doctrees"),
        buildername="html",
        freshenv=True,
        status=None,
    )
    app.build()
    fresh = json.loads((out / "needs.json").read_text(encoding="utf-8"))
    pinned = json.loads((PLAN / "_spec" / "needs.json").read_text(encoding="utf-8"))

    def ids(doc):
        return {
            need_id: need["title"]
            for need_id, need in doc["versions"][doc["current_version"]]["needs"].items()
        }

    assert ids(pinned) == ids(fresh)


def test_example_is_built_twice_identically(tmp_path):
    first = build_plan(tmp_path / "a")
    second = build_plan(tmp_path / "b")
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_example_stays_within_its_size_cap():
    """Large examples are not read.  The cap is 6 testpoints and 8 rules."""
    from sphinx_covsight.emit import count_plan

    counts = count_plan(json.loads(GOLDEN.read_text(encoding="utf-8")))
    assert counts["testpoints"] <= 6
    assert counts["goals"] <= 8


def test_every_citation_in_the_example_resolves():
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    unresolved = []

    def walk(goals):
        for goal in goals:
            for requirement in goal.get("custom", {}).get("covsight", {}).get("requirements", []):
                if "url" not in requirement:
                    unresolved.append(requirement["item_id"])
            for tp in goal.get("testpoints", []):
                for requirement in tp.get("requirements", []):
                    if "url" not in requirement:
                        unresolved.append(requirement["item_id"])
            walk(goal.get("goals", []))

    walk(golden["goals"])
    assert unresolved == []


@pytest.mark.parametrize("system", ["spec", "rdl", "sv"])
def test_example_exercises_every_citation_backend(system):
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    systems = set()

    def walk(goals):
        for goal in goals:
            for requirement in goal.get("custom", {}).get("covsight", {}).get("requirements", []):
                systems.add(requirement["system"])
            for tp in goal.get("testpoints", []):
                for requirement in tp.get("requirements", []):
                    systems.add(requirement["system"])
            walk(goal.get("goals", []))

    walk(golden["goals"])
    assert system in systems


def test_the_example_rtl_and_testbench_elaborate():
    """The example's SystemVerilog is real source, not a sketch.

    A design that does not elaborate would still render perfectly well on the
    plan's pages, and every ``sv:`` citation in the plan would still resolve --
    the documentation extension parses declarations and never builds a
    hierarchy. This is the only thing standing between the example and
    collateral that merely looks like it compiles.
    """
    pyslang = pytest.importorskip("pyslang")

    sources = sorted(str(p) for p in (EXAMPLE / "rtl").glob("*.sv"))
    sources += sorted(str(p) for p in (EXAMPLE / "verif").glob("*.sv"))
    assert sources, "no SystemVerilog found; did the example move?"

    driver = pyslang.driver.Driver()
    driver.addStandardArgs()
    assert driver.parseCommandLine(" ".join(["slang", "--top", "uart_tb", *sources]))
    assert driver.parseAllSources()

    compilation = driver.createCompilation()
    engine = pyslang.DiagnosticEngine(driver.sourceManager)
    client = pyslang.TextDiagnosticClient()
    engine.addClient(client)
    for diagnostic in compilation.getAllDiagnostics():
        engine.issue(diagnostic)
    # Warnings too: an example is read as a model of how to write the thing, so
    # it does not get to ship with the sloppiness a real project tolerates.
    assert client.getString() == ""


def test_every_test_named_in_the_plan_exists_in_the_testbench():
    """A plan naming a test nobody wrote reads exactly like one that does.

    ``covsight.testpoint-unmapped`` catches a testpoint with *no* tests. Nothing
    in the extension can catch a testpoint whose tests are fictional, because
    the extension has no idea what a test is -- ``tests`` bodies are opaque
    strings to it, by design, so that a plan can be written before the
    testbench exists. Past that point the correspondence has to be checked
    somewhere, and for this example it is checked here.
    """
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))

    named: set[str] = set()

    def walk(goals):
        for goal in goals:
            for tp in goal.get("testpoints", []):
                named.update(tp.get("tests", []))
            walk(goal.get("goals", []))

    walk(golden["goals"])
    assert named, "the plan names no tests at all; did the schema change?"

    # Both trees: the formal environment's "tests" are property sets, which are
    # modules in the design tree rather than classes in the testbench.
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for directory in ("rtl", "verif")
        for path in sorted((EXAMPLE / directory).glob("*.sv"))
    )

    missing = [
        name
        for name in sorted(named)
        if not re.search(rf"^\s*(?:class|module)\s+{re.escape(name)}\b", source, re.MULTILINE)
    ]
    assert missing == [], f"named in the plan, absent from the source: {missing}"


def test_example_extracts_without_the_optional_extensions(tmp_path, monkeypatch):
    """Removing sphinx-peakrdl and sphinx-systemverilog still builds and extracts."""
    plan = build_plan(
        tmp_path,
        # Not strict: without sphinx-peakrdl the inline {rdl:doc-ref} role in
        # feat_framing.md is an unknown role, which is the expected degradation
        # for the *other* extension's role, not for covsight's citations.
        strict=False,
        extensions=["myst_parser", "sphinx_covsight"],
        exclude_patterns=["_build", "_spec", "registers.md", "testbench.md"],
    )
    names = []

    def walk(goals):
        for goal in goals:
            names.extend(tp["name"] for tp in goal.get("testpoints", []))
            walk(goal.get("goals", []))

    walk(plan["goals"])
    assert len(names) == 6
