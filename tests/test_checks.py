"""Every build-time check fires on the crafted root and is silent on a clean one."""

from __future__ import annotations

import pytest


def warnings_text(warning) -> str:
    return warning.getvalue()


@pytest.mark.sphinx("html", testroot="errors", freshenv=True)
def test_duplicate_feature_id(app, warning):
    app.build()
    assert "duplicate feature id 'FEAT-DUP'" in warnings_text(warning)


@pytest.mark.sphinx("html", testroot="errors", freshenv=True)
def test_unmapped_testpoint(app, warning):
    app.build()
    text = warnings_text(warning)
    assert "has no '.. tests::' and is not marked ':na:'" in text
    assert "FEAT-DUP.tp_unmapped" in text


@pytest.mark.sphinx("html", testroot="errors", freshenv=True)
def test_empty_goals(app, warning):
    app.build()
    text = warnings_text(warning)
    assert "feature 'FEAT-EMPTY' has no environments and no testpoints" in text
    assert "environment 'ip_simulation' of feature 'FEAT-NOTP' has no testpoints" in text


@pytest.mark.sphinx("html", testroot="errors", freshenv=True)
def test_unbound_substitution(app, warning):
    app.build()
    assert "no substitution binding for {unbound}" in warnings_text(warning)


@pytest.mark.sphinx("html", testroot="errors", freshenv=True)
def test_missing_policy(app, warning):
    app.build()
    assert "no covsight_env_policy entry for environment 'ip_simulation'" in warnings_text(warning)


@pytest.mark.sphinx("html", testroot="errors", freshenv=True)
def test_citation_id_charset(app, warning):
    """sphinx-needs only resolves ``[A-Za-z0-9_]`` ids (myst-authoring.md §6)."""
    app.build()
    text = warnings_text(warning)
    assert "rule id 'UART.1.1.1' contains characters outside [A-Za-z0-9_]" in text


@pytest.mark.sphinx("html", testroot="errors", freshenv=True)
def test_bad_citation_syntax(app, warning):
    app.build()
    text = warnings_text(warning)
    assert "unknown citation prefix 'bogus'" in text
    assert "'not-a-citation' is not a citation" in text


@pytest.mark.sphinx("html", testroot="errors", freshenv=True)
def test_bad_coverage_binding(app, warning):
    app.build()
    text = warnings_text(warning)
    assert "unknown binding type 'nonsense'" in text
    assert "'no-colon-here' is not a binding" in text


@pytest.mark.sphinx("html", testroot="basic")
def test_clean_root_is_silent(app, warning):
    app.build()
    assert warnings_text(warning).strip() == ""


@pytest.mark.sphinx(
    "html",
    testroot="errors",
    freshenv=True,
    confoverrides={
        "suppress_warnings": [
            "covsight.duplicate-id",
            "covsight.empty-goal",
            "covsight.testpoint-unmapped",
            "covsight.missing-policy",
            "covsight.substitution",
            "covsight.citation-id-charset",
            "covsight.citation-syntax",
            "covsight.coverage-binding",
        ]
    },
)
def test_checks_are_suppressible(app, warning):
    app.build()
    text = warnings_text(warning)
    assert "covsight.duplicate-id" not in text
    assert "covsight.empty-goal" not in text
    assert "covsight.coverage-binding" not in text


@pytest.mark.sphinx(
    "html",
    testroot="basic",
    confoverrides={"covsight_require_explicit_testpoint_ids": "1"},
)
def test_require_explicit_testpoint_ids(app, warning):
    app.build()
    text = warnings_text(warning)
    assert "has no ':id:'" in text
    assert "All supported divisor values" in text


@pytest.mark.sphinx("html", testroot="errors", freshenv=True)
def test_warnings_carry_covsight_subtypes(app, warning):
    """Subtypes are the public interface of the degradation story."""
    app.build()
    text = warnings_text(warning)
    for subtype in (
        "covsight.duplicate-id",
        "covsight.testpoint-unmapped",
        "covsight.empty-goal",
        "covsight.substitution",
        "covsight.missing-policy",
        "covsight.citation-id-charset",
        "covsight.coverage-binding",
    ):
        assert f"[{subtype}]" in text
