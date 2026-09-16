"""The six authoring directives.

The syntax contract is deliberately format-neutral (decision D7), so one
implementation serves both RST and MyST:

* no repeated options — they are a hard error in RST and are silently dropped
  in MyST;
* no MyST YAML-block options — not valid RST, and lists arrive flattened;
* list-valued inputs (``covers``, ``coverage``, ``tests``) take a **body**,
  one item per line;
* nothing that depends on RST indentation semantics.

Nesting is tracked with an explicit stack on the environment rather than
inferred from node parentage, which breaks the moment a directive appears
inside a ``container`` or an ``only`` block.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any, cast

from docutils import nodes
from docutils.parsers.rst import directives
from sphinx.util.docutils import SphinxDirective
from sphinx.util.nodes import make_id

from . import logging as cslog
from .citations import parse_citation_lines
from .model import (
    CoverageBinding,
    EnvRecord,
    FeatureRecord,
    TestpointRecord,
    get_store,
)
from .nodes import citation_xref
from .util import slugify, split_list

#: Coverage binding types accepted by covsight testplan v1.
COVERAGE_TYPES = (
    "covergroup",
    "coverpoint",
    "cross",
    "assertion",
    "expression",
    "toggle",
    "line",
    "branch",
    "functional",
)

_STACK_KEY = "covsight:stack"
_ORDER_KEY = "covsight:order"

#: Start of a nested covsight directive, in either format.  Used to split a
#: directive body into "the prose the author wrote" and "the children".
_CHILD_START_RE = re.compile(
    r"^\s*(?:\.\.\s+(?:feature|env|testpoint|covers|coverage|tests)::"
    r"|(?::{3,}|`{3,})\{(?:feature|env|testpoint|covers|coverage|tests)\})"
)


def _priority(argument: str) -> str:
    return directives.choice(argument.strip().lower(), ("high", "medium", "low"))


def _positive_int(argument: str) -> int:
    value = directives.positive_int(argument)
    return value


class CovsightDirective(SphinxDirective):
    """Shared behaviour: nesting stack, document order, prose capture."""

    #: ``feature`` | ``env`` | ``testpoint`` | ``covers`` | ``coverage`` | ``tests``
    covsight_kind = ""
    #: Enclosing kinds this directive may appear in.  ``None`` means the
    #: document root is also acceptable.
    allowed_parents: tuple[str | None, ...] = ()

    # ── environment plumbing ─────────────────────────────────────────────

    @property
    def stack(self) -> list[tuple[str, Any]]:
        stack = cast("list[tuple[str, Any]]", self.env.temp_data.setdefault(_STACK_KEY, []))
        return stack

    def next_order(self) -> int:
        order = cast(int, self.env.temp_data.get(_ORDER_KEY, 0))
        self.env.temp_data[_ORDER_KEY] = order + 1
        return order

    def enclosing(self, *kinds: str) -> Any | None:
        for kind, record in reversed(self.stack):
            if kind in kinds:
                return record
        return None

    def check_nesting(self) -> None:
        parent_kind = self.stack[-1][0] if self.stack else None
        if parent_kind in self.allowed_parents:
            return
        allowed = ", ".join(
            "the document root" if p is None else f"'{p}'" for p in self.allowed_parents
        )
        where = f"inside '{parent_kind}'" if parent_kind else "at the document root"
        raise self.error(
            f"'{self.covsight_kind}' is not allowed {where}; it may only appear in {allowed}"
        )

    # ── body handling ────────────────────────────────────────────────────

    def prose(self) -> str:
        """The leading prose of the body, excluding any nested directives.

        The body is *also* parsed into the doctree for display.  The extracted
        ``desc`` is raw source rather than a re-serialisation of the rendered
        doctree, because serialising a doctree back to text is lossy and
        non-deterministic, and raw source is neither.
        """
        lines: list[str] = []
        for line in self.content:
            if _CHILD_START_RE.match(line):
                break
            lines.append(line)
        while lines and not lines[-1].strip():
            lines.pop()
        while lines and not lines[0].strip():
            lines.pop(0)
        return "\n".join(lines)

    def parse_body(self, into: nodes.Element) -> None:
        if self.content:
            self.state.nested_parse(self.content, self.content_offset, into)

    def body_text(self) -> str:
        return "\n".join(self.content)

    def line_of(self, index: int) -> int:
        """Source line number of content line *index*, 1-based.

        RST hands the directive a ``StringList`` that remembers the document
        line each content line came from; MyST hands one whose offsets are
        relative to the directive.  Taking the recorded offset only when it
        lands after the directive itself resolves both without asking which
        parser is in play.
        """
        items = getattr(self.content, "items", None)
        if items and index < len(items):
            lineno = int(items[index][1]) + 1
            if lineno > self.lineno:
                return lineno
        return self.lineno + 1 + index

    def argument_lines(self) -> list[tuple[str, int]]:
        """``(text, lineno)`` for each argument line.

        In RST a list-valued body written directly under the directive marker
        arrives as a multi-line *argument*, not as content — which is fine, but
        it means the line numbers have to be reconstructed from the block text.
        """
        if not self.arguments:
            return []
        first = (self.block_text or "").splitlines()
        marker = first[0] if first else ""
        after_marker = marker.partition("::")[2] or marker.partition("}")[2]
        start = self.lineno if after_marker.strip() else self.lineno + 1
        text = "\n".join(self.arguments)
        return [(line, start + offset) for offset, line in enumerate(text.splitlines())]

    def body_lines(self) -> list[tuple[str, int]]:
        """Every line an author wrote in this directive, with its line number."""
        lines = self.argument_lines()
        lines += [(line, self.line_of(index)) for index, line in enumerate(self.content)]
        return lines

    # ── presentation ─────────────────────────────────────────────────────

    def make_block(self, title: str, *, objid: str | None = None) -> nodes.Element:
        block = nodes.admonition(
            "",
            classes=["covsight", f"covsight-{self.covsight_kind}"],
        )
        block += nodes.title(title, title)
        if objid:
            node_id = make_id(self.env, self.state.document, "covsight", objid)
            block["ids"].append(node_id)
            block["names"].append(nodes.fully_normalize_name(objid))
            self.state.document.note_explicit_target(block)
            domain = self.env.get_domain("covsight")
            domain.note_object(  # type: ignore[attr-defined]
                self.covsight_kind, objid, node_id, self.env.docname
            )
        return block

    @staticmethod
    def field_list(rows: Sequence[tuple[str, nodes.Node | str]]) -> nodes.field_list | None:
        present = [(name, value) for name, value in rows if value not in (None, "", [])]
        if not present:
            return None
        field_list = nodes.field_list(classes=["covsight-fields"])
        for name, value in present:
            field = nodes.field()
            field += nodes.field_name(name, name)
            body = nodes.field_body()
            if isinstance(value, str):
                body += nodes.paragraph(value, value)
            else:
                paragraph = nodes.paragraph()
                paragraph += value
                body += paragraph
            field += body
            field_list += field
        return field_list


class FeatureDirective(CovsightDirective):
    """A feature — the review unit, and a ``goals[]`` entry."""

    covsight_kind = "feature"
    allowed_parents = (None, "feature")
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True
    has_content = True
    option_spec = {
        "id": directives.unchanged_required,
        "owner": directives.unchanged,
        "tags": directives.unchanged,
        "status": directives.unchanged,
    }

    def run(self) -> list[nodes.Node]:
        self.check_nesting()
        title = self.arguments[0].strip()
        feature_id = self.options["id"].strip()
        parent = self.enclosing("feature")

        record = FeatureRecord(
            id=feature_id,
            title=title,
            desc=self.prose(),
            owner=self.options.get("owner"),
            status=self.options.get("status"),
            tags=split_list(self.options.get("tags")),
            parent_id=parent.id if parent is not None else None,
            docname=self.env.docname,
            lineno=self.lineno,
            order=self.next_order(),
        )
        get_store(self.env).add_feature(record)

        block = self.make_block(f"Feature {feature_id}: {title}", objid=feature_id)
        fields = self.field_list(
            [
                ("Owner", record.owner or ""),
                ("Status", record.status or ""),
                ("Tags", ", ".join(record.tags)),
            ]
        )
        if fields is not None:
            block += fields

        self.stack.append((self.covsight_kind, record))
        try:
            self.parse_body(block)
        finally:
            self.stack.pop()
        return [block]


class EnvDirective(CovsightDirective):
    """A verification environment within a feature."""

    covsight_kind = "env"
    allowed_parents = ("feature",)
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = False
    has_content = True
    option_spec = {
        "title": directives.unchanged,
        "scope": directives.unchanged,
        "difficulty": directives.nonnegative_int,
        "coverage": directives.nonnegative_int,
    }

    def run(self) -> list[nodes.Node]:
        self.check_nesting()
        env_name = self.arguments[0].strip()
        feature = self.enclosing("feature")
        assert feature is not None  # guaranteed by check_nesting

        record = EnvRecord(
            env=env_name,
            feature_id=feature.id,
            title=self.options.get("title"),
            scope=self.options.get("scope"),
            difficulty=self.options.get("difficulty"),
            coverage_score=self.options.get("coverage"),
            desc=self.prose(),
            docname=self.env.docname,
            lineno=self.lineno,
            order=self.next_order(),
        )
        get_store(self.env).add_env(record)

        policy_title = (self.env.config.covsight_env_policy or {}).get(env_name, {}).get("title")
        block = self.make_block(
            f"Environment: {record.title or policy_title or env_name}",
            objid=f"{feature.id}.{env_name}",
        )
        fields = self.field_list(
            [
                ("Scope", record.scope or ""),
                ("Difficulty", "" if record.difficulty is None else str(record.difficulty)),
                (
                    "Coverage score",
                    "" if record.coverage_score is None else str(record.coverage_score),
                ),
            ]
        )
        if fields is not None:
            block += fields

        self.stack.append((self.covsight_kind, record))
        try:
            self.parse_body(block)
        finally:
            self.stack.pop()
        return [block]


class TestpointDirective(CovsightDirective):
    """A testpoint — the extraction unit."""

    covsight_kind = "testpoint"
    allowed_parents = ("env", "feature")
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True
    has_content = True
    option_spec = {
        "id": directives.unchanged,
        "stage": directives.unchanged,
        "priority": _priority,
        "weight": _positive_int,
        "owner": directives.unchanged,
        "tags": directives.unchanged,
        "na": directives.flag,
    }

    def run(self) -> list[nodes.Node]:
        self.check_nesting()
        title = self.arguments[0].strip()
        feature = self.enclosing("feature")
        env_record = self.enclosing("env")
        assert feature is not None

        env_name = env_record.env if env_record is not None else None
        explicit_id = self.options.get("id")
        if explicit_id:
            testpoint_id = explicit_id.strip()
        else:
            parts = [feature.id]
            if env_name:
                parts.append(env_name)
            parts.append(slugify(title))
            testpoint_id = ".".join(parts)

        record = TestpointRecord(
            id=testpoint_id,
            title=title,
            desc=self.prose(),
            feature_id=feature.id,
            env=env_name,
            stage=self.options.get("stage"),
            priority=self.options.get("priority"),
            weight=self.options.get("weight", 1),
            na="na" in self.options,
            explicit_id=bool(explicit_id),
            owner=self.options.get("owner"),
            tags=split_list(self.options.get("tags")),
            docname=self.env.docname,
            lineno=self.lineno,
            order=self.next_order(),
        )
        get_store(self.env).add_testpoint(record)

        block = self.make_block(f"Testpoint: {title}", objid=testpoint_id)
        fields = self.field_list(
            [
                ("ID", testpoint_id),
                ("Environment", env_name or ""),
                ("Stage", record.stage or ""),
                ("Priority", record.priority or ""),
                ("Weight", str(record.weight) if record.weight != 1 else ""),
                ("Owner", record.owner or ""),
                ("Tags", ", ".join(record.tags)),
                ("Not applicable", "yes" if record.na else ""),
            ]
        )
        if fields is not None:
            block += fields

        self.stack.append((self.covsight_kind, record))
        try:
            self.parse_body(block)
        finally:
            self.stack.pop()
        return [block]


class CoversDirective(CovsightDirective):
    """Citations to what a feature or testpoint is accountable to.

    Takes a body — one or more comma- and/or newline-separated targets — so a
    long citation list wraps cleanly.  A single-line argument form is also
    accepted for the common one-citation case.
    """

    covsight_kind = "covers"
    allowed_parents = ("feature", "testpoint")
    required_arguments = 0
    optional_arguments = 1
    final_argument_whitespace = True
    has_content = True
    option_spec: dict[str, Any] = {}

    def run(self) -> list[nodes.Node]:
        self.check_nesting()
        owner = self.enclosing("feature", "testpoint")
        assert owner is not None

        citations = parse_citation_lines(
            self.body_lines(), self.env.docname, location=self.get_location()
        )
        owner.citations.extend(citations)

        container = nodes.container(classes=["covsight", "covsight-covers"])
        container += nodes.rubric("", "Covers", classes=["covsight-rubric"])
        bullet_list = nodes.bullet_list()
        for citation in citations:
            item = nodes.list_item()
            paragraph = nodes.paragraph()
            xref = citation_xref("", citation.text)
            xref["kind"] = citation.kind
            xref["target"] = citation.target
            paragraph += xref
            item += paragraph
            bullet_list += item
        container += bullet_list
        return [container]


class CoverageDirective(CovsightDirective):
    """Coverage bindings, one ``<type>: <path>`` per body line.

    Body-parsed rather than option-parsed: repeated options are a hard error in
    RST and are silently dropped in MyST, so the option form is unavailable in
    *both* formats (``myst-authoring.md`` §3).
    """

    covsight_kind = "coverage"
    allowed_parents = ("testpoint",)
    required_arguments = 0
    optional_arguments = 0
    has_content = True
    option_spec: dict[str, Any] = {}

    def run(self) -> list[nodes.Node]:
        self.check_nesting()
        testpoint = self.enclosing("testpoint")
        assert testpoint is not None

        bindings: list[CoverageBinding] = []
        for raw, lineno in self.body_lines():
            line = raw.strip()
            if not line:
                continue
            kind, sep, path = line.partition(":")
            kind = kind.strip().lower()
            path = path.strip()
            if not sep or not path:
                cslog.warn(
                    "coverage-binding",
                    f"coverage: {line!r} is not a binding; expected '<type>: <path>'",
                    location=(self.env.docname, lineno),
                )
                continue
            if kind not in COVERAGE_TYPES:
                cslog.warn(
                    "coverage-binding",
                    f"coverage: unknown binding type {kind!r}; "
                    f"known types are {', '.join(COVERAGE_TYPES)}",
                    location=(self.env.docname, lineno),
                )
                continue
            bindings.append(
                CoverageBinding(
                    type=kind,
                    path=path,
                    docname=self.env.docname,
                    lineno=lineno,
                )
            )
        testpoint.coverage.extend(bindings)

        container = nodes.container(classes=["covsight", "covsight-coverage"])
        container += nodes.rubric("", "Coverage", classes=["covsight-rubric"])
        bullet_list = nodes.bullet_list()
        for binding in bindings:
            item = nodes.list_item()
            paragraph = nodes.paragraph()
            paragraph += nodes.emphasis(binding.type, binding.type)
            paragraph += nodes.Text(": ")
            paragraph += nodes.literal(binding.path, binding.path)
            item += paragraph
            bullet_list += item
        container += bullet_list
        return [container]


class TestsDirective(CovsightDirective):
    """The test names that exercise a testpoint, before substitution."""

    covsight_kind = "tests"
    allowed_parents = ("testpoint",)
    required_arguments = 0
    optional_arguments = 1
    final_argument_whitespace = True
    has_content = True
    option_spec: dict[str, Any] = {}

    def run(self) -> list[nodes.Node]:
        self.check_nesting()
        testpoint = self.enclosing("testpoint")
        assert testpoint is not None

        names = split_list("\n".join(line for line, _lineno in self.body_lines()))
        testpoint.tests.extend(names)

        container = nodes.container(classes=["covsight", "covsight-tests"])
        container += nodes.rubric("", "Tests", classes=["covsight-rubric"])
        bullet_list = nodes.bullet_list()
        for name in names:
            item = nodes.list_item()
            paragraph = nodes.paragraph()
            paragraph += nodes.literal(name, name)
            item += paragraph
            bullet_list += item
        container += bullet_list
        return [container]


DIRECTIVES = {
    "feature": FeatureDirective,
    "env": EnvDirective,
    "testpoint": TestpointDirective,
    "covers": CoversDirective,
    "coverage": CoverageDirective,
    "tests": TestsDirective,
}
