"""Environment policy and the score expression (decision D5).

Policy is *data*, not code: it is either an inline dict in ``conf.py`` or a YAML
file, and either way it is canonicalized and hashed so the provenance sidecar
can record which policy produced the derived scores.  The score itself is a
restricted arithmetic expression string rather than a lambda, for the same
reason — a lambda cannot be hashed stably or serialised.
"""

from __future__ import annotations

import ast
import hashlib
import json
import math
import operator
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from sphinx.errors import ConfigError

#: Placeholders accepted in ``approach`` / ``reasoning``.
PLACEHOLDERS = ("feature", "env")

_PLACEHOLDER_RE = re.compile(r"\{([^{}]*)\}")

DEFAULT_SCORE_EXPRESSION = "(11 - difficulty) * coverage"

#: Variables the score expression may reference.
SCORE_VARIABLES = ("difficulty", "coverage")


@dataclass
class EnvPolicy:
    """Policy for one verification environment."""

    title: str = ""
    approach: str = ""
    reasoning: str = ""
    exit_criteria: list[str] = field(default_factory=list)

    def rendered(self, *, feature: str, env: str) -> EnvPolicy:
        """Return a copy with ``{feature}`` / ``{env}`` interpolated."""
        subs = {"feature": feature, "env": env}
        return EnvPolicy(
            title=self.title,
            approach=_interpolate(self.approach, subs),
            reasoning=_interpolate(self.reasoning, subs),
            exit_criteria=list(self.exit_criteria),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "approach": self.approach,
            "reasoning": self.reasoning,
            "exit_criteria": list(self.exit_criteria),
        }


def _interpolate(text: str, subs: Mapping[str, str]) -> str:
    return _PLACEHOLDER_RE.sub(lambda m: subs.get(m.group(1), m.group(0)), text)


def _check_placeholders(where: str, text: str) -> None:
    for match in _PLACEHOLDER_RE.finditer(text):
        name = match.group(1)
        if name not in PLACEHOLDERS:
            raise ConfigError(
                f"covsight_env_policy: unknown placeholder {{{name}}} in {where}; "
                f"known placeholders are {', '.join('{' + p + '}' for p in PLACEHOLDERS)}"
            )


def _policy_from_mapping(env: str, raw: Mapping[str, Any]) -> EnvPolicy:
    unknown = set(raw) - {"title", "approach", "reasoning", "exit_criteria"}
    if unknown:
        raise ConfigError(
            f"covsight_env_policy['{env}']: unknown key(s) {', '.join(sorted(unknown))}"
        )
    criteria = raw.get("exit_criteria", []) or []
    if isinstance(criteria, str):
        criteria = [criteria]
    policy = EnvPolicy(
        title=str(raw.get("title", "") or ""),
        approach=str(raw.get("approach", "") or ""),
        reasoning=str(raw.get("reasoning", "") or ""),
        exit_criteria=[str(c) for c in criteria],
    )
    _check_placeholders(f"covsight_env_policy['{env}'].approach", policy.approach)
    _check_placeholders(f"covsight_env_policy['{env}'].reasoning", policy.reasoning)
    return policy


def load_policy(
    inline: Mapping[str, Any] | None,
    policy_file: str | None,
    confdir: str | Path,
) -> dict[str, EnvPolicy]:
    """Load the env policy from the inline config or from a YAML file.

    The two forms are interchangeable and produce identical fingerprints for
    identical content.
    """
    raw: Mapping[str, Any]
    if policy_file:
        path = Path(confdir) / policy_file
        if not path.is_file():
            raise ConfigError(f"covsight_env_policy_file not found: {path}")
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(loaded, dict):
            raise ConfigError(f"covsight_env_policy_file must contain a mapping: {path}")
        if inline:
            raise ConfigError(
                "covsight_env_policy and covsight_env_policy_file are mutually exclusive"
            )
        raw = loaded
    else:
        raw = inline or {}

    policy: dict[str, EnvPolicy] = {}
    for env, entry in raw.items():
        if not isinstance(entry, Mapping):
            raise ConfigError(f"covsight_env_policy['{env}'] must be a mapping")
        policy[str(env)] = _policy_from_mapping(str(env), entry)
    return policy


def policy_as_dict(policy: Mapping[str, EnvPolicy]) -> dict[str, Any]:
    return {env: policy[env].as_dict() for env in sorted(policy)}


def policy_fingerprint(policy: Mapping[str, EnvPolicy], score_expression: str) -> str:
    """sha256 over canonical JSON of the policy plus the score expression."""
    payload = {
        "policy": policy_as_dict(policy),
        "score_expression": score_expression,
    }
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ── the score expression sandbox ──────────────────────────────────────────────

_BIN_OPS: dict[type[ast.AST], Callable[[Any, Any], Any]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_UNARY_OPS: dict[type[ast.AST], Callable[[Any], Any]] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


class ScoreExpression:
    """A restricted arithmetic expression over ``difficulty`` and ``coverage``.

    Only literals, whitelisted names, ``+ - * / // % **``, unary sign, and
    parentheses are permitted.  Calls, attribute access, subscripts,
    comprehensions and the walrus operator are rejected at compile time — this
    expression comes from a ``conf.py`` that CI builds from arbitrary branches,
    so ``eval`` of the raw string would be a real vulnerability rather than a
    theoretical one.
    """

    def __init__(self, expression: str, variables: tuple[str, ...] = SCORE_VARIABLES) -> None:
        self.expression = expression
        self.variables = variables
        try:
            tree = ast.parse(expression, mode="eval")
        except SyntaxError as exc:  # pragma: no cover - message varies by version
            raise ConfigError(f"covsight_score: invalid expression {expression!r}: {exc}") from exc
        self._validate(tree)
        self._tree = tree

    def _validate(self, tree: ast.Expression) -> None:
        for node in ast.walk(tree):
            if isinstance(node, ast.Expression):
                continue
            if isinstance(node, ast.Constant):
                if not isinstance(node.value, (int, float)):
                    raise ConfigError(
                        f"covsight_score: only numeric literals are permitted, got {node.value!r}"
                    )
                continue
            if isinstance(node, ast.Name):
                if node.id not in self.variables:
                    raise ConfigError(
                        f"covsight_score: unknown name {node.id!r}; "
                        f"available names are {', '.join(self.variables)}"
                    )
                continue
            if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
                continue
            if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
                continue
            if isinstance(node, tuple(_BIN_OPS) + tuple(_UNARY_OPS)):
                continue
            if isinstance(node, ast.Load):
                continue
            raise ConfigError(
                f"covsight_score: {type(node).__name__} is not permitted in a score "
                f"expression ({self.expression!r})"
            )

    def __call__(self, **values: Any) -> int | float:
        missing = [v for v in self.variables if v not in values]
        if missing:
            raise ConfigError(f"covsight_score: missing value(s) for {', '.join(missing)}")
        result = self._eval(self._tree.body, values)
        if isinstance(result, bool) or not isinstance(result, (int, float)):
            raise ConfigError(f"covsight_score: expression produced {result!r}, expected a number")
        if not math.isfinite(result):
            raise ConfigError(f"covsight_score: expression produced a non-finite result {result!r}")
        if isinstance(result, float) and result.is_integer():
            return int(result)
        return result

    def _eval(self, node: ast.AST, values: Mapping[str, Any]) -> Any:
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            return values[node.id]
        if isinstance(node, ast.BinOp):
            op = _BIN_OPS[type(node.op)]
            left = self._eval(node.left, values)
            right = self._eval(node.right, values)
            if isinstance(node.op, ast.Pow) and abs(right) > 64:
                # An unbounded integer power is a denial of service, not an
                # arithmetic error: 9 ** 9 ** 99 never returns.
                raise ConfigError(
                    f"covsight_score: exponent {right!r} exceeds the permitted range (-64..64)"
                )
            try:
                return op(left, right)
            except ZeroDivisionError as exc:
                raise ConfigError(
                    f"covsight_score: division by zero evaluating {self.expression!r}"
                ) from exc
            except OverflowError as exc:
                raise ConfigError(
                    f"covsight_score: overflow evaluating {self.expression!r}"
                ) from exc
        if isinstance(node, ast.UnaryOp):
            return _UNARY_OPS[type(node.op)](self._eval(node.operand, values))
        raise ConfigError(  # pragma: no cover - _validate rejects these first
            f"covsight_score: {type(node).__name__} is not permitted"
        )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"ScoreExpression({self.expression!r})"
