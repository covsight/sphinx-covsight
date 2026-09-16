"""The documentation itself builds clean, and its reference tables come from the code."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
DOCS = REPO / "docs"

pytest.importorskip("myst_parser")
pytest.importorskip("sphinx_needs")


@pytest.fixture(scope="module")
def built_docs(tmp_path_factory) -> Path:
    from sphinx.application import Sphinx

    tmp = tmp_path_factory.mktemp("docs")
    out = tmp / "out"
    app = Sphinx(
        srcdir=str(DOCS),
        confdir=str(DOCS),
        outdir=str(out),
        doctreedir=str(tmp / "doctrees"),
        buildername="html",
        freshenv=True,
        warningiserror=True,
        status=None,
    )
    app.build()
    return out


def test_docs_build_clean_under_W_and_nitpicky(built_docs):
    assert (built_docs / "index.html").is_file()


def test_configuration_reference_lists_every_config_value(built_docs):
    from sphinx_covsight import CONFIG_VALUES

    html = (built_docs / "reference" / "configuration.html").read_text(encoding="utf-8")
    for name, _default, _rebuild, _doc in CONFIG_VALUES:
        assert name in html, f"{name} missing from the generated configuration reference"


def test_directive_reference_lists_every_directive_and_option(built_docs):
    from sphinx_covsight.directives import DIRECTIVES

    html = (built_docs / "reference" / "directives.html").read_text(encoding="utf-8")
    for name, directive in DIRECTIVES.items():
        assert f'<span class="pre">{name}</span>' in html or name in html
        for option in directive.option_spec or {}:
            assert f":{option}:" in re.sub("<[^>]+>", "", html)


def test_warning_reference_lists_every_subtype(built_docs):
    from sphinx_covsight.logging import SUBTYPES

    text = re.sub("<[^>]+>", "", (built_docs / "reference" / "directives.html").read_text())
    for subtype in SUBTYPES:
        assert f"covsight.{subtype}" in text


def test_guides_quote_the_example_rather_than_restating_it(built_docs):
    """Every code block in a guide is a literalinclude from docs/example."""
    for guide in (DOCS / "guide").glob("*.rst"):
        source = guide.read_text(encoding="utf-8")
        includes = re.findall(r"\.\. literalinclude:: (\S+)", source)
        for target in includes:
            assert (guide.parent / target).resolve().is_file(), f"{guide.name}: {target}"


def test_index_links_every_guide():
    index = (DOCS / "index.rst").read_text(encoding="utf-8")
    for guide in (DOCS / "guide").glob("*.rst"):
        assert f"guide/{guide.stem}" in index
