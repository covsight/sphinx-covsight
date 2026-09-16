"""Policy loading, interpolation, and the score-expression sandbox (D5)."""

from __future__ import annotations

import pytest
import yaml
from sphinx.errors import ConfigError

from sphinx_covsight.policy import (
    EnvPolicy,
    ScoreExpression,
    load_policy,
    policy_fingerprint,
)

POLICY = {
    "ip_simulation": {
        "title": "IP Simulation",
        "approach": "Constrained-random stimulus targeting {feature}.",
        "reasoning": "Practical run time.",
        "exit_criteria": ["100% regression pass", "95%+ coverage"],
    },
    "formal": {
        "title": "Formal",
        "approach": "Property proofs over {feature} in {env}.",
    },
}


def test_inline_and_file_forms_are_equivalent(tmp_path):
    inline = load_policy(POLICY, None, tmp_path)
    path = tmp_path / "policy.yaml"
    path.write_text(yaml.safe_dump(POLICY), encoding="utf-8")
    from_file = load_policy(None, "policy.yaml", tmp_path)

    assert inline == from_file
    assert policy_fingerprint(inline, "(11 - difficulty) * coverage") == policy_fingerprint(
        from_file, "(11 - difficulty) * coverage"
    )


def test_fingerprint_changes_with_policy_and_with_expression(tmp_path):
    policy = load_policy(POLICY, None, tmp_path)
    base = policy_fingerprint(policy, "(11 - difficulty) * coverage")
    assert base != policy_fingerprint(policy, "difficulty * coverage")

    changed = load_policy({**POLICY, "formal": {"title": "Formal proofs"}}, None, tmp_path)
    assert base != policy_fingerprint(changed, "(11 - difficulty) * coverage")


def test_interpolation(tmp_path):
    policy = load_policy(POLICY, None, tmp_path)["formal"]
    rendered = policy.rendered(feature="Baud rate generation", env="formal")
    assert rendered.approach == "Property proofs over Baud rate generation in formal."
    # The stored policy is untouched, so a second feature interpolates cleanly.
    assert "{feature}" in policy.approach


def test_unknown_placeholder_is_a_config_error(tmp_path):
    with pytest.raises(ConfigError, match=r"unknown placeholder \{owner\}"):
        load_policy({"sim": {"approach": "targeting {owner}"}}, None, tmp_path)


def test_unknown_policy_key_is_a_config_error(tmp_path):
    with pytest.raises(ConfigError, match="unknown key"):
        load_policy({"sim": {"strategy": "x"}}, None, tmp_path)


def test_inline_and_file_are_mutually_exclusive(tmp_path):
    (tmp_path / "policy.yaml").write_text("sim: {}", encoding="utf-8")
    with pytest.raises(ConfigError, match="mutually exclusive"):
        load_policy(POLICY, "policy.yaml", tmp_path)


def test_missing_policy_file(tmp_path):
    with pytest.raises(ConfigError, match="not found"):
        load_policy(None, "nope.yaml", tmp_path)


def test_exit_criteria_string_is_accepted(tmp_path):
    policy = load_policy({"sim": {"exit_criteria": "one thing"}}, None, tmp_path)
    assert policy["sim"].exit_criteria == ["one thing"]


# ── the score expression ──────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("expression", "difficulty", "coverage", "expected"),
    [
        ("(11 - difficulty) * coverage", 3, 8, 64),
        ("(11 - difficulty) * coverage", 6, 4, 20),
        ("difficulty + coverage", 1, 2, 3),
        ("coverage / 2", 0, 9, 4.5),
        ("coverage // 2", 0, 9, 4),
        ("coverage % 4", 0, 9, 1),
        ("-difficulty", 3, 0, -3),
        ("difficulty ** 2", 3, 0, 9),
        ("2 * (difficulty + coverage) - 1", 1, 1, 3),
    ],
)
def test_score_arithmetic(expression, difficulty, coverage, expected):
    score = ScoreExpression(expression)
    assert score(difficulty=difficulty, coverage=coverage) == expected


HOSTILE = [
    "__import__('os').system('true')",
    "(lambda: 1)()",
    "difficulty.__class__",
    "difficulty.__class__.__mro__[1]",
    "[x for x in range(10)]",
    "{'a': 1}['a']",
    "(y := difficulty)",
    "difficulty if coverage else 0",
    "open('/etc/passwd').read()",
    "globals()",
    "difficulty and coverage",
    "difficulty > coverage",
    "f'{difficulty}'",
    "'string'",
    "unknown_name",
]


@pytest.mark.parametrize("expression", HOSTILE)
def test_score_expression_sandbox(expression):
    """An ``eval`` reaching ``__import__`` in a doc build is a real vulnerability:
    plans are built in CI from arbitrary branches."""
    with pytest.raises(ConfigError):
        ScoreExpression(expression)


def test_score_rejects_division_by_zero():
    score = ScoreExpression("coverage / difficulty")
    with pytest.raises(ConfigError, match="division by zero"):
        score(difficulty=0, coverage=1)


def test_score_rejects_unbounded_exponent():
    score = ScoreExpression("difficulty ** coverage")
    with pytest.raises(ConfigError, match="exponent"):
        score(difficulty=9, coverage=10_000)


def test_score_rejects_syntax_error():
    with pytest.raises(ConfigError, match="invalid expression"):
        ScoreExpression("difficulty *")


def test_policy_as_dict_roundtrip(tmp_path):
    policy = load_policy(POLICY, None, tmp_path)
    assert policy["ip_simulation"].as_dict()["exit_criteria"] == [
        "100% regression pass",
        "95%+ coverage",
    ]
    assert EnvPolicy().as_dict() == {
        "title": "",
        "approach": "",
        "reasoning": "",
        "exit_criteria": [],
    }
