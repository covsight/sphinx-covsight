"""The shipped example is also the test fixture.

Every guide quotes the example by ``literalinclude``, so a golden diff here is
what keeps the documentation honest.
"""

from __future__ import annotations

import json
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
