"""Build-time validations, run before emission.

Every check is a warning with a stable subtype, so a project can silence a
class of message with ``suppress_warnings``.  The one exception is the D1
invariant, which indicates a bug in this extension rather than in the document.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

from . import logging as cslog
from .citations import NEEDS_ID_RE
from .extract import ExtractResult
from .model import PlanStore


def run_checks(
    store: PlanStore,
    result: ExtractResult,
    *,
    policy: Mapping[str, Any],
    env_in_custom: bool,
    require_explicit_testpoint_ids: bool = False,
) -> None:
    _check_duplicate_feature_ids(store)
    _check_duplicate_testpoint_ids(store)
    _check_unmapped_testpoints(store)
    _check_explicit_testpoint_ids(store, require_explicit_testpoint_ids)
    _check_empty_goals(store)
    _check_substitutions(result)
    _check_policy_coverage(store, policy)
    _check_citation_charset(store)
    check_env_denormalization(result.plan, env_in_custom=env_in_custom)


def _location(record: Any) -> tuple[str, int]:
    return (record.docname, record.lineno)


def _check_duplicate_feature_ids(store: PlanStore) -> None:
    seen: dict[str, Any] = {}
    for feature in store.all_features():
        first = seen.get(feature.id)
        if first is not None:
            cslog.warn(
                "duplicate-id",
                f"duplicate feature id {feature.id!r}; first declared at "
                f"{first.docname}:{first.lineno}",
                location=_location(feature),
            )
        else:
            seen[feature.id] = feature


def _check_duplicate_testpoint_ids(store: PlanStore) -> None:
    seen: dict[str, Any] = {}
    for tp in store.all_testpoints():
        first = seen.get(tp.id)
        if first is not None:
            cslog.warn(
                "duplicate-id",
                f"duplicate testpoint id {tp.id!r}; first declared at "
                f"{first.docname}:{first.lineno}",
                location=_location(tp),
            )
        else:
            seen[tp.id] = tp


def _check_unmapped_testpoints(store: PlanStore) -> None:
    for tp in store.all_testpoints():
        if not tp.tests and not tp.na:
            cslog.warn(
                "testpoint-unmapped",
                f"testpoint {tp.id!r} has no '.. tests::' and is not marked ':na:'",
                location=_location(tp),
            )


def _check_explicit_testpoint_ids(store: PlanStore, required: bool) -> None:
    if not required:
        return
    for tp in store.all_testpoints():
        if not tp.explicit_id:
            cslog.warn(
                "duplicate-id",
                f"testpoint {tp.title!r} has no ':id:' and "
                "covsight_require_explicit_testpoint_ids is set",
                location=_location(tp),
            )


def _check_empty_goals(store: PlanStore) -> None:
    envs_by_feature: dict[str, list[Any]] = defaultdict(list)
    for env_record in store.all_envs():
        envs_by_feature[env_record.feature_id].append(env_record)
    tps_by_feature: dict[str, list[Any]] = defaultdict(list)
    for tp in store.all_testpoints():
        tps_by_feature[tp.feature_id].append(tp)

    parents = {feature.parent_id for feature in store.all_features()}
    for feature in store.all_features():
        if feature.id in parents:
            continue  # a feature whose children carry the content
        if not envs_by_feature[feature.id] and not tps_by_feature[feature.id]:
            cslog.warn(
                "empty-goal",
                f"feature {feature.id!r} has no environments and no testpoints",
                location=_location(feature),
            )
    for env_record in store.all_envs():
        if not any(tp.env == env_record.env for tp in tps_by_feature[env_record.feature_id]):
            cslog.warn(
                "empty-goal",
                f"environment {env_record.env!r} of feature "
                f"{env_record.feature_id!r} has no testpoints",
                location=_location(env_record),
            )


def _check_substitutions(result: ExtractResult) -> None:
    for where, keys in sorted(result.unknown_substitutions.items()):
        docname, _, lineno = where.rpartition(":")
        cslog.warn(
            "substitution",
            "no substitution binding for " + ", ".join(f"{{{k}}}" for k in sorted(set(keys))),
            location=(docname, int(lineno)),
        )


def _check_policy_coverage(store: PlanStore, policy: Mapping[str, Any]) -> None:
    reported: set[str] = set()
    for env_record in store.all_envs():
        if env_record.env in policy or env_record.env in reported:
            continue
        reported.add(env_record.env)
        cslog.warn(
            "missing-policy",
            f"no covsight_env_policy entry for environment {env_record.env!r}",
            location=_location(env_record),
        )


def _check_citation_charset(store: PlanStore) -> None:
    for citation in store.all_citations():
        if citation.kind != "rule":
            continue
        if not NEEDS_ID_RE.match(citation.target):
            cslog.warn(
                "citation-id-charset",
                f"rule id {citation.target!r} contains characters outside [A-Za-z0-9_]; "
                "sphinx-needs cross-references will not resolve such ids",
                location=(citation.docname, citation.lineno),
            )


def check_env_denormalization(plan: Mapping[str, Any], *, env_in_custom: bool) -> list[str]:
    """The D1 invariant: ``testpoint.env`` equals its nearest enclosing env goal.

    ``env`` is emitted twice on purpose — the goal tree is the canonical
    structure, the field is a denormalized index — so something has to hold the
    two in agreement.  A violation is an extension bug, not an authoring error.
    """
    problems: list[str] = []

    def testpoint_env(tp: Mapping[str, Any]) -> str | None:
        if env_in_custom:
            return tp.get("custom", {}).get("covsight", {}).get("env")
        return tp.get("env")

    def walk(goals: Sequence[Mapping[str, Any]], enclosing: str | None) -> None:
        for goal in goals:
            goal_env = goal.get("custom", {}).get("covsight", {}).get("env", enclosing)
            for tp in goal.get("testpoints", []):
                actual = testpoint_env(tp)
                if actual != goal_env:
                    problems.append(
                        f"testpoint {tp.get('name')!r}: env {actual!r} does not match "
                        f"enclosing goal env {goal_env!r}"
                    )
            walk(goal.get("goals", []), goal_env)

    for tp in plan.get("testpoints", []):
        if testpoint_env(tp) is not None:
            problems.append(
                f"testpoint {tp.get('name')!r} carries an env but has no enclosing env goal"
            )
    walk(plan.get("goals", []), None)

    for problem in problems:
        cslog.warn("internal", "env denormalization invariant violated: " + problem)
    return problems
