"""The ``covsight`` domain: anchors and cross-references for plan objects.

Only two object kinds are registered — features and testpoints — because those
are the two things that have an id an author can point at.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import TYPE_CHECKING

from docutils import nodes
from sphinx.domains import Domain, ObjType
from sphinx.roles import XRefRole
from sphinx.util.nodes import make_refnode

from . import logging as cslog

if TYPE_CHECKING:  # pragma: no cover
    from sphinx.builders import Builder
    from sphinx.environment import BuildEnvironment


class CovsightDomain(Domain):
    name = "covsight"
    label = "covsight"

    object_types = {
        "feature": ObjType("feature", "feature"),
        "testpoint": ObjType("testpoint", "tp"),
    }
    roles = {
        "feature": XRefRole(),
        "tp": XRefRole(),
    }
    initial_data = {"objects": {}}  # type: ignore[assignment]

    @property
    def objects(self) -> dict[str, tuple[str, str, str]]:
        # objid -> (docname, anchor, kind)
        return self.data.setdefault("objects", {})

    def note_object(self, kind: str, objid: str, anchor: str, docname: str) -> None:
        self.objects[objid] = (docname, anchor, kind)

    def clear_doc(self, docname: str) -> None:
        for objid, (dn, _anchor, _kind) in list(self.objects.items()):
            if dn == docname:
                del self.objects[objid]

    def merge_domaindata(self, docnames: Iterable[str], otherdata: dict) -> None:
        for objid, data in otherdata.get("objects", {}).items():
            if data[0] in docnames:
                self.objects[objid] = data

    def resolve_xref(
        self,
        env: BuildEnvironment,
        fromdocname: str,
        builder: Builder,
        typ: str,
        target: str,
        node: nodes.Element,
        contnode: nodes.Element,
    ) -> nodes.Element | None:
        entry = self.objects.get(target)
        if entry is None:
            cslog.warn(
                "citation-unresolved",
                f"cannot resolve covsight:{typ} reference {target!r}",
                location=node,
            )
            return None
        docname, anchor, _kind = entry
        return make_refnode(builder, fromdocname, docname, anchor, contnode, target)

    def resolve_any_xref(
        self,
        env: BuildEnvironment,
        fromdocname: str,
        builder: Builder,
        target: str,
        node: nodes.Element,
        contnode: nodes.Element,
    ) -> list[tuple[str, nodes.Element]]:
        entry = self.objects.get(target)
        if entry is None:
            return []
        docname, anchor, kind = entry
        refnode = make_refnode(builder, fromdocname, docname, anchor, contnode, target)
        return [(f"covsight:{kind}", refnode)]

    def get_objects(self) -> Iterator[tuple[str, str, str, str, str, int]]:
        for objid, (docname, anchor, kind) in self.objects.items():
            yield (objid, objid, kind, docname, anchor, 1)
