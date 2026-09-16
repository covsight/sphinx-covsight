"""Shared pytest fixtures.

``sphinx.testing`` is used rather than hand-rolled builds because it gives
warning capture and incremental-build control for free — and the incremental
behaviour is exactly where this extension is most likely to go quietly wrong.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

pytest_plugins = ["sphinx.testing.fixtures"]

TESTS_DIR = Path(__file__).parent.resolve()

# sphinx-covsight declares no dependency on covsight-core (D6.4).  The
# round-trip test is the one place that wants it, and it skips when absent — but
# when a checkout happens to sit next to this one, use it.
_COVSIGHT_CORE = TESTS_DIR.parents[1] / "covsight-core" / "python"
if _COVSIGHT_CORE.is_dir() and str(_COVSIGHT_CORE) not in sys.path:
    sys.path.append(str(_COVSIGHT_CORE))


@pytest.fixture(scope="session")
def rootdir() -> Path:
    return TESTS_DIR / "roots"


@pytest.fixture
def plan_of():
    """Return the plan a built app wrote, parsed."""

    def _plan_of(app: Any) -> dict:
        path = Path(app.outdir) / "testplan.json"
        assert path.is_file(), f"no testplan written to {path}"
        return json.loads(path.read_text(encoding="utf-8"))

    return _plan_of


def warnings_of(app: Any, warning: Any) -> list[str]:
    """Warning lines emitted by a build, with the temp path stripped."""
    text = warning.getvalue()
    return [line for line in text.splitlines() if line.strip()]


def find_testpoint(plan: dict, name: str) -> dict:
    for tp in iter_testpoints(plan):
        if tp["name"] == name:
            return tp
    have = [t["name"] for t in iter_testpoints(plan)]
    raise AssertionError(f"testpoint {name!r} not in plan; have {have}")


def iter_testpoints(plan: dict):
    yield from plan.get("testpoints", [])

    def walk(goals):
        for goal in goals or []:
            yield from goal.get("testpoints", [])
            yield from walk(goal.get("goals"))

    yield from walk(plan.get("goals"))


def find_goal(plan: dict, goal_id: str) -> dict:
    def walk(goals):
        for goal in goals or []:
            if goal["id"] == goal_id:
                return goal
            found = walk(goal.get("goals"))
            if found is not None:
                return found
        return None

    goal = walk(plan.get("goals"))
    assert goal is not None, f"goal {goal_id!r} not in plan"
    return goal
