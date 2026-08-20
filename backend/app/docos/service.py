"""DocOS orchestration service — wires the four engines together.

This is the application/service layer the API depends on. It owns no HTTP concerns
and no storage details; it composes Document, Command, Execution and Version engines.
"""
from __future__ import annotations

from typing import Any, Awaitable, Callable, Optional

from app.docos.command import CommandEngine, ControlOp
from app.docos.execution import ExecutionEngine
from app.docos.graph import DocumentGraph
from app.docos.parser import parse_docx_bytes, repaginate
from app.docos.versioning import VersionEngine
from app.services.storage import new_id

Emit = Callable[[dict[str, Any]], Awaitable[None]]


class DocOSService:
    def __init__(
        self,
        versions: Optional[VersionEngine] = None,
        commands: Optional[CommandEngine] = None,
        executor: Optional[ExecutionEngine] = None,
    ):
        self.versions = versions or VersionEngine()
        self.commands = commands or CommandEngine()
        self.executor = executor or ExecutionEngine()

    # ── ownership ─────────────────────────────────────────────────────────
    def _require_owner(self, doc_id: str, owner_id: Optional[str]) -> dict[str, Any]:
        doc = self.versions.store.get_document(doc_id)
        if not doc:
            raise KeyError(doc_id)
        if owner_id is not None and doc.get("owner_id") not in (None, owner_id):
            raise PermissionError("not your document")
        return doc

    def list_documents(self, owner_id: Optional[str]) -> list[dict[str, Any]]:
        out = []
        for doc in self.versions.store.list_documents(owner_id=owner_id):
            versions = self.versions.store.list_versions(doc["id"])
            out.append({
                "document_id": doc["id"],
                "title": doc["title"],
                "created_at": doc["created_at"],
                "current_version": doc["current_version"],
                "versions": len(versions),
            })
        return out

    # ── import / read ─────────────────────────────────────────────────────
    def import_docx(self, data: bytes, *, title: str = "", user: str = "user",
                    owner_id: Optional[str] = None) -> dict[str, Any]:
        doc_id = new_id("doc")
        graph = parse_docx_bytes(data, title=title)
        graph.title = title or "Untitled"
        # Exact pagination via LibreOffice when available; silently keeps the
        # marker heuristic otherwise.
        exact_pages: Optional[int] = None
        try:
            exact_pages = repaginate(graph, data)
        except Exception:
            exact_pages = None
        info = self.versions.init_document(doc_id, graph.title, graph, user=user, owner_id=owner_id)
        return {"document_id": doc_id, "title": graph.title,
                "version": info.to_dict(), "graph": graph.to_dict(),
                "exact_pages": exact_pages}

    def import_spec(self, spec: Any, *, title: str = "", user: str = "user",
                    owner_id: Optional[str] = None) -> dict[str, Any]:
        """Import a composed document without rendering it to .docx first.

        Going through a file would flatten what the spec knows — a listing into
        loose paragraphs, an equation into whatever characters it typeset to —
        because DOCX has no word for either. Converting directly keeps them.
        """
        from app.paper.to_graph import spec_to_graph

        doc_id = new_id("doc")
        graph = spec_to_graph(spec, title=title)
        graph.title = title or graph.title or "Untitled"
        info = self.versions.init_document(doc_id, graph.title, graph,
                                           user=user, owner_id=owner_id)
        return {"document_id": doc_id, "title": graph.title,
                "version": info.to_dict(), "graph": graph.to_dict(),
                "exact_pages": None}

    def get_document(self, doc_id: str, owner_id: Optional[str] = None) -> dict[str, Any]:
        doc = self._require_owner(doc_id, owner_id)
        graph = self.versions.current_graph(doc_id)
        return {"document_id": doc_id, "title": graph.title,
                "current_version": doc["current_version"] if doc else None,
                "graph": graph.to_dict()}

    def history(self, doc_id: str, owner_id: Optional[str] = None) -> list[dict[str, Any]]:
        self._require_owner(doc_id, owner_id)
        return [v.to_dict() for v in self.versions.history(doc_id)]

    def diff(self, doc_id: str, seq_a: int, seq_b: int, owner_id: Optional[str] = None) -> dict[str, Any]:
        self._require_owner(doc_id, owner_id)
        va, vb = self._version_by_seq(doc_id, seq_a), self._version_by_seq(doc_id, seq_b)
        return self.versions.diff(va, vb).to_dict()

    # ── command execution (streams events via `emit`) ─────────────────────
    async def run_command(self, doc_id: str, command: str, emit: Emit,
                          *, user: str = "user", owner_id: Optional[str] = None) -> dict[str, Any]:
        self._require_owner(doc_id, owner_id)
        graph = self.versions.current_graph(doc_id)
        result = self.commands.parse(command, graph)

        if result.kind == "control":
            return await self._run_control(doc_id, result.control, emit)  # type: ignore[arg-type]

        batch = result.batch
        assert batch is not None
        await emit({"event": "command_parsed",
                    "payload": {"source": result.source, "provider": result.provider,
                                "reasoning": batch.reasoning,
                                "actions": [a.model_dump(exclude_none=True) for a in batch.actions]}})

        exec_result = self.executor.execute(graph, batch)
        for ev in exec_result.events:
            await emit(ev.to_message())

        if not exec_result.ok:
            return {"ok": False, "error": exec_result.error}

        info = self.versions.commit(doc_id, batch, exec_result.graph, user=user)
        await emit({"event": "version_committed", "payload": info.to_dict()})
        return {"ok": True, "version": info.to_dict(), "graph": exec_result.graph.to_dict()}

    async def _run_control(self, doc_id: str, op: ControlOp, emit: Emit) -> dict[str, Any]:
        kind = op.kind
        if kind == "undo":
            info = self.versions.undo(doc_id)
        elif kind == "redo":
            info = self.versions.redo(doc_id)
        elif kind == "rewind":
            info = self.versions.rewind(doc_id, self._version_by_seq(doc_id, op.params["seq"]))
        elif kind == "restore":
            info = self.versions.restore(doc_id, self._version_by_seq(doc_id, op.params["seq"]))
        elif kind == "compare":
            diff = self.diff(doc_id, op.params["a"], op.params["b"])
            await emit({"event": "compare_result",
                        "payload": {"a": op.params["a"], "b": op.params["b"], "diff": diff}})
            return {"ok": True, "control": "compare", "diff": diff}
        else:
            return {"ok": False, "error": f"unknown control op {kind}"}

        if info is None:
            await emit({"event": "control_noop", "payload": {"op": kind}})
            return {"ok": False, "error": f"{kind} not possible"}

        graph = self.versions.current_graph(doc_id)
        await emit({"event": "version_changed",
                    "payload": {"op": kind, "version": info.to_dict()}})
        return {"ok": True, "control": kind, "version": info.to_dict(), "graph": graph.to_dict()}

    # ── helpers ───────────────────────────────────────────────────────────
    def _version_by_seq(self, doc_id: str, seq: int) -> str:
        for row in self.versions.store.list_versions(doc_id):
            if row.seq == seq:
                return row.id
        raise KeyError(f"document {doc_id} has no version with seq {seq}")


_service: DocOSService | None = None


def get_service() -> DocOSService:
    global _service
    if _service is None:
        _service = DocOSService()
    return _service
