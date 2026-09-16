"""Model -> covsight testplan v1.

The ordering rules here *are* the determinism guarantee:

1. goals ordered by ``(document order, order within document)``;
2. testpoints ordered the same way within their enclosing goal;
3. ``requirements[]``, ``coverage[]`` and ``tags[]`` sorted lexically — these
   are sets, not sequences, so authoring order carries no meaning and sorting
   removes a diff source;
4. ``tests[]`` keeps authored order after substitution expansion, and the
   expansion is cartesian over sorted substitution keys;
5. every dict key is sorted at emit time.
"""

from __future__ import annotations

import itertools
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from .model import (
    Citation,
    CoverageBinding,
    EnvRecord,
    FeatureRecord,
    PlanStore,
    TestpointRecord,
)
from .policy import EnvPolicy, ScoreExpression

SCHEMA_URI = "https://schema.covsight.io/testplan/v1"
FORMAT_VERSION = 1

_PLACEHOLDER_RE = re.compile(r"\{([A-Za-z0-9_]+)\}")


@dataclass
class ExtractOptions:
    """Everything extraction needs from ``conf.py``."""

    plan_name: str = ""
    description: str = ""
    owner: str = ""
    tags: Sequence[str] = ()
    substitutions: Mapping[str, Sequence[str]] = field(default_factory=dict)
    policy: Mapping[str, EnvPolicy] = field(default_factory=dict)
    score: ScoreExpression | None = None
    env_in_custom: bool = True
    document_order: Mapping[str, int] = field(default_factory=dict)


@dataclass
class ExtractResult:
    plan: dict[str, Any]
    unknown_substitutions: dict[str, list[str]] = field(default_factory=dict)


def extract(store: PlanStore, options: ExtractOptions) -> ExtractResult:
    """Build the testplan dict from *store*."""
    result = ExtractResult(plan={})
    sort_key = _record_sort_key(options.document_order)

    features = sorted(store.all_features(), key=sort_key)
    envs = sorted(store.all_envs(), key=sort_key)
    testpoints = sorted(store.all_testpoints(), key=sort_key)

    children: dict[str | None, list[FeatureRecord]] = {}
    for feature in features:
        children.setdefault(feature.parent_id, []).append(feature)
    # A feature whose declared parent does not exist is still emitted, at the
    # root, rather than silently dropped.
    known_ids = {feature.id for feature in features}
    roots = list(children.get(None, []))
    for parent_id, group in children.items():
        if parent_id is not None and parent_id not in known_ids:
            roots.extend(group)
    roots.sort(key=sort_key)

    envs_by_feature: dict[str, list[EnvRecord]] = {}
    for env_record in envs:
        envs_by_feature.setdefault(env_record.feature_id, []).append(env_record)

    tps_by_feature: dict[str, list[TestpointRecord]] = {}
    for tp in testpoints:
        tps_by_feature.setdefault(tp.feature_id, []).append(tp)

    goals = [
        _feature_goal(
            feature,
            options=options,
            result=result,
            children=children,
            envs_by_feature=envs_by_feature,
            tps_by_feature=tps_by_feature,
            sort_key=sort_key,
        )
        for feature in roots
    ]

    plan: dict[str, Any] = {
        "schema": SCHEMA_URI,
        "format_version": FORMAT_VERSION,
        "imports": [],
        "goals": goals,
    }
    if options.plan_name:
        plan["name"] = options.plan_name
    if options.description:
        plan["description"] = options.description
    if options.owner:
        plan["owner"] = options.owner
    if options.tags:
        plan["tags"] = sorted(set(options.tags))
    if options.substitutions:
        plan["substitutions"] = {
            key: list(values) for key, values in sorted(options.substitutions.items())
        }
    result.plan = plan
    return result


# ── goals ─────────────────────────────────────────────────────────────────────


def _record_sort_key(document_order: Mapping[str, int]):
    def key(record: Any) -> tuple[int, str, int]:
        docname = record.docname
        return (document_order.get(docname, len(document_order)), docname, record.order)

    return key


def _feature_goal(
    feature: FeatureRecord,
    *,
    options: ExtractOptions,
    result: ExtractResult,
    children: Mapping[str | None, list[FeatureRecord]],
    envs_by_feature: Mapping[str, list[EnvRecord]],
    tps_by_feature: Mapping[str, list[TestpointRecord]],
    sort_key: Any,
) -> dict[str, Any]:
    feature_tps = tps_by_feature.get(feature.id, [])
    direct_tps = [tp for tp in feature_tps if tp.env is None]

    # Children of a feature — nested features and env goals — are interleaved
    # in document order, because that is the order the reader met them in.
    sub_goals: list[tuple[tuple[int, str, int], dict[str, Any]]] = []
    for env_record in envs_by_feature.get(feature.id, []):
        sub_goals.append(
            (
                sort_key(env_record),
                _env_goal(env_record, feature, feature_tps, options, result),
            )
        )
    for child in sorted(children.get(feature.id, []), key=sort_key):
        sub_goals.append(
            (
                sort_key(child),
                _feature_goal(
                    child,
                    options=options,
                    result=result,
                    children=children,
                    envs_by_feature=envs_by_feature,
                    tps_by_feature=tps_by_feature,
                    sort_key=sort_key,
                ),
            )
        )
    sub_goals.sort(key=lambda item: item[0])

    goal: dict[str, Any] = {"id": feature.id, "title": feature.title}
    if feature.desc:
        goal["desc"] = feature.desc
    if feature.owner:
        goal["owner"] = feature.owner
    if feature.tags:
        goal["tags"] = sorted(set(feature.tags))
    status = feature.status
    if not status and not feature_tps:
        # No testpoints anywhere beneath: the feature is planned, not covered.
        status = "planned"
    if status:
        goal["status"] = status
    if sub_goals:
        goal["goals"] = [entry for _key, entry in sub_goals]
    if direct_tps:
        goal["testpoints"] = [_testpoint(tp, options, result) for tp in direct_tps]
    custom = _feature_custom(feature)
    if custom:
        goal["custom"] = custom
    return goal


def _feature_custom(feature: FeatureRecord) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    requirements = _requirements(feature.citations)
    if requirements:
        payload["requirements"] = requirements
    return {"covsight": payload} if payload else {}


def _env_goal(
    env_record: EnvRecord,
    feature: FeatureRecord,
    feature_tps: Sequence[TestpointRecord],
    options: ExtractOptions,
    result: ExtractResult,
) -> dict[str, Any]:
    policy = options.policy.get(env_record.env, EnvPolicy())
    rendered = policy.rendered(feature=feature.title, env=env_record.env)

    goal: dict[str, Any] = {
        "id": f"{feature.id}.{env_record.env}",
        "title": env_record.title or rendered.title or env_record.env,
    }
    if env_record.desc:
        goal["desc"] = env_record.desc

    custom: dict[str, Any] = {"env": env_record.env}
    if env_record.scope:
        custom["scope"] = env_record.scope
    if env_record.difficulty is not None:
        custom["difficulty"] = env_record.difficulty
    if env_record.coverage_score is not None:
        custom["coverage_score"] = env_record.coverage_score
    if (
        options.score is not None
        and env_record.difficulty is not None
        and env_record.coverage_score is not None
    ):
        custom["overall_score"] = options.score(
            difficulty=env_record.difficulty, coverage=env_record.coverage_score
        )
    if rendered.approach:
        custom["approach"] = rendered.approach
    if rendered.reasoning:
        custom["reasoning"] = rendered.reasoning
    if rendered.exit_criteria:
        custom["exit_criteria"] = list(rendered.exit_criteria)
    goal["custom"] = {"covsight": custom}

    env_tps = [tp for tp in feature_tps if tp.env == env_record.env]
    if env_tps:
        goal["testpoints"] = [_testpoint(tp, options, result) for tp in env_tps]
    else:
        goal["status"] = "planned"
    return goal


# ── testpoints ────────────────────────────────────────────────────────────────


def _testpoint(
    tp: TestpointRecord, options: ExtractOptions, result: ExtractResult
) -> dict[str, Any]:
    tests, unknown = expand_tests(tp.tests, options.substitutions)
    if unknown:
        result.unknown_substitutions.setdefault(f"{tp.docname}:{tp.lineno}", []).extend(
            sorted(unknown)
        )

    entry: dict[str, Any] = {"name": tp.id, "stage": tp.stage or ""}
    if tp.desc:
        entry["desc"] = tp.desc
    if tests:
        entry["tests"] = tests
    if tp.tests and tests != tp.tests:
        entry["source_template"] = ", ".join(tp.tests)
    if tp.na or not tp.tests:
        entry["na"] = True
    if tp.tags:
        entry["tags"] = sorted(set(tp.tags))
    if tp.priority:
        entry["priority"] = tp.priority
    if tp.weight != 1:
        entry["weight"] = tp.weight
    if tp.owner:
        entry["owner"] = tp.owner

    requirements = _requirements(tp.citations)
    if requirements:
        entry["requirements"] = requirements
    coverage = _coverage(tp.coverage)
    if coverage:
        entry["coverage"] = coverage

    custom: dict[str, Any] = {"title": tp.title, "feature": tp.feature_id}
    if tp.env is not None:
        if options.env_in_custom:
            custom["env"] = tp.env
        else:
            entry["env"] = tp.env
    entry["custom"] = {"covsight": custom}
    return entry


def _requirements(citations: Iterable[Citation]) -> list[dict[str, Any]]:
    seen: dict[tuple[str, str], dict[str, Any]] = {}
    for citation in citations:
        key = (citation.system, citation.target)
        entry: dict[str, Any] = {"system": citation.system, "item_id": citation.target}
        if citation.url:
            entry["url"] = citation.url
        # A later duplicate with a URL wins over an earlier one without.
        if key not in seen or ("url" in entry and "url" not in seen[key]):
            seen[key] = entry
    return [seen[key] for key in sorted(seen)]


def _coverage(bindings: Iterable[CoverageBinding]) -> list[dict[str, Any]]:
    seen: dict[tuple[str, str], dict[str, Any]] = {}
    for binding in bindings:
        entry: dict[str, Any] = {"type": binding.type, "path": binding.path}
        if binding.desc:
            entry["desc"] = binding.desc
        seen.setdefault((binding.type, binding.path), entry)
    return [seen[key] for key in sorted(seen)]


# ── substitution expansion ────────────────────────────────────────────────────


def _substitute(name: str, mapping: Mapping[str, str]) -> str:
    return _PLACEHOLDER_RE.sub(lambda m: str(mapping.get(m.group(1), m.group(0))), name)


def expand_tests(
    names: Sequence[str], substitutions: Mapping[str, Sequence[str]]
) -> tuple[list[str], set[str]]:
    """Expand ``{key}`` placeholders cartesian-wise over sorted keys.

    Returns the expanded names in authored order plus the set of placeholders
    that had no binding (those names are kept verbatim so nothing is lost).
    """
    expanded: list[str] = []
    unknown: set[str] = set()
    for name in names:
        keys = sorted({m.group(1) for m in _PLACEHOLDER_RE.finditer(name)})
        bound = [key for key in keys if key in substitutions]
        unknown.update(key for key in keys if key not in substitutions)
        if not bound:
            expanded.append(name)
            continue
        value_lists = [list(substitutions[key]) for key in bound]
        for combination in itertools.product(*value_lists):
            mapping = dict(zip(bound, combination, strict=True))
            expanded.append(_substitute(name, mapping))
    return expanded, unknown
