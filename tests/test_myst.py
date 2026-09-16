"""MyST / RST format parity.

A directive that quietly depends on RST-only behaviour produces output that is
wrong only in MyST, and would be found by a user rather than by CI.  This is
the test that keeps the format-neutral contract (D7) true over time.
"""

from __future__ import annotations

import pytest


@pytest.mark.sphinx("html", testroot="myst")
def test_myst_rst_equivalence(app, plan_of, make_app, rootdir, sphinx_test_tempdir):
    """The same content in both formats extracts to the same plan."""
    import shutil

    app.build()
    myst_plan = plan_of(app)

    srcdir = sphinx_test_tempdir / "basic-for-parity"
    shutil.copytree(rootdir / "test-basic", srcdir, dirs_exist_ok=True)
    rst_app = make_app(srcdir=srcdir)
    rst_app.build()
    rst_plan = plan_of(rst_app)

    assert myst_plan == rst_plan


@pytest.mark.sphinx("html", testroot="myst")
def test_myst_line_numbers_point_at_the_md_source(app, warning):
    """Warnings from a MyST source name the ``.md`` file, not a generated one."""
    app.build()
    from sphinx_covsight.model import get_store

    store = get_store(app.env)
    tp = next(t for t in store.all_testpoints() if t.id == "FEAT-001.tp_start_bit")
    assert tp.docname == "index"
    source = (app.srcdir / "index.md").read_text(encoding="utf-8").splitlines()
    assert "Start bit detection" in source[tp.lineno - 1]


@pytest.mark.sphinx("html", testroot="myst")
def test_citation_line_numbers_are_exact_in_myst(app):
    """A ``covers`` target's line number points at the ``.md`` line that holds it."""
    app.build()
    from sphinx_covsight.model import get_store

    source = (app.srcdir / "index.md").read_text(encoding="utf-8").splitlines()
    citations = list(get_store(app.env).all_citations())
    assert citations
    for citation in citations:
        assert citation.target in source[citation.lineno - 1]


@pytest.mark.sphinx("html", testroot="myst")
def test_backtick_fences_nest_inside_colon_fences(app):
    """Leaf directives use backtick fences, which buys one free nesting level."""
    app.build()
    from sphinx_covsight.model import get_store

    tp = next(t for t in get_store(app.env).all_testpoints() if t.id == "FEAT-001.tp_start_bit")
    assert [b.type for b in tp.coverage] == ["covergroup", "coverpoint"]
    assert tp.tests == ["uart_framing_test", "uart_smoke_test"]
