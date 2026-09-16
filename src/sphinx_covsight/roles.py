"""Inline citation roles.

``:rule:`UART_3_2_1``` validates an inline reference in prose.  Inline
citations are *not* extracted into ``requirements[]`` — that is what
``.. covers::`` is for — because a citation in the middle of a sentence is
evidence, not an accountability claim.
"""

from __future__ import annotations

from typing import Any

from docutils import nodes

from .nodes import citation_xref


def _citation_role(kind: str):
    def role(
        name: str,
        rawtext: str,
        text: str,
        lineno: int,
        inliner: Any,
        options: dict | None = None,
        content: list | None = None,
    ) -> tuple[list[nodes.Node], list[nodes.system_message]]:
        target = nodes.unescape(text).strip()
        node = citation_xref("", target)
        node["kind"] = kind
        node["target"] = target
        return [node], []

    role.__name__ = f"{kind}_role"
    return role


#: The MVP ships exactly one inline citation role.  ``rdl:`` and ``sv:``
#: targets are authored in ``.. covers::``; their own extensions already
#: provide inline roles (``:rdl:ref:``, ``:sv:class:``) for prose.
ROLES = {
    "rule": _citation_role("rule"),
}
