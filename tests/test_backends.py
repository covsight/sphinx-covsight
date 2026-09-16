"""The two optional citation backends, and the proof that they are optional.

``sv:`` resolves against the SystemVerilog domain; ``rdl:`` against the
compiled SystemRDL model.  Both degrade to "recorded without a url" when their
extension is absent, which is the normal case while a plan is being written
before the RTL exists.
"""

from __future__ import annotations

import pytest

from conftest import find_testpoint

sphinx_systemverilog = pytest.importorskip("sphinx_systemverilog")
sphinx_peakrdl = pytest.importorskip("sphinx_peakrdl")


def requirements(plan, name):
    return {r["item_id"]: r for r in find_testpoint(plan, name)["requirements"]}


# ── sv: ───────────────────────────────────────────────────────────────────────


@pytest.mark.sphinx("html", testroot="sv", freshenv=True)
def test_sv_exact_fullname(app, plan_of):
    app.build()
    hit = requirements(plan_of(app), "FEAT-002.tp_divisors")["uart_pkg::uart_cfg::uart_cfg_cg"]
    assert hit["url"].endswith("#sv-uart_pkg-uart_cfg-uart_cfg_cg")


@pytest.mark.sphinx("html", testroot="sv", freshenv=True)
def test_sv_leaf_candidate_match(app, plan_of):
    """The sv domain keys on declaration paths; a leaf name resolves when unique."""
    app.build()
    hit = requirements(plan_of(app), "FEAT-002.tp_divisors")["uart_cfg_cg"]
    assert hit["url"].endswith("#sv-uart_pkg-uart_cfg-uart_cfg_cg")


@pytest.mark.sphinx("html", testroot="sv", freshenv=True)
def test_sv_ambiguous_leaf_warns_and_records_no_url(app, plan_of, warning):
    app.build()
    text = warning.getvalue()
    assert "sv:shared_cg is ambiguous" in text
    assert "uart_pkg::uart_rx_mon::shared_cg" in text
    assert "url" not in requirements(plan_of(app), "FEAT-002.tp_divisors")["shared_cg"]


@pytest.mark.sphinx("html", testroot="sv", freshenv=True)
def test_sv_miss_warns(app, plan_of, warning):
    app.build()
    assert "unresolved citation sv:no_such_covergroup" in warning.getvalue()
    assert "url" not in requirements(plan_of(app), "FEAT-002.tp_divisors")["no_such_covergroup"]


@pytest.mark.sphinx("html", testroot="sv", freshenv=True)
def test_coverage_binding_leaf_validation(app, warning):
    """D2: only the leaf is checked — UCIS instance paths are a different namespace."""
    app.build()
    text = warning.getvalue()
    assert "no coverpoint named 'nonexistent_cp' is documented in the sv domain" in text
    # The valid bindings, whose UCIS instance prefix does not exist in the sv
    # domain at all, are not reported.
    assert "uart_cfg_cg'" not in text
    assert "baud_div_cp" not in text


@pytest.mark.sphinx(
    "html",
    testroot="sv",
    freshenv=True,
    confoverrides={"covsight_validate_coverage_bindings": "0"},
)
def test_coverage_binding_validation_is_config_gated(app, warning):
    app.build()
    assert "is documented in the sv domain" not in warning.getvalue()


@pytest.mark.sphinx("html", testroot="sv", freshenv=True)
def test_sv_backend_recorded_in_provenance(app):
    import json
    from pathlib import Path

    app.build()
    sidecar = json.loads(
        (Path(app.outdir) / "testplan.provenance.json").read_text(encoding="utf-8")
    )
    assert sidecar["citation_backends"]["sv"] is True
    assert sidecar["citation_backends"]["rdl"] is False


# ── rdl: ──────────────────────────────────────────────────────────────────────


@pytest.mark.sphinx("html", testroot="rdl", freshenv=True)
def test_rdl_register_and_field_links(app, plan_of):
    app.build()
    hits = requirements(plan_of(app), "FEAT-002.tp_divisors")
    assert hits["uart.CTRL"]["url"] == "peakrdl-html/index.html?p=uart.CTRL"
    assert hits["uart.CTRL.PARITY_EN"]["url"] == "peakrdl-html/index.html?p=uart.CTRL#PARITY_EN"


@pytest.mark.sphinx("html", testroot="rdl", freshenv=True)
def test_rdl_miss_warns(app, plan_of, warning):
    app.build()
    assert "unresolved citation rdl:uart.NOSUCH.FIELD" in warning.getvalue()
    assert "url" not in requirements(plan_of(app), "FEAT-002.tp_divisors")["uart.NOSUCH.FIELD"]


@pytest.mark.sphinx("html", testroot="rdl", freshenv=True)
def test_rdl_feature_level_citation_resolves(app, plan_of):
    from conftest import find_goal

    app.build()
    goal = find_goal(plan_of(app), "FEAT-002")
    assert goal["custom"]["covsight"]["requirements"][0]["url"].endswith("#BAUD_DIV")


@pytest.mark.sphinx(
    "html",
    testroot="rdl",
    freshenv=True,
    confoverrides={"covsight_doc_base_url": "https://docs.example/"},
)
def test_doc_base_url_prefixes_resolved_links(app, plan_of):
    app.build()
    hits = requirements(plan_of(app), "FEAT-002.tp_divisors")
    assert hits["uart.CTRL"]["url"].startswith("https://docs.example/peakrdl-html/")


# ── the minimal-deps leg ──────────────────────────────────────────────────────


@pytest.mark.sphinx("html", testroot="no-backends", freshenv=True)
def test_extraction_without_either_extension(app, plan_of):
    """Removing both extras must still build and still extract."""
    app.build()
    plan = plan_of(app)
    requirement_systems = {
        r["system"]
        for goal in plan["goals"]
        for sub in goal.get("goals", [])
        for tp in sub.get("testpoints", [])
        for r in tp.get("requirements", [])
    }
    assert requirement_systems == {"rdl", "sv", "spec"}
