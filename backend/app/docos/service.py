"""DocOS orchestration service — wires the four engines together.

This is the application/service layer the API depends on. It owns no HTTP concerns
and no storage details; it composes Document, Command, Execution and Version engines.
"""
from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable, Optional

import anyio
import anyio.to_thread

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
        # What has been read of each document, by heading. Survives edits,
        # because it describes what a section is about rather than its words.
        self._readings: dict[str, dict[str, str]] = {}

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

    async def read_document(self, doc_id: str, emit: Emit,
                            owner_id: Optional[str] = None) -> dict[str, Any]:
        """Read the document once so later instructions arrive with context.

        Streamed page by page: the reader sees where the assistant is, and the
        pages it could not read are named rather than quietly missing.
        """
        from app.docos.command.reading import brief_with_reading, read_document
        from app.services.router import get_router

        self._require_owner(doc_id, owner_id)
        graph = self.versions.current_graph(doc_id)
        loop = asyncio.get_running_loop()

        def on_progress(info: dict) -> None:
            asyncio.run_coroutine_threadsafe(
                emit({"event": "reading_progress", "payload": info}), loop)

        await emit({"event": "reading_started", "payload": {"document_id": doc_id}})
        about, failures = await anyio.to_thread.run_sync(
            lambda: read_document(graph, router=get_router(), on_progress=on_progress))

        # Kept on the document, not the version: it describes the document as a
        # whole and would otherwise be re-read after every edit.
        self._readings[doc_id] = about
        brief = brief_with_reading(graph, about)
        await emit({"event": "reading_finished",
                    "payload": {"sections": len(brief.get("sections", [])),
                                "read": len(about), "warnings": failures}})
        return {"ok": True, "brief": brief, "warnings": failures}

    def brief(self, doc_id: str, owner_id: Optional[str] = None) -> dict[str, Any]:
        """What the document is, with whatever has been read of it."""
        from app.docos.command.reading import brief_with_reading

        self._require_owner(doc_id, owner_id)
        graph = self.versions.current_graph(doc_id)
        return brief_with_reading(graph, self._readings.get(doc_id, {}))

    def delete_document(self, doc_id: str, owner_id: Optional[str] = None) -> bool:
        """Delete one of the caller's own documents, with all its history.

        Ownership is checked first, so a stranger's id is a 403 and an unknown
        id is a 404 — neither silently reports success.
        """
        self._require_owner(doc_id, owner_id)
        return self.versions.store.delete_document(doc_id)

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

    def current_graph(self, doc_id: str, owner_id: Optional[str] = None):
        """The document's current graph, if it belongs to this user."""
        self._require_owner(doc_id, owner_id)
        return self.versions.current_graph(doc_id)

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
        result = self.commands.parse(command, graph, self._readings.get(doc_id))

        if result.kind == "control":
            return await self._run_control(doc_id, result.control, emit)  # type: ignore[arg-type]

        batch = result.batch
        assert batch is not None

        # A request that names a part of the document is pinned to that part.
        # The planner is given the sections and what each is about and still
        # answers "the part about the results" with a target that happens to
        # share a word with it, so the match is made here instead.
        placed = self._place_in_section(command, graph, doc_id, batch)
        if placed is not None:
            await emit({"event": "section_located",
                        "payload": {"heading": placed["heading"],
                                    "about": placed.get("about"),
                                    "nodes": len(placed["node_ids"])}})
        await emit({"event": "command_parsed",
                    "payload": {"source": result.source, "provider": result.provider,
                                "reasoning": batch.reasoning,
                                "actions": [a.model_dump(exclude_none=True) for a in batch.actions]}})

        # A text instruction is resolved before the structural actions run: it
        # needs the document's own words, which the planner never sees.
        rewrite_edits, rewrite_failures = await self._apply_rewrites(
            graph, batch, emit, command)

        exec_result = self.executor.execute(graph, batch)
        for ev in exec_result.events:
            await emit(ev.to_message())

        if not exec_result.ok:
            return {"ok": False, "error": exec_result.error}

        changed = _changed_node_ids(graph, exec_result.graph)

        # The planner is inconsistent about which op a text instruction needs:
        # the same request comes back as `rewrite` one run and as `replace` with
        # a regex the next, and this system's replace is literal-only, so that
        # one silently matches nothing. Rather than keep tuning the prompt, the
        # capable path runs when the cheap one turns out to have done nothing.
        if not changed and _wanted_text_change(batch):
            await emit({"event": "rewrite_fallback",
                        "payload": {"reason": "the planned edit matched nothing"}})
            from app.docos.actions import Action, ActionType

            # The whole document, not just its body paragraphs. This runs
            # because the planned edit matched nothing, so narrowing the second
            # attempt to where the first already failed to find anything is how
            # an instruction about equations — which live in table cells and
            # captions — came back "done" with the document untouched.
            rewrite_edits, more_failures = await self._rewrite_scope(
                graph, None, None, command, emit)
            rewrite_failures.extend(more_failures)
            if rewrite_edits:
                batch.actions.append(Action(type=ActionType.REWRITE, target="body",
                                            params={"edits": rewrite_edits}))
                exec_result = self.executor.execute(graph, batch)
                for ev in exec_result.events:
                    await emit(ev.to_message())
                changed = _changed_node_ids(graph, exec_result.graph)

        if not changed and not rewrite_edits:
            # Nothing moved. Saying "done" here is how an instruction that
            # matched nothing came to look like it had worked.
            message = "nothing matched, so nothing changed"
            if rewrite_failures:
                message += " (" + "; ".join(rewrite_failures[:3]) + ")"
            await emit({"event": "command_noop", "payload": {"reason": message}})
            return {"ok": False, "error": message, "graph": graph.to_dict()}

        info = self.versions.commit(doc_id, batch, exec_result.graph, user=user)
        await emit({"event": "version_committed", "payload": info.to_dict()})
        return {"ok": True, "version": info.to_dict(), "graph": exec_result.graph.to_dict(),
                "changed": len(changed),
                "warnings": rewrite_failures}

    async def _apply_rewrites(self, graph, batch, emit,
                              command: str) -> tuple[dict[str, str], list[str]]:
        """Run any `rewrite` actions against the graph, in place.

        The resolved text is recorded on the action rather than applied here:
        the executor stays the only mutator, and a version log that carries the
        words can be replayed without asking a model again.
        """
        from app.docos.actions import ActionType

        actions = [a for a in batch.actions if a.type == ActionType.REWRITE]
        if not actions:
            return {}, []

        all_edits: dict[str, str] = {}
        all_failures: list[str] = []
        for action in actions:
            # The planner is asked to restate the request in params.instruction,
            # but it often just emits the action. The user's own words are the
            # instruction, so falling back to them is right rather than a guess.
            instruction = str(action.params.get("instruction") or "").strip() or command.strip()
            if not instruction:
                all_failures.append("a rewrite action arrived with no instruction")
                continue

            # The planner fills in a target whether or not the request named
            # one, and it nearly always guesses "body". "Convert every equation"
            # then reached the equations in body paragraphs and silently skipped
            # the ones in table cells and captions. A scope the user did not ask
            # for is not a scope: unless they named one, or picked nodes
            # themselves, the rewrite covers the document. The rewriter is told
            # to leave passages the instruction does not cover alone, so a wider
            # scope changes what it *can* reach, not what it *will* touch.
            target = action.target if (action.node_ids or _names_a_scope(command)) else None
            edits, failures = await self._rewrite_scope(
                graph, action.node_ids, target, instruction, emit)
            # Recorded on the action so the executor applies it and the version
            # log can be replayed without asking a model again.
            if edits:
                action.params["edits"] = edits
            all_edits.update(edits)
            all_failures.extend(failures)
        return all_edits, all_failures

    async def _rewrite_scope(self, graph, node_ids, target, instruction,
                             emit) -> tuple[dict[str, str], list[str]]:
        """Rewrite the text nodes in scope, applying the edits to `graph`."""
        from app.docos.command.rewriter import rewrite_nodes, rewritable
        from app.services.router import get_router

        nodes = rewritable(graph, node_ids or [], target)
        if not nodes:
            return {}, ["no text nodes were in scope"]

        loop = asyncio.get_running_loop()

        def on_progress(info: dict) -> None:
            asyncio.run_coroutine_threadsafe(
                emit({"event": "rewrite_progress", "payload": info}), loop)

        edits, failures = await anyio.to_thread.run_sync(
            lambda: rewrite_nodes(graph, nodes, instruction,
                                  router=get_router(), on_progress=on_progress))

        if edits or failures:
            await emit({"event": "rewrite_finished",
                        "payload": {"edited": len(edits), "warnings": failures}})
        return edits, failures

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

    def _place_in_section(self, command: str, graph, doc_id: str,
                          batch) -> Optional[dict[str, Any]]:
        """Pin a plan to the section the request names, if it names one.

        Only actions the planner left unplaced are pinned: one that already
        names its nodes has been told where to work, and a plan of several
        actions is not second-guessed.
        """
        from app.docos.command.locate import locate_section
        from app.docos.command.reading import brief_with_reading

        unplaced = [a for a in batch.actions if not a.node_ids]
        if not unplaced or len(batch.actions) > 2:
            return None

        section = locate_section(
            command, brief_with_reading(graph, self._readings.get(doc_id, {})))
        if section is None:
            return None

        for action in unplaced:
            action.node_ids = list(section["node_ids"])
            action.target = None
        return section

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


def _changed_node_ids(before: DocumentGraph, after: DocumentGraph) -> set[str]:
    """Ids whose content, style or presence differs between two graphs."""
    a = {n.id: n for n in before.nodes()}
    b = {n.id: n for n in after.nodes()}
    changed = set(a) ^ set(b)
    for nid in set(a) & set(b):
        if (a[nid].content != b[nid].content
                or a[nid].style.model_dump() != b[nid].style.model_dump()):
            changed.add(nid)
    return changed


# The words a request uses when it means one part of the document. "Table" and
# "figure" are here because "reword the table captions" is a scope; "equation"
# is not, because an equation is a thing to change, not a place to look.
_SCOPE_WORDS = (
    "body", "paragraph", "heading", "subheading", "title", "caption", "reference",
    "bibliography", "footnote", "table", "figure", "abstract", "header", "footer",
    "selected", "selection", "this section",
)


def _names_a_scope(command: str) -> bool:
    """Did the request name a part of the document to work on?"""
    lowered = (command or "").lower()
    return any(word in lowered for word in _SCOPE_WORDS)


def _wanted_text_change(batch) -> bool:
    """Did this batch try to change the document's words?

    `replace` counts: the planner reaches for it when it means a transformation,
    and this system's replace is literal-only, so it is exactly the case that
    quietly matches nothing.
    """
    from app.docos.actions import ActionType

    return any(a.type in (ActionType.REPLACE, ActionType.REWRITE) for a in batch.actions)
