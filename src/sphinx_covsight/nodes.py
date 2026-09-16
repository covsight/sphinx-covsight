"""Custom docutils nodes."""

from __future__ import annotations

from typing import Any

from docutils import nodes


class citation_xref(nodes.Inline, nodes.TextElement):
    """A ``prefix:target`` citation awaiting resolution.

    Citations are resolved at ``doctree-resolved`` rather than at parse time:
    the ``sv`` and ``rdl`` domains are not fully populated until every document
    has been read, so resolving during parsing would produce spurious misses on
    incremental builds.  The pass-through visitors below exist only for
    builders that never fire that event — the node renders as its text.
    """


def visit_passthrough(self: Any, node: nodes.Element) -> None:  # pragma: no cover
    pass


def depart_passthrough(self: Any, node: nodes.Element) -> None:  # pragma: no cover
    pass
