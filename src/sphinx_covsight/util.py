"""Small helpers shared across modules."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from sphinx.environment import BuildEnvironment

_SLUG_STRIP_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    """``"All supported divisor values"`` -> ``"all_supported_divisor_values"``."""
    slug = _SLUG_STRIP_RE.sub("_", text.strip().lower()).strip("_")
    return slug or "unnamed"


def split_list(value: str | None) -> list[str]:
    """Split a comma- and/or newline-separated option value."""
    if not value:
        return []
    return [item.strip() for item in re.split(r"[,\n]", value) if item.strip()]


def document_order(env: BuildEnvironment) -> dict[str, int]:
    """Map docname -> position in the toctree, then by name for orphans.

    Extraction orders goals by document order, which is the order a reader
    meets them in the rendered document — not alphabetical docname order.
    """
    order: dict[str, int] = {}
    root = getattr(env, "config", None) and env.config.root_doc or "index"

    def visit(docname: str) -> None:
        if docname in order:
            return
        order[docname] = len(order)
        for child in getattr(env, "toctree_includes", {}).get(docname, []):
            visit(child)

    if root in getattr(env, "found_docs", set()):
        visit(root)
    for docname in sorted(getattr(env, "found_docs", set())):
        visit(docname)
    return order
