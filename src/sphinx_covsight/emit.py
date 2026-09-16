"""Deterministic writers for the plan and its provenance sidecar.

One rule makes SHA-binding viable: **no timestamp, path, hostname, or version
goes into the hashed artifact**.  All of it lives in the sidecar.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


def dumps_json(plan: Mapping[str, Any]) -> str:
    return json.dumps(plan, sort_keys=True, ensure_ascii=False, indent=2) + "\n"


def dumps_yaml(plan: Mapping[str, Any]) -> str:
    return yaml.safe_dump(
        json.loads(json.dumps(plan)),  # plain types only
        sort_keys=True,
        default_flow_style=False,
        allow_unicode=True,
    )


def write_json(path: str | Path, plan: Mapping[str, Any]) -> Path:
    return _write(path, dumps_json(plan))


def write_yaml(path: str | Path, plan: Mapping[str, Any]) -> Path:
    return _write(path, dumps_yaml(plan))


def _write(path: str | Path, text: str) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    # newline="\n" keeps the artifact byte-identical on Windows.
    with open(target, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    return target


def plan_sha256(plan: Mapping[str, Any]) -> str:
    return hashlib.sha256(dumps_json(plan).encode("utf-8")).hexdigest()


def source_commit(srcdir: str | Path) -> str | None:
    """``git rev-parse HEAD`` for *srcdir*, or ``None`` outside a repository."""
    try:
        result = subprocess.run(
            ["git", "-C", str(srcdir), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):  # pragma: no cover - platform dependent
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def provenance(
    *,
    plan: Mapping[str, Any],
    srcdir: str | Path,
    version: str,
    policy_sha256: str,
    score_expression: str,
    needs_json_sha256: str | None,
    citation_backends: Mapping[str, bool],
    counts: Mapping[str, int],
    generated_at: str | None = None,
) -> dict[str, Any]:
    return {
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "source_commit": source_commit(srcdir),
        "sphinx_covsight_version": version,
        "policy_sha256": policy_sha256,
        "score_expression": score_expression,
        "needs_json_sha256": needs_json_sha256,
        "citation_backends": dict(sorted(citation_backends.items())),
        "counts": dict(sorted(counts.items())),
        "testplan_sha256": plan_sha256(plan),
    }


def write_provenance(path: str | Path, payload: Mapping[str, Any]) -> Path:
    return _write(path, json.dumps(payload, sort_keys=True, indent=2) + "\n")


def count_plan(plan: Mapping[str, Any]) -> dict[str, int]:
    """Counts for the provenance sidecar and ``covsight-testplan show``."""
    counts = {"goals": 0, "testpoints": 0, "requirements": 0, "coverage": 0, "tests": 0}

    def walk(goals: Any) -> None:
        for goal in goals or []:
            counts["goals"] += 1
            for tp in goal.get("testpoints", []):
                _count_testpoint(tp, counts)
            walk(goal.get("goals"))

    for tp in plan.get("testpoints", []):
        _count_testpoint(tp, counts)
    walk(plan.get("goals"))
    return counts


def _count_testpoint(tp: Mapping[str, Any], counts: dict[str, int]) -> None:
    counts["testpoints"] += 1
    counts["requirements"] += len(tp.get("requirements", []))
    counts["coverage"] += len(tp.get("coverage", []))
    counts["tests"] += len(tp.get("tests", []))
