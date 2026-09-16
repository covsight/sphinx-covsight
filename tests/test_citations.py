"""Citation resolution and the degradation ladder."""

from __future__ import annotations

import pytest

from conftest import find_testpoint
from sphinx_covsight.citations import _index_needs, parse_citations
from sphinx_covsight.model import get_store


def test_parse_citations_splits_on_commas_and_newlines():
    citations = parse_citations("rule:A, rule:B\nrdl:c.d", "index", 10)
    assert [(c.kind, c.target, c.lineno) for c in citations] == [
        ("rule", "A", 10),
        ("rule", "B", 10),
        ("rdl", "c.d", 11),
    ]


def test_index_needs_accepts_both_shapes():
    versioned = {
        "current_version": "1.0",
        "versions": {"1.0": {"needs": {"A": {"id": "A"}}}},
    }
    assert set(_index_needs(versioned)) == {"A"}
    assert set(_index_needs({"needs": {"B": {"id": "B"}}})) == {"B"}


@pytest.mark.sphinx("html", testroot="citations")
def test_rule_citation_resolves(app, plan_of):
    app.build()
    tp = find_testpoint(plan_of(app), "FEAT-001.tp_mixed")
    resolved = {r["item_id"]: r for r in tp["requirements"]}
    assert resolved["UART_1_1_1"]["url"] == "https://spec.example/uart.html#UART_1_1_1"


@pytest.mark.sphinx("html", testroot="citations")
def test_rule_citation_miss_warns_once(app, warning):
    app.build()
    text = warning.getvalue()
    assert text.count("unresolved citation rule:UART_9_9_9") == 1


@pytest.mark.sphinx("html", testroot="citations")
def test_absent_backend_citations_are_recorded_without_a_url(app, plan_of):
    app.build()
    tp = find_testpoint(plan_of(app), "FEAT-001.tp_mixed")
    rdl = next(r for r in tp["requirements"] if r["system"] == "rdl")
    assert rdl == {"item_id": "uart.CTRL.BAUD_DIV", "system": "rdl"}
    sv = next(r for r in tp["requirements"] if r["system"] == "sv")
    assert "url" not in sv


@pytest.mark.sphinx("html", testroot="citations")
def test_absent_backend_does_not_warn(app, warning):
    app.build()
    text = warning.getvalue()
    assert "rdl:uart.CTRL.BAUD_DIV" not in text
    assert "sv:uart_cfg_cg" not in text


@pytest.mark.sphinx("html", testroot="citations")
def test_inline_role_renders_a_link(app):
    app.build()
    html = (app.outdir / "index.html").read_text(encoding="utf-8")
    assert 'href="https://spec.example/uart.html#UART_1_1_1"' in html
    assert "covsight-citation" in html


@pytest.mark.sphinx("html", testroot="no-backends")
def test_absent_backend_single_message(app, status, warning):
    """36 citations across three absent backends must produce three messages, not 36.

    The failure mode this guards is not noise: it is that everyone stops
    writing ``rdl:`` citations.
    """
    app.build()
    log = status.getvalue() + warning.getvalue()
    assert log.count("citation(s) recorded without a URL") == 3
    assert "12 'rdl:' citation(s) recorded without a URL" in log
    assert "12 'sv:' citation(s) recorded without a URL" in log
    assert "12 'rule:' citation(s) recorded without a URL" in log


@pytest.mark.sphinx("html", testroot="no-backends")
def test_build_without_any_backend_succeeds_cleanly(app, warning):
    app.build()
    assert "WARNING" not in warning.getvalue()


@pytest.mark.sphinx("html", testroot="citations", confoverrides={"covsight_strict_citations": "1"})
def test_strict_citations_fails_the_build(app):
    from sphinx.errors import ExtensionError

    with pytest.raises(ExtensionError, match="UART_9_9_9"):
        app.build()


@pytest.mark.sphinx("html", testroot="citations")
def test_citation_records_keep_line_numbers(app):
    app.build()
    tp = next(t for t in get_store(app.env).all_testpoints() if t.id == "FEAT-001.tp_mixed")
    source = (app.srcdir / "index.rst").read_text(encoding="utf-8").splitlines()
    for citation in tp.citations:
        assert citation.target in source[citation.lineno - 1]
