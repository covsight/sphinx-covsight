"""``covsight-testplan`` — extract a plan without a documentation build step.

``check`` is the CI gate: it re-extracts and compares against the committed
plan, so "someone edited the artifact without regenerating it" and "the build
stopped being deterministic" both fail loudly.  It diffs parsed JSON rather
than bytes, because a byte diff on a 400-testpoint plan is unreadable.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .emit import count_plan, dumps_json, write_json, write_yaml


def _build_plan(
    srcdir: Path,
    *,
    confdir: Path | None = None,
    warningiserror: bool = False,
    quiet: bool = True,
) -> dict[str, Any]:
    """Run a Sphinx build over *srcdir* and return the extracted plan."""
    from sphinx.application import Sphinx

    with tempfile.TemporaryDirectory(prefix="covsight-testplan-") as tmp:
        tmpdir = Path(tmp)
        outdir = tmpdir / "out"
        doctreedir = tmpdir / "doctrees"
        target = outdir / "testplan.json"
        app = Sphinx(
            srcdir=str(srcdir),
            confdir=str(confdir or srcdir),
            outdir=str(outdir),
            doctreedir=str(doctreedir),
            buildername="dummy",
            confoverrides={
                "covsight_output": str(target),
                "covsight_output_format": "json",
                "covsight_provenance": False,
            },
            status=None if quiet else sys.stdout,
            warning=sys.stderr,
            freshenv=True,
            warningiserror=warningiserror,
        )
        app.build()
        if not target.is_file():
            raise SystemExit(
                f"error: no testplan was written; is sphinx_covsight in {srcdir}/conf.py "
                "extensions?"
            )
        return json.loads(target.read_text(encoding="utf-8"))


# ── structural diff ───────────────────────────────────────────────────────────


def diff_plans(expected: Any, actual: Any, path: str = "") -> list[str]:
    """Human-readable structural differences between two parsed plans."""
    where = path or "<plan>"
    if type(expected) is not type(actual) and not (
        isinstance(expected, (int, float)) and isinstance(actual, (int, float))
    ):
        return [f"{where}: type {type(expected).__name__} -> {type(actual).__name__}"]
    if isinstance(expected, dict):
        differences: list[str] = []
        for key in sorted(set(expected) | set(actual)):
            child = f"{path}.{key}" if path else key
            if key not in actual:
                differences.append(f"{child}: removed ({_brief(expected[key])})")
            elif key not in expected:
                differences.append(f"{child}: added ({_brief(actual[key])})")
            else:
                differences.extend(diff_plans(expected[key], actual[key], child))
        return differences
    if isinstance(expected, list):
        differences = []
        for index in range(max(len(expected), len(actual))):
            child = f"{path}[{index}]"
            if index >= len(actual):
                differences.append(f"{child}: removed ({_brief(expected[index])})")
            elif index >= len(expected):
                differences.append(f"{child}: added ({_brief(actual[index])})")
            else:
                differences.extend(diff_plans(expected[index], actual[index], child))
        return differences
    if expected != actual:
        return [f"{where}: {_brief(expected)} -> {_brief(actual)}"]
    return []


def _brief(value: Any) -> str:
    if isinstance(value, dict):
        for key in ("id", "name"):
            if key in value:
                return f"{{{key}={value[key]!r}}}"
        return "{...}"
    if isinstance(value, list):
        return f"[{len(value)} item(s)]"
    text = repr(value)
    return text if len(text) <= 60 else text[:57] + "..."


# ── commands ──────────────────────────────────────────────────────────────────


def cmd_build(args: argparse.Namespace) -> int:
    plan = _build_plan(
        Path(args.srcdir), confdir=args.confdir, warningiserror=args.strict, quiet=not args.verbose
    )
    output = Path(args.output)
    if args.format in ("json", "both"):
        write_json(output, plan)
        print(f"wrote {output}")
    if args.format in ("yaml", "both"):
        yaml_path = output.with_suffix(".yaml")
        write_yaml(yaml_path, plan)
        print(f"wrote {yaml_path}")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    reference_path = Path(args.against)
    if not reference_path.is_file():
        print(f"error: {reference_path} does not exist", file=sys.stderr)
        return 2
    reference = json.loads(reference_path.read_text(encoding="utf-8"))
    plan = _build_plan(
        Path(args.srcdir), confdir=args.confdir, warningiserror=args.strict, quiet=not args.verbose
    )
    differences = diff_plans(reference, plan)
    if not differences:
        print(f"{reference_path}: up to date")
        return 0
    print(f"{reference_path}: {len(differences)} difference(s)", file=sys.stderr)
    for line in differences:
        print(f"  {line}", file=sys.stderr)
    return 1


def cmd_show(args: argparse.Namespace) -> int:
    plan = _build_plan(
        Path(args.srcdir), confdir=args.confdir, warningiserror=False, quiet=not args.verbose
    )
    if not args.summary:
        print(dumps_json(plan), end="")
        return 0
    counts = count_plan(plan)
    resolved = 0
    total = 0
    for tp in _iter_testpoints(plan):
        for requirement in tp.get("requirements", []):
            total += 1
            resolved += 1 if requirement.get("url") else 0
    print(f"plan:         {plan.get('name') or '<unnamed>'}")
    for key in sorted(counts):
        print(f"{key + ':':<13} {counts[key]}")
    if total:
        print(f"{'citations:':<13} {resolved}/{total} resolved")
    return 0


def _iter_testpoints(plan: Any) -> Any:
    yield from plan.get("testpoints", [])

    def walk(goals: Any) -> Any:
        for goal in goals or []:
            yield from goal.get("testpoints", [])
            yield from walk(goal.get("goals"))

    yield from walk(plan.get("goals"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="covsight-testplan",
        description="Extract a covsight testplan from a Sphinx documentation source tree.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_common(sub: argparse.ArgumentParser) -> None:
        sub.add_argument("srcdir", help="Sphinx source directory (the one with conf.py)")
        sub.add_argument("-c", "--confdir", type=Path, default=None, help="conf.py directory")
        sub.add_argument(
            "-W", "--strict", action="store_true", help="turn build warnings into errors"
        )
        sub.add_argument("-v", "--verbose", action="store_true", help="show the Sphinx build log")

    build = subparsers.add_parser("build", help="extract and write the plan")
    add_common(build)
    build.add_argument("-o", "--output", default="testplan.json", help="output file")
    build.add_argument("-f", "--format", choices=("json", "yaml", "both"), default="json")
    build.set_defaults(func=cmd_build)

    check = subparsers.add_parser("check", help="compare a re-extraction against a committed plan")
    add_common(check)
    check.add_argument("--against", required=True, help="the committed plan to compare against")
    check.set_defaults(func=cmd_check)

    show = subparsers.add_parser("show", help="print the plan or a summary of it")
    add_common(show)
    show.add_argument("--summary", action="store_true", help="counts instead of the full plan")
    show.set_defaults(func=cmd_show)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
