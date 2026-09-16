"""sphinx-covsight — author verification plans as documents, extract covsight testplan v1.

The extension's whole job is to keep two readers happy at once: a human
reviewing a diff of prose, and a tool walking a graph.  Everything here follows
from that — the authored document is the source of truth, and the emitted plan
is a deterministic projection of it.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from docutils import nodes as docnodes

from . import logging as cslog
from .checks import run_checks
from .citations import CitationResolver
from .directives import DIRECTIVES
from .domain import CovsightDomain
from .emit import (
    count_plan,
    provenance,
    write_json,
    write_provenance,
    write_yaml,
)
from .extract import ExtractOptions, ExtractResult, extract
from .model import (
    ENV_VERSION,
    Citation,
    FeatureRecord,
    PlanStore,
    TestpointRecord,
    get_store,
)
from .nodes import citation_xref, depart_passthrough, visit_passthrough
from .policy import DEFAULT_SCORE_EXPRESSION, ScoreExpression, load_policy, policy_fingerprint
from .roles import ROLES
from .util import document_order

if TYPE_CHECKING:  # pragma: no cover
    from sphinx.application import Sphinx
    from sphinx.environment import BuildEnvironment

__version__ = "0.1.0"

#: Coverage-binding types the ``sv`` domain has an object kind for, and which
#: leaf validation (D2) can therefore check.
SV_VALIDATED_COVERAGE_TYPES = frozenset({"covergroup", "coverpoint"})

#: Every configuration value, its default, and what it does.  The configuration
#: reference in the documentation is generated from this table, so the two
#: cannot drift.
CONFIG_VALUES: tuple[tuple[str, Any, str, str], ...] = (
    ("covsight_plan_name", "", "env", "Plan-level ``name`` in the emitted testplan."),
    ("covsight_plan_description", "", "env", "Plan-level ``description``."),
    ("covsight_plan_owner", "", "env", "Plan-level ``owner``."),
    ("covsight_plan_tags", [], "env", "Plan-level ``tags``."),
    (
        "covsight_env_policy",
        {},
        "env",
        "Per-environment policy: ``title``, ``approach``, ``reasoning``, "
        "``exit_criteria``.  ``{feature}`` and ``{env}`` are interpolated.",
    ),
    (
        "covsight_env_policy_file",
        None,
        "env",
        "YAML file holding the same data as ``covsight_env_policy``, relative to "
        "``conf.py``.  Mutually exclusive with the inline form.",
    ),
    (
        "covsight_score",
        DEFAULT_SCORE_EXPRESSION,
        "env",
        "Restricted arithmetic expression over ``difficulty`` and ``coverage`` "
        "giving a goal's ``overall_score``.  Calls, attributes and subscripts are "
        "rejected.",
    ),
    (
        "covsight_substitutions",
        {},
        "env",
        "``{key}`` bindings expanded in ``.. tests::`` names, and recorded in the plan.",
    ),
    (
        "covsight_needs_json",
        None,
        "env",
        "Path to the specification's ``needs.json``, relative to ``conf.py``.  "
        "Enables the ``rule:`` citation backend.",
    ),
    (
        "covsight_spec_base_url",
        "",
        "env",
        "URL prefix prepended to resolved ``rule:`` citation links.",
    ),
    (
        "covsight_doc_base_url",
        "",
        "env",
        "URL prefix prepended to resolved ``sv:`` and ``rdl:`` citation links.",
    ),
    (
        "covsight_strict_citations",
        False,
        "env",
        "Promote unresolved-citation warnings to build errors.  What CI should set.",
    ),
    (
        "covsight_validate_coverage_bindings",
        True,
        "env",
        "Validate the leaf name of each ``.. coverage::`` path against the ``sv`` "
        "domain.  A no-op when sphinx-systemverilog is absent.",
    ),
    (
        "covsight_require_explicit_testpoint_ids",
        False,
        "env",
        "Warn when a testpoint relies on a derived id, for teams that SHA-bind at "
        "testpoint granularity.",
    ),
    (
        "covsight_env_in_custom",
        True,
        "env",
        "Write a testpoint's environment to ``custom.covsight.env`` rather than to a "
        "top-level ``env`` field.  Flip to ``False`` once covsight-core's schema "
        "carries the field.",
    ),
    (
        "covsight_output",
        "testplan.json",
        "html",
        "Where to write the plan, relative to the build output directory.  Set to "
        "``None`` to disable emission.",
    ),
    (
        "covsight_output_format",
        "json",
        "html",
        "``json``, ``yaml`` or ``both``.  JSON is the hashed artifact; YAML is for humans.",
    ),
    (
        "covsight_provenance",
        True,
        "html",
        "Write the ``*.provenance.json`` sidecar next to the plan.",
    ),
)


@dataclass
class BuildState:
    """Per-build state that must not be pickled into the environment."""

    resolver: CitationResolver
    policy: dict[str, Any] = field(default_factory=dict)
    score: ScoreExpression | None = None
    policy_sha256: str = ""
    last_result: ExtractResult | None = None


def _state(app: Sphinx) -> BuildState:
    return app._covsight_state  # type: ignore[attr-defined]


# ── event handlers ────────────────────────────────────────────────────────────


def on_builder_inited(app: Sphinx) -> None:
    resolver = CitationResolver(app)
    state = BuildState(resolver=resolver)
    app._covsight_state = state  # type: ignore[attr-defined]

    state.policy = load_policy(
        app.config.covsight_env_policy,
        app.config.covsight_env_policy_file,
        app.confdir,
    )
    state.score = ScoreExpression(app.config.covsight_score or DEFAULT_SCORE_EXPRESSION)
    state.policy_sha256 = policy_fingerprint(state.policy, state.score.expression)
    resolver.load()
    get_store(app.env)


def on_env_purge_doc(app: Sphinx, env: BuildEnvironment, docname: str) -> None:
    get_store(env).purge(docname)


def on_env_merge_info(
    app: Sphinx, env: BuildEnvironment, docnames: list[str], other: BuildEnvironment
) -> None:
    other_store = getattr(other, "covsight_plan", None)
    if isinstance(other_store, PlanStore):
        get_store(env).merge(other_store, docnames)


def on_doctree_resolved(app: Sphinx, doctree: docnodes.document, docname: str) -> None:
    state = _state(app)
    store = get_store(app.env)

    # Fill urls on the records of this document so the rendered page links even
    # on an incremental build.  Warnings are deferred to build-finished, where
    # every document's citations are visited exactly once.
    records: list[FeatureRecord | TestpointRecord] = [
        *store.features.get(docname, []),
        *store.testpoints.get(docname, []),
    ]
    for record in records:
        state.resolver.resolve_iter(record.citations, app.env, warn=False)

    for node in list(doctree.findall(citation_xref)):
        node.replace_self(_render_citation(app, state, node, docname))


def _render_citation(
    app: Sphinx, state: BuildState, node: citation_xref, docname: str
) -> docnodes.Node:
    citation = Citation(
        kind=node["kind"],
        target=node["target"],
        docname=docname,
        lineno=node.line or 0,
    )
    state.resolver.resolve(citation, app.env, warn=False)
    text = node.astext() or citation.text
    label = docnodes.literal(text, text, classes=["covsight-citation"])
    if not citation.url:
        return label
    reference = docnodes.reference("", "", internal=False, refuri=citation.url)
    if citation.title:
        reference["reftitle"] = citation.title
    reference += label
    return reference


def on_build_finished(app: Sphinx, exception: Exception | None) -> None:
    if exception is not None:
        # A failed build must never publish an artifact.
        return
    state = _state(app)
    env = app.env
    store = get_store(env)

    state.resolver.resolve_all(store, env, warn=True)
    state.resolver.report_unresolved()
    _validate_coverage_bindings(app, store)

    options = ExtractOptions(
        plan_name=app.config.covsight_plan_name,
        description=app.config.covsight_plan_description,
        owner=app.config.covsight_plan_owner,
        tags=list(app.config.covsight_plan_tags or []),
        substitutions=dict(app.config.covsight_substitutions or {}),
        policy=state.policy,
        score=state.score,
        env_in_custom=app.config.covsight_env_in_custom,
        document_order=document_order(env),
    )
    result = extract(store, options)
    state.last_result = result

    run_checks(
        store,
        result,
        policy=state.policy,
        env_in_custom=options.env_in_custom,
        require_explicit_testpoint_ids=app.config.covsight_require_explicit_testpoint_ids,
    )

    _write_outputs(app, state, result)
    _copy_assets(app)


def _validate_coverage_bindings(app: Sphinx, store: PlanStore) -> None:
    """Validate the leaf name of each coverage path against the ``sv`` domain (D2).

    Only the leaf is checked.  ``.. coverage::`` paths are UCIS *instance*
    paths while the ``sv`` domain keys on SystemVerilog *declaration* paths —
    different namespaces — so a full-path check would be wrong rather than
    merely strict.
    """
    if not app.config.covsight_validate_coverage_bindings:
        return
    if "sphinx_systemverilog" not in app.extensions:
        return
    try:
        domain = app.env.get_domain("sv")
    except Exception:  # pragma: no cover - defensive
        return
    for tp in store.all_testpoints():
        for binding in tp.coverage:
            if binding.type not in SV_VALIDATED_COVERAGE_TYPES:
                # The sv domain has no object kind for crosses, assertions or
                # code-coverage bindings, so checking them would report every
                # one of them as missing.
                continue
            leaf = binding.path.replace("::", ".").split(".")[-1]
            if not domain.candidates(leaf):  # type: ignore[attr-defined]
                cslog.warn(
                    "coverage-binding",
                    f"no {binding.type} named {leaf!r} is documented in the sv domain "
                    f"(from {binding.path!r})",
                    location=(binding.docname, binding.lineno),
                )


def _output_path(app: Sphinx) -> Path | None:
    output = app.config.covsight_output
    if not output:
        return None
    path = Path(output)
    return path if path.is_absolute() else Path(app.outdir) / path


def _write_outputs(app: Sphinx, state: BuildState, result: ExtractResult) -> None:
    path = _output_path(app)
    if path is None:
        return
    fmt = app.config.covsight_output_format
    if fmt in ("json", "both"):
        write_json(path, result.plan)
    if fmt in ("yaml", "both"):
        write_yaml(path.with_suffix(".yaml"), result.plan)
    if fmt not in ("json", "yaml", "both"):
        cslog.warn("config", f"unknown covsight_output_format {fmt!r}; writing JSON")
        write_json(path, result.plan)

    if app.config.covsight_provenance:
        write_provenance(
            path.with_suffix(".provenance.json"),
            provenance(
                plan=result.plan,
                srcdir=app.srcdir,
                version=__version__,
                policy_sha256=state.policy_sha256,
                score_expression=state.score.expression if state.score else "",
                needs_json_sha256=state.resolver.state.needs_sha256,
                citation_backends=state.resolver.backend_availability(),
                counts=count_plan(result.plan),
            ),
        )


def _copy_assets(app: Sphinx) -> None:
    if app.builder.format != "html":
        return
    try:
        from sphinx.util.fileutil import copy_asset_file
    except ImportError:  # pragma: no cover
        return
    source = Path(__file__).parent / "static" / "covsight.css"
    if source.is_file():
        copy_asset_file(str(source), os.path.join(app.builder.outdir, "_static"))


# ── setup ─────────────────────────────────────────────────────────────────────


def setup(app: Sphinx) -> dict[str, Any]:
    for name, default, rebuild, _doc in CONFIG_VALUES:
        app.add_config_value(name, default, cast(Any, rebuild))

    app.add_domain(CovsightDomain)
    app.add_node(
        citation_xref,
        html=(visit_passthrough, depart_passthrough),
        latex=(visit_passthrough, depart_passthrough),
        text=(visit_passthrough, depart_passthrough),
        man=(visit_passthrough, depart_passthrough),
        texinfo=(visit_passthrough, depart_passthrough),
    )
    for name, directive in DIRECTIVES.items():
        app.add_directive(name, directive)
    for name, role in ROLES.items():
        app.add_role(name, role)
    app.add_css_file("covsight.css")

    app.connect("builder-inited", on_builder_inited)
    app.connect("env-purge-doc", on_env_purge_doc)
    app.connect("env-merge-info", on_env_merge_info)
    app.connect("doctree-resolved", on_doctree_resolved)
    app.connect("build-finished", on_build_finished)

    return {
        "version": __version__,
        "env_version": ENV_VERSION,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
