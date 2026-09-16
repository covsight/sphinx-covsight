"""The mapping from authored records to covsight testplan v1."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import find_goal, find_testpoint, iter_testpoints
from sphinx_covsight.checks import check_env_denormalization
from sphinx_covsight.extract import FORMAT_VERSION, SCHEMA_URI, expand_tests

SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / "covsight-core"
    / "python"
    / "covsight"
    / "core"
    / "schema"
    / "testplan.schema.json"
)


@pytest.mark.sphinx("html", testroot="basic")
def test_plan_header(app, plan_of):
    app.build()
    plan = plan_of(app)
    assert plan["schema"] == SCHEMA_URI
    assert plan["format_version"] == FORMAT_VERSION
    assert plan["name"] == "uart"
    assert plan["owner"] == "verification"
    assert plan["imports"] == []
    assert plan["substitutions"] == {"baud": ["9600", "115200"]}


@pytest.mark.sphinx("html", testroot="basic")
def test_feature_goal_fields(app, plan_of):
    app.build()
    goal = find_goal(plan_of(app), "FEAT-001")
    assert goal["title"] == "Character framing"
    assert goal["owner"] == "alice"
    assert goal["tags"] == ["framing", "uart"]  # sorted: a set, not a sequence
    assert goal["desc"].startswith("The receiver samples")
    assert goal["custom"]["covsight"]["requirements"] == [
        {"item_id": "UART_1_1_1", "system": "spec"},
        {"item_id": "UART_1_1_2", "system": "spec"},
    ]


@pytest.mark.sphinx("html", testroot="basic")
def test_env_goal_carries_policy(app, plan_of):
    app.build()
    goal = find_goal(plan_of(app), "FEAT-001.ip_simulation")
    custom = goal["custom"]["covsight"]
    assert goal["title"] == "IP Simulation"
    assert custom["env"] == "ip_simulation"
    assert custom["scope"] == "block"
    assert custom["difficulty"] == 3
    assert custom["coverage_score"] == 8
    assert custom["overall_score"] == (11 - 3) * 8
    assert custom["approach"].endswith("targeting Character framing.")
    assert custom["exit_criteria"] == ["100% regression pass", "95%+ functional coverage"]


@pytest.mark.sphinx("html", testroot="basic")
def test_testpoint_fields(app, plan_of):
    app.build()
    tp = find_testpoint(plan_of(app), "FEAT-001.tp_start_bit")
    assert tp["stage"] == "V1"
    assert tp["priority"] == "high"
    assert tp["tags"] == ["smoke"]
    assert tp["tests"] == ["uart_framing_test", "uart_smoke_test"]
    assert tp["coverage"] == [
        {"path": "uart_env.uart_cfg_cg", "type": "covergroup"},
        {"path": "uart_env.uart_cfg_cg.parity_cp", "type": "coverpoint"},
    ]
    assert tp["requirements"] == [{"item_id": "UART_1_1_1", "system": "spec"}]
    assert tp["custom"]["covsight"] == {
        "env": "ip_simulation",
        "feature": "FEAT-001",
        "title": "Start bit detection",
    }


@pytest.mark.sphinx("html", testroot="basic")
def test_na_testpoint_has_no_tests(app, plan_of):
    app.build()
    tp = find_testpoint(plan_of(app), "FEAT-002.tp_divisor_locked")
    assert tp["na"] is True
    assert "tests" not in tp


@pytest.mark.sphinx("html", testroot="basic", confoverrides={"covsight_env_in_custom": "0"})
def test_env_as_a_top_level_field(app, plan_of):
    """The fallback for when covsight-core's schema grows the ``env`` field."""
    app.build()
    tp = find_testpoint(plan_of(app), "FEAT-001.tp_start_bit")
    assert tp["env"] == "ip_simulation"
    assert "env" not in tp["custom"]["covsight"]


@pytest.mark.sphinx("html", testroot="basic")
def test_env_denormalization_consistent(app, plan_of):
    """D1: every testpoint's env equals the env of its nearest enclosing env goal."""
    app.build()
    assert check_env_denormalization(plan_of(app), env_in_custom=True) == []


@pytest.mark.sphinx("html", testroot="nesting")
def test_env_denormalization_with_three_levels(app, plan_of):
    app.build()
    plan = plan_of(app)
    assert check_env_denormalization(plan, env_in_custom=True) == []
    # a testpoint outside any env goal carries no env
    tp = find_testpoint(plan, "FEAT-P.tp_no_env")
    assert "env" not in tp["custom"]["covsight"]


@pytest.mark.sphinx("html", testroot="nesting")
def test_empty_feature_is_planned(app, plan_of):
    app.build()
    goal = find_goal(plan_of(app), "FEAT-P")
    # FEAT-P has a direct testpoint, so it is not 'planned'
    assert "status" not in goal


@pytest.mark.sphinx("html", testroot="errors")
def test_feature_with_no_testpoints_is_planned(app, plan_of):
    app.build()
    assert find_goal(plan_of(app), "FEAT-EMPTY")["status"] == "planned"


# ── substitutions ─────────────────────────────────────────────────────────────


@pytest.mark.sphinx("html", testroot="substitutions")
def test_substitution_expansion(app, plan_of):
    app.build()
    plan = plan_of(app)
    assert find_testpoint(plan, "FEAT-001.tp_single")["tests"] == [
        "uart_baud_9600_test",
        "uart_baud_115200_test",
    ]
    cross = find_testpoint(plan, "FEAT-001.tp_cross")
    assert cross["tests"] == [
        "uart_9600_none_test",
        "uart_9600_even_test",
        "uart_9600_odd_test",
        "uart_115200_none_test",
        "uart_115200_even_test",
        "uart_115200_odd_test",
    ]
    assert cross["source_template"] == "uart_{baud}_{parity}_test"
    literal = find_testpoint(plan, "FEAT-001.tp_literal")
    assert literal["tests"] == ["uart_smoke_test", "uart_regression_test"]
    assert "source_template" not in literal


@pytest.mark.sphinx("html", testroot="substitutions")
def test_unbound_substitution_keeps_the_name(app, plan_of):
    app.build()
    tp = find_testpoint(plan_of(app), "FEAT-001.tp_unbound")
    assert tp["tests"] == ["uart_{stopbits}_test"]


def test_expand_tests_is_cartesian_over_sorted_keys():
    expanded, unknown = expand_tests(["t_{b}_{a}"], {"a": ["1", "2"], "b": ["x", "y"]})
    assert expanded == ["t_x_1", "t_y_1", "t_x_2", "t_y_2"]
    assert unknown == set()


def test_expand_tests_reports_unknown_keys():
    expanded, unknown = expand_tests(["t_{nope}"], {"a": ["1"]})
    assert expanded == ["t_{nope}"]
    assert unknown == {"nope"}


# ── schema conformance ────────────────────────────────────────────────────────


@pytest.mark.skipif(not SCHEMA_PATH.is_file(), reason="covsight-core schema not available")
@pytest.mark.sphinx("html", testroot="basic")
def test_plan_validates_against_testplan_v1(app, plan_of):
    jsonschema = pytest.importorskip("jsonschema")
    app.build()
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(plan_of(app), schema)


@pytest.mark.sphinx("html", testroot="basic")
def test_round_trip_through_covsight_core(app, plan_of):
    """T-208: the emitted plan is a first-class covsight object, not a format."""
    testplan = pytest.importorskip("covsight.core.ncdb.testplan")
    app.build()
    plan = plan_of(app)
    loaded = testplan.Testplan.from_dict(plan)
    assert loaded.name == "uart"
    names = {tp.name for tp in testplan.iter_testpoints(loaded)}
    assert names == {tp["name"] for tp in iter_testpoints(plan)}
    start_bit = loaded.getTestpoint("FEAT-001.tp_start_bit")
    assert start_bit.stage == "V1"
    assert [b.path for b in start_bit.coverage] == [
        "uart_env.uart_cfg_cg",
        "uart_env.uart_cfg_cg.parity_cp",
    ]
