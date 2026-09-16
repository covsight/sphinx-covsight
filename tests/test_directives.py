"""Directive parsing, nesting, and rendering."""

from __future__ import annotations

import pytest

from conftest import find_goal, find_testpoint
from sphinx_covsight.model import get_store


@pytest.mark.sphinx("html", testroot="basic")
def test_records_are_stored(app):
    app.build()
    store = get_store(app.env)
    assert [f.id for f in store.all_features()] == ["FEAT-001", "FEAT-002"]
    assert [e.env for e in store.all_envs()] == ["ip_simulation", "ip_simulation", "formal"]
    assert [tp.id for tp in store.all_testpoints()] == [
        "FEAT-001.tp_start_bit",
        "FEAT-002.ip_simulation.all_supported_divisor_values",
        "FEAT-002.tp_divisor_locked",
    ]


@pytest.mark.sphinx("html", testroot="basic")
def test_feature_options(app):
    app.build()
    feature = next(f for f in get_store(app.env).all_features() if f.id == "FEAT-001")
    assert feature.title == "Character framing"
    assert feature.owner == "alice"
    assert feature.tags == ["uart", "framing"]
    assert feature.desc.startswith("The receiver samples each bit")
    # The body prose stops at the first nested directive.
    assert "covers" not in feature.desc


@pytest.mark.sphinx("html", testroot="basic")
def test_testpoint_options(app):
    app.build()
    tp = next(t for t in get_store(app.env).all_testpoints() if t.id == "FEAT-001.tp_start_bit")
    assert tp.stage == "V1"
    assert tp.priority == "high"
    assert tp.weight == 1
    assert tp.tags == ["smoke"]
    assert tp.env == "ip_simulation"
    assert tp.feature_id == "FEAT-001"
    assert tp.explicit_id is True


@pytest.mark.sphinx("html", testroot="basic")
def test_derived_testpoint_id(app):
    app.build()
    tp = next(t for t in get_store(app.env).all_testpoints() if not t.explicit_id)
    assert tp.id == "FEAT-002.ip_simulation.all_supported_divisor_values"


@pytest.mark.sphinx("html", testroot="basic")
def test_repeated_coverage_bindings_collect_in_order(app):
    app.build()
    tp = next(t for t in get_store(app.env).all_testpoints() if t.id == "FEAT-001.tp_start_bit")
    assert [(b.type, b.path) for b in tp.coverage] == [
        ("covergroup", "uart_env.uart_cfg_cg"),
        ("coverpoint", "uart_env.uart_cfg_cg.parity_cp"),
    ]


@pytest.mark.sphinx("html", testroot="basic")
def test_covers_argument_and_body_forms(app):
    app.build()
    store = get_store(app.env)
    feature = next(f for f in store.all_features() if f.id == "FEAT-001")
    # body form, two targets over two lines
    assert [c.target for c in feature.citations] == ["UART_1_1_1", "UART_1_1_2"]
    tp = next(t for t in store.all_testpoints() if t.id == "FEAT-001.tp_start_bit")
    # argument form, one target
    assert [c.target for c in tp.citations] == ["UART_1_1_1"]


@pytest.mark.sphinx("html", testroot="basic")
def test_na_flag(app):
    app.build()
    tp = next(
        t for t in get_store(app.env).all_testpoints() if t.id == "FEAT-002.tp_divisor_locked"
    )
    assert tp.na is True
    assert tp.tests == []


@pytest.mark.sphinx("html", testroot="nesting")
def test_nested_features(app, plan_of):
    app.build()
    plan = plan_of(app)
    child = find_goal(plan, "FEAT-C")
    assert child["title"] == "Child feature"
    parent = find_goal(plan, "FEAT-P")
    assert any(goal["id"] == "FEAT-C" for goal in parent["goals"])


@pytest.mark.sphinx("html", testroot="nesting")
def test_testpoint_directly_under_feature_has_no_env(app, plan_of):
    app.build()
    tp = find_testpoint(plan_of(app), "FEAT-P.tp_no_env")
    assert "env" not in tp["custom"]["covsight"]
    assert find_goal(plan_of(app), "FEAT-P")["testpoints"][0]["name"] == "FEAT-P.tp_no_env"


@pytest.mark.sphinx("html", testroot="nesting")
def test_directive_inside_container_still_attributes(app, plan_of):
    """Nesting is tracked on an explicit stack, not inferred from node parentage."""
    app.build()
    tp = find_testpoint(plan_of(app), "FEAT-K.ip_simulation.testpoint_inside_two_containers")
    assert tp["custom"]["covsight"]["env"] == "ip_simulation"
    assert tp["custom"]["covsight"]["feature"] == "FEAT-K"


@pytest.mark.sphinx("html", testroot="errors", freshenv=True)
def test_misnesting_is_an_error(app, warning):
    app.build()
    text = warning.getvalue()
    assert "'env' is not allowed at the document root" in text
    assert "'coverage' is not allowed at the document root" in text


@pytest.mark.sphinx("html", testroot="basic")
def test_html_renders_blocks_and_anchors(app):
    app.build()
    html = (app.outdir / "index.html").read_text(encoding="utf-8")
    assert "covsight-feature" in html
    assert "covsight-testpoint" in html
    assert "Feature FEAT-001: Character framing" in html
    assert 'id="covsight-FEAT-001"' in html
    assert 'id="covsight-FEAT-001.tp_start_bit"' in html


@pytest.mark.sphinx("html", testroot="basic")
def test_domain_registers_objects(app):
    app.build()
    domain = app.env.get_domain("covsight")
    assert "FEAT-001" in domain.objects
    assert domain.objects["FEAT-001"][2] == "feature"
    assert domain.objects["FEAT-001.tp_start_bit"][2] == "testpoint"


@pytest.mark.sphinx("html", testroot="nesting", freshenv=True)
def test_domain_xref_roles(app, warning):
    app.build()
    html = (app.outdir / "index.html").read_text(encoding="utf-8")
    assert 'href="#covsight-FEAT-P"' in html
    assert 'href="#covsight-FEAT-P.tp_no_env"' in html
    assert "cannot resolve covsight:tp reference 'FEAT-NOPE'" in warning.getvalue()


@pytest.mark.sphinx("html", testroot="nesting", freshenv=True)
def test_domain_get_objects_feeds_the_search_index(app):
    app.build()
    domain = app.env.get_domain("covsight")
    kinds = {objid: kind for objid, _disp, kind, _doc, _anchor, _prio in domain.get_objects()}
    assert kinds["FEAT-P"] == "feature"
    assert kinds["FEAT-P.tp_no_env"] == "testpoint"
