"""``covsight-testplan`` build / check / show."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
import yaml

from sphinx_covsight.cli import diff_plans, main


@pytest.fixture
def srcdir(rootdir, tmp_path) -> Path:
    target = tmp_path / "plan"
    shutil.copytree(rootdir / "test-basic", target)
    return target


def test_build_writes_json(srcdir, tmp_path, capsys):
    output = tmp_path / "testplan.json"
    assert main(["build", str(srcdir), "-o", str(output)]) == 0
    plan = json.loads(output.read_text(encoding="utf-8"))
    assert plan["name"] == "uart"
    assert "wrote" in capsys.readouterr().out


def test_build_writes_both_formats(srcdir, tmp_path):
    output = tmp_path / "testplan.json"
    assert main(["build", str(srcdir), "-o", str(output), "-f", "both"]) == 0
    assert yaml.safe_load(output.with_suffix(".yaml").read_text(encoding="utf-8")) == json.loads(
        output.read_text(encoding="utf-8")
    )


def test_build_output_has_no_provenance_fields(srcdir, tmp_path):
    output = tmp_path / "testplan.json"
    main(["build", str(srcdir), "-o", str(output)])
    assert not output.with_suffix(".provenance.json").exists()


def test_check_exits_zero_when_up_to_date(srcdir, tmp_path, capsys):
    output = tmp_path / "testplan.json"
    main(["build", str(srcdir), "-o", str(output)])
    capsys.readouterr()
    assert main(["check", str(srcdir), "--against", str(output)]) == 0
    assert "up to date" in capsys.readouterr().out


def test_check_exits_one_on_drift_with_a_readable_diff(srcdir, tmp_path, capsys):
    output = tmp_path / "testplan.json"
    main(["build", str(srcdir), "-o", str(output)])
    capsys.readouterr()

    index = srcdir / "index.rst"
    index.write_text(
        index.read_text(encoding="utf-8").replace("uart_smoke_test", "uart_sanity_test"),
        encoding="utf-8",
    )
    assert main(["check", str(srcdir), "--against", str(output)]) == 1
    err = capsys.readouterr().err
    assert "1 difference(s)" in err
    assert "'uart_smoke_test' -> 'uart_sanity_test'" in err


def test_check_reports_a_missing_reference(tmp_path, srcdir, capsys):
    assert main(["check", str(srcdir), "--against", str(tmp_path / "nope.json")]) == 2
    assert "does not exist" in capsys.readouterr().err


def test_show_summary(srcdir, capsys):
    assert main(["show", str(srcdir), "--summary"]) == 0
    out = capsys.readouterr().out
    assert "plan:         uart" in out
    assert "testpoints:   3" in out
    assert "citations:" in out


def test_show_prints_the_plan(srcdir, capsys):
    assert main(["show", str(srcdir)]) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["format_version"] == 1


def test_build_is_deterministic_across_invocations(srcdir, tmp_path):
    first = tmp_path / "a.json"
    second = tmp_path / "b.json"
    main(["build", str(srcdir), "-o", str(first)])
    main(["build", str(srcdir), "-o", str(second)])
    assert first.read_bytes() == second.read_bytes()


# ── the structural diff ───────────────────────────────────────────────────────


def test_diff_reports_added_removed_and_changed():
    expected = {"a": 1, "b": [1, 2], "c": {"d": "x"}}
    actual = {"a": 2, "b": [1], "e": True, "c": {"d": "x"}}
    assert sorted(diff_plans(expected, actual)) == sorted(
        [
            "a: 1 -> 2",
            "b[1]: removed (2)",
            "e: added (True)",
        ]
    )


def test_diff_names_goals_and_testpoints_helpfully():
    expected = {"goals": [{"id": "FEAT-1"}, {"id": "FEAT-2"}]}
    actual = {"goals": [{"id": "FEAT-1"}]}
    assert diff_plans(expected, actual) == ["goals[1]: removed ({id='FEAT-2'})"]


def test_diff_of_identical_plans_is_empty():
    plan = {"goals": [{"id": "FEAT-1", "testpoints": [{"name": "tp"}]}]}
    assert diff_plans(plan, json.loads(json.dumps(plan))) == []
