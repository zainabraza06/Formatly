"""Version Engine — history, undo/redo/rewind, branching, restore, diff.

Storage strategy (per spec): every Nth version stores a full snapshot; versions in
between store only the action batch that produced them. A version's graph is
materialised by loading its nearest checkpoint ancestor and replaying the action
batches forward along the parent chain. Branching is implicit: committing onto a
historical parent simply creates another child of that parent.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from app.docos.actions import ActionBatch, validate_batch
from app.docos.execution import ExecutionEngine
from app.docos.graph import DocumentGraph
from app.docos.versioning.diff import GraphDiff, diff_graphs
from app.docos.versioning.store import VersionRow, VersionStore
from app.services.storage import new_id

SNAPSHOT_EVERY = 10


@dataclass
class VersionInfo:
    id: str
    parent_id: Optional[str]
    seq: int
    timestamp: str
    user: str
    label: str
    is_checkpoint: bool
    is_current: bool = False

    @classmethod
    def from_row(cls, row: VersionRow, current: Optional[str]) -> "VersionInfo":
        return cls(
            id=row.id, parent_id=row.parent_id, seq=row.seq, timestamp=row.timestamp,
            user=row.user, label=row.label, is_checkpoint=row.is_checkpoint,
            is_current=(row.id == current),
        )

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__


class VersionEngine:
    def __init__(self, store: Optional[VersionStore] = None):
        self.store = store or VersionStore()
        self._exec = ExecutionEngine()

    # ── lifecycle ───────────────────────────────────────────────────────────
    def init_document(self, doc_id: str, title: str, graph: DocumentGraph,
                      user: str = "user", owner_id: Optional[str] = None) -> VersionInfo:
        """Create a document with its version 0 (the imported DOCX), always a checkpoint."""
        now = _now()
        self.store.create_document(doc_id, title, now, owner_id=owner_id)
        row = VersionRow(
            id=new_id("v"), document_id=doc_id, parent_id=None, seq=0, timestamp=now,
            user=user, label="import", actions={"actions": [], "reasoning": "initial import"},
            snapshot=graph.to_dict(),
        )
        self.store.add_version(row)
        self.store.set_pointers(doc_id, current=row.id, redo=None)
        return VersionInfo.from_row(row, row.id)

    def commit(self, doc_id: str, batch: ActionBatch, result_graph: DocumentGraph,
               *, user: str = "user", label: str = "", parent_id: Optional[str] = None) -> VersionInfo:
        """Record a new version. `parent_id` defaults to the document's current version
        (pass an older id to branch). Clears the redo pointer."""
        doc = self.store.get_document(doc_id)
        if not doc:
            raise KeyError(f"unknown document {doc_id}")
        parent = parent_id or doc["current_version"]
        seq = self.store.next_seq(doc_id)
        checkpoint = (seq % SNAPSHOT_EVERY == 0)
        row = VersionRow(
            id=new_id("v"), document_id=doc_id, parent_id=parent, seq=seq, timestamp=_now(),
            user=user, label=label or (batch.reasoning[:60] if batch.reasoning else "edit"),
            actions=batch.model_dump(),
            snapshot=result_graph.to_dict() if checkpoint else None,
        )
        self.store.add_version(row)
        self.store.set_pointers(doc_id, current=row.id, redo=None)
        return VersionInfo.from_row(row, row.id)

    # ── materialisation ─────────────────────────────────────────────────────
    def materialize(self, version_id: str) -> DocumentGraph:
        """Reconstruct the graph at a given version via checkpoint + replay."""
        target = self.store.get_version(version_id)
        if target is None:
            raise KeyError(f"unknown version {version_id}")

        # build the parent chain root -> ... -> target
        chain: list[VersionRow] = []
        cur: Optional[VersionRow] = target
        while cur is not None:
            chain.append(cur)
            chain_snapshot = cur.snapshot is not None
            if chain_snapshot:
                break
            cur = self.store.get_version(cur.parent_id) if cur.parent_id else None
        chain.reverse()

        if not chain or chain[0].snapshot is None:
            raise RuntimeError(f"no checkpoint reachable from version {version_id}")

        graph = DocumentGraph.from_dict(chain[0].snapshot)
        # replay every version after the checkpoint
        for row in chain[1:]:
            batch = validate_batch(row.actions) if row.actions.get("actions") else ActionBatch()
            if batch.actions:
                res = self._exec.execute(graph, batch)
                graph = res.graph
        return graph

    def current_graph(self, doc_id: str) -> DocumentGraph:
        doc = self.store.get_document(doc_id)
        if not doc or not doc["current_version"]:
            raise KeyError(f"document {doc_id} has no versions")
        return self.materialize(doc["current_version"])

    # ── navigation ──────────────────────────────────────────────────────────
    def undo(self, doc_id: str) -> Optional[VersionInfo]:
        doc = self._doc(doc_id)
        cur = self.store.get_version(doc["current_version"]) if doc["current_version"] else None
        if cur is None or cur.parent_id is None:
            return None
        self.store.set_pointers(doc_id, current=cur.parent_id, redo=cur.id)
        return self._info(doc_id, cur.parent_id)

    def redo(self, doc_id: str) -> Optional[VersionInfo]:
        doc = self._doc(doc_id)
        redo = doc.get("redo_version")
        if not redo:
            return None
        self.store.set_pointers(doc_id, current=redo, redo=None)
        return self._info(doc_id, redo)

    def rewind(self, doc_id: str, version_id: str) -> VersionInfo:
        """Move the current pointer to any historical version (non-destructive)."""
        if self.store.get_version(version_id) is None:
            raise KeyError(f"unknown version {version_id}")
        self.store.set_pointers(doc_id, current=version_id, redo=None)
        return self._info(doc_id, version_id)

    def restore(self, doc_id: str, version_id: str, *, user: str = "user") -> VersionInfo:
        """Create a NEW version whose content equals an old version (keeps history)."""
        graph = self.materialize(version_id)
        batch = ActionBatch(reasoning=f"restore {version_id}")
        return self.commit(doc_id, batch, graph, user=user, label=f"restore→{version_id[:8]}")

    # ── inspection ──────────────────────────────────────────────────────────
    def history(self, doc_id: str) -> list[VersionInfo]:
        doc = self._doc(doc_id)
        current = doc["current_version"]
        return [VersionInfo.from_row(r, current) for r in self.store.list_versions(doc_id)]

    def diff(self, version_a: str, version_b: str) -> GraphDiff:
        return diff_graphs(self.materialize(version_a), self.materialize(version_b))

    # ── helpers ─────────────────────────────────────────────────────────────
    def _doc(self, doc_id: str) -> dict[str, Any]:
        doc = self.store.get_document(doc_id)
        if not doc:
            raise KeyError(f"unknown document {doc_id}")
        return doc

    def _info(self, doc_id: str, version_id: str) -> VersionInfo:
        row = self.store.get_version(version_id)
        assert row is not None
        doc = self.store.get_document(doc_id)
        return VersionInfo.from_row(row, doc["current_version"] if doc else None)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
