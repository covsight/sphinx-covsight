"""Citation parsing and resolution across three independently optional backends.

The degradation ladder is the substance of this module:

===============================  ==================================================
Situation                        Behaviour
===============================  ==================================================
Backend present, target resolves ``url`` and ``title`` filled
Backend present, target missing  warning ``covsight.citation-unresolved``
Backend absent                   **one** informational message per backend per build
``covsight_strict_citations``    the first two rows' warnings become errors
===============================  ==================================================

The "one message per backend" rule is load-bearing.  A plan with 400 ``rdl:``
citations built without sphinx-peakrdl must not emit 400 warnings, or authors
stop writing the citations.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from . import logging as cslog
from .model import Citation

if TYPE_CHECKING:  # pragma: no cover
    from sphinx.application import Sphinx
    from sphinx.environment import BuildEnvironment

#: Recognised citation prefixes.
KINDS = ("rule", "rdl", "sv")

#: sphinx-needs resolves cross-references only for IDs in this charset
#: (``myst-authoring.md`` §6), so anything else is flagged by ``checks.py``.
NEEDS_ID_RE = re.compile(r"^[A-Za-z0-9_]+$")

_SPLIT_RE = re.compile(r"[,\n]")


def parse_citations(
    text: str,
    docname: str,
    lineno: int,
    *,
    location: Any = None,
) -> list[Citation]:
    """Parse citation text whose lines start at *lineno*."""
    lines = [(line, lineno + offset) for offset, line in enumerate(text.splitlines())]
    return parse_citation_lines(lines, docname, location=location)


def parse_citation_lines(
    lines: Iterable[tuple[str, int]],
    docname: str,
    *,
    location: Any = None,
) -> list[Citation]:
    """Parse ``(source line, line number)`` pairs into citations.

    Targets are separated by commas and/or newlines.  Line numbers are carried
    per source line so a warning points at the offending line rather than at
    the top of the directive.
    """
    citations: list[Citation] = []
    for line, line_no in lines:
        for token in _SPLIT_RE.split(line):
            token = token.strip()
            if not token:
                continue
            kind, sep, target = token.partition(":")
            if not sep or not target.strip():
                cslog.warn(
                    "citation-syntax",
                    f"covers: {token!r} is not a citation; expected '<{'|'.join(KINDS)}>:<target>'",
                    location=location,
                )
                continue
            kind = kind.strip()
            if kind not in KINDS:
                cslog.warn(
                    "citation-syntax",
                    f"covers: unknown citation prefix {kind!r}; "
                    f"known prefixes are {', '.join(KINDS)}",
                    location=location,
                )
                continue
            citations.append(
                Citation(
                    kind=kind,
                    target=target.strip(),
                    docname=docname,
                    lineno=line_no,
                )
            )
    return citations


@dataclass
class BackendStatus:
    """Whether a citation backend can resolve anything this build."""

    name: str
    available: bool = False
    reason: str = ""
    requested: int = 0  # citations of this kind seen this build


@dataclass
class ResolverState:
    backends: dict[str, BackendStatus] = field(default_factory=dict)
    needs: dict[str, dict] = field(default_factory=dict)
    needs_sha256: str | None = None


class CitationResolver:
    """Resolves ``rule:`` / ``sv:`` / ``rdl:`` citations, or degrades cleanly."""

    def __init__(self, app: Sphinx) -> None:
        self.app = app
        self.state = ResolverState(
            backends={k: BackendStatus(name=k) for k in KINDS},
        )
        self._unvalidated_rdl = 0
        self._counting = False

    # ── setup, at builder-inited ──────────────────────────────────────────

    def load(self) -> None:
        config = self.app.config
        self._load_needs(config.covsight_needs_json)

        sv = self.state.backends["sv"]
        if "sphinx_systemverilog" in self.app.extensions:
            sv.available = True
        else:
            sv.reason = "sphinx-systemverilog is not enabled"

        rdl = self.state.backends["rdl"]
        if "sphinx_peakrdl" in self.app.extensions:
            rdl.available = True
        else:
            rdl.reason = "sphinx-peakrdl is not enabled"

        for name in KINDS:
            backend = self.state.backends[name]
            cslog.verbose(
                f"citation backend {name}: "
                + ("available" if backend.available else f"absent ({backend.reason})")
            )

    def _load_needs(self, needs_json: str | None) -> None:
        backend = self.state.backends["rule"]
        if not needs_json:
            backend.reason = "covsight_needs_json is not configured"
            return
        path = Path(self.app.confdir) / needs_json
        if not path.is_file():
            backend.reason = f"covsight_needs_json not found: {path}"
            return
        data = path.read_bytes()
        self.state.needs_sha256 = hashlib.sha256(data).hexdigest()
        try:
            doc = json.loads(data.decode("utf-8"))
        except ValueError as exc:
            backend.reason = f"covsight_needs_json is not valid JSON: {exc}"
            return
        self.state.needs = _index_needs(doc)
        backend.available = True

    # ── resolution ────────────────────────────────────────────────────────

    def resolve(self, citation: Citation, env: BuildEnvironment, *, warn: bool) -> Citation:
        """Fill ``url``/``title`` on *citation* in place and return it."""
        backend = self.state.backends.get(citation.kind)
        if backend is None:  # pragma: no cover - parse_citations filters these
            return citation
        if warn:
            # Only the authoritative pass counts, so the once-per-build summary
            # reports the number of citations in the plan rather than the number
            # of times resolution happened to run.
            backend.requested += 1
        if not backend.available:
            return citation

        resolver = getattr(self, f"_resolve_{citation.kind}")
        self._counting = warn
        resolved = resolver(citation, env)
        if not resolved and warn:
            self._unresolved(citation)
        return citation

    def resolve_all(self, store: Any, env: BuildEnvironment, *, warn: bool = True) -> None:
        for citation in store.all_citations():
            self.resolve(citation, env, warn=warn)

    def resolve_iter(
        self, citations: Iterable[Citation], env: BuildEnvironment, *, warn: bool = False
    ) -> None:
        for citation in citations:
            self.resolve(citation, env, warn=warn)

    # ── backends ──────────────────────────────────────────────────────────

    def _resolve_rule(self, citation: Citation, env: BuildEnvironment) -> bool:
        need = self.state.needs.get(citation.target)
        if need is None:
            return False
        base = self.app.config.covsight_spec_base_url or ""
        docname = need.get("docname") or ""
        citation.url = f"{base}{docname}.html#{citation.target}" if docname else None
        citation.title = need.get("title") or None
        citation.validated = True
        return True

    def _resolve_sv(self, citation: Citation, env: BuildEnvironment) -> bool:
        try:
            domain = env.get_domain("sv")
        except Exception:  # pragma: no cover - extension present but domain missing
            return False
        objects = getattr(domain, "objects", {})
        target = citation.target
        fullname = None
        if target in objects:
            fullname = target
        else:
            alt = target.replace(".", "::")
            if alt in objects:
                fullname = alt
            else:
                candidates = sorted(domain.candidates(target))  # type: ignore[attr-defined]
                if len(candidates) == 1:
                    fullname = candidates[0]
                elif len(candidates) > 1:
                    if not self._counting:
                        return True
                    cslog.warn(
                        "citation-unresolved",
                        f"sv:{target} is ambiguous; candidates: {', '.join(candidates)}",
                        location=(citation.docname, citation.lineno),
                    )
                    return True  # reported here; do not report again as unresolved
        if fullname is None:
            return False
        docname, anchor, _kind = objects[fullname]
        base = self.app.config.covsight_doc_base_url or ""
        citation.url = f"{base}{docname}.html#{anchor}"
        citation.title = fullname
        citation.validated = True
        return True

    def _resolve_rdl(self, citation: Citation, env: BuildEnvironment) -> bool:
        try:
            from sphinx_peakrdl import design_state as rdl_state
            from sphinx_peakrdl.html import HTML_INDEX
            from sphinx_peakrdl.utils import lookup_rdl_node
        except ImportError:  # pragma: no cover - availability is probed at load()
            return False

        base = self.app.config.covsight_doc_base_url or ""
        if getattr(rdl_state, "root_node", None) is None:
            # The RDL was not compiled in this build, so the target cannot be
            # validated.  Record it unvalidated rather than dropping it.
            if self._counting:
                self._unvalidated_rdl += 1
            citation.validated = False
            return True

        node = lookup_rdl_node(citation.target)
        if node is None:
            return False

        from systemrdl.node import FieldNode

        anchor = ""
        if isinstance(node, FieldNode):
            anchor = f"#{node.inst_name}"
            node = node.parent
        path = node.get_path(empty_array_suffix="")
        citation.url = f"{base}{HTML_INDEX}.html?p={path}{anchor}"
        citation.title = citation.target
        citation.validated = True
        return True

    # ── reporting ─────────────────────────────────────────────────────────

    def _unresolved(self, citation: Citation) -> None:
        message = f"unresolved citation {citation.text}"
        if self.app.config.covsight_strict_citations:
            from sphinx.errors import ExtensionError

            raise ExtensionError(
                f"{citation.docname}:{citation.lineno}: {message} "
                f"(covsight_strict_citations is set)"
            )
        cslog.warn(
            "citation-unresolved",
            message,
            location=(citation.docname, citation.lineno),
        )

    def report_unresolved(self) -> None:
        """Emit the once-per-build summary messages."""
        for name in KINDS:
            backend = self.state.backends[name]
            if backend.available or not backend.requested:
                continue
            cslog.info(
                f"{backend.requested} '{name}:' citation(s) recorded without a URL: "
                f"{backend.reason}"
            )
        if self._unvalidated_rdl:
            cslog.info(
                f"{self._unvalidated_rdl} 'rdl:' citation(s) could not be validated: "
                "the SystemRDL model was not compiled in this build"
            )

    # ── provenance ────────────────────────────────────────────────────────

    def backend_availability(self) -> dict[str, bool]:
        return {name: self.state.backends[name].available for name in KINDS}


def _index_needs(doc: dict) -> dict[str, dict]:
    """Index a ``needs.json`` by need id.

    sphinx-needs writes ``{"versions": {"<v>": {"needs": {...}}}}``; older and
    hand-written files sometimes carry a bare ``needs`` mapping.  Both are
    accepted, and the *current* version wins when several are present.
    """
    needs: dict[str, dict] = {}
    versions = doc.get("versions")
    if isinstance(versions, dict) and versions:
        current = doc.get("current_version")
        keys = [current] if current in versions else sorted(versions)
        for key in keys:
            entry = versions.get(key) or {}
            needs.update(entry.get("needs") or {})
    needs.update(doc.get("needs") or {})
    return {str(k): v for k, v in needs.items() if isinstance(v, dict)}
