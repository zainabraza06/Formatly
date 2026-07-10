"""Node-level diff between two document graphs."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.docos.graph import DocumentGraph


@dataclass
class GraphDiff:
    added: list[dict[str, Any]] = field(default_factory=list)
    removed: list[dict[str, Any]] = field(default_factory=list)
    changed: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"added": self.added, "removed": self.removed, "changed": self.changed}


def diff_graphs(a: DocumentGraph, b: DocumentGraph) -> GraphDiff:
    """Diff `a` (before) against `b` (after) by node id."""
    ia = {n.id: n for n in a.nodes()}
    ib = {n.id: n for n in b.nodes()}
    diff = GraphDiff()

    for nid, nb in ib.items():
        if nid not in ia:
            diff.added.append({"id": nid, "type": nb.type.value, "content": nb.content[:120]})

    for nid, na in ia.items():
        nb = ib.get(nid)
        if nb is None:
            diff.removed.append({"id": nid, "type": na.type.value, "content": na.content[:120]})
            continue
        changes: dict[str, Any] = {}
        if na.content != nb.content:
            changes["content"] = {"before": na.content[:120], "after": nb.content[:120]}
        sa = na.style.model_dump(exclude_none=True)
        sb = nb.style.model_dump(exclude_none=True)
        if sa != sb:
            changes["style"] = {"before": sa, "after": sb}
        if changes:
            diff.changed.append({"id": nid, "type": nb.type.value, **changes})

    return diff
