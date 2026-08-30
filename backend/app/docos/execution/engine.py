"""Execution Engine — the sole mutator of the document graph.

Applies a validated ActionBatch to a *clone* of the graph while streaming granular
events. Execution is atomic: if any action fails, the clone is discarded and the
caller keeps the original graph (rollback on failure — no version is committed).
"""
from __future__ import annotations

from typing import Iterator

from app.docos.actions import Action, ActionBatch, ActionType
from app.docos.execution.events import Event, EventName
from app.docos.graph import DocumentGraph, Node, NodeType, Style


class ExecutionError(Exception):
    def __init__(self, action_index: int, message: str):
        self.action_index = action_index
        self.message = message
        super().__init__(f"action[{action_index}]: {message}")


class ExecutionResult:
    def __init__(self, graph: DocumentGraph, events: list[Event], ok: bool, error: str = ""):
        self.graph = graph
        self.events = events
        self.ok = ok
        self.error = error


def _style_of(action: Action) -> Style:
    """The formatting an action asks for, wherever the planner put it.

    The schema has a `style` field, and a planner that has just been told to
    put the words in `params.find` will cheerfully put `bold` next to them.
    Reading only `style` meant a correct plan applied an empty patch and
    reported that nothing changed.
    """
    if action.style and action.style.model_dump(exclude_none=True):
        return action.style

    loose = {key: value for key, value in (action.params or {}).items()
             if key in Style.model_fields}
    nested = (action.params or {}).get("style") or {}
    if isinstance(nested, dict):
        loose.update({k: v for k, v in nested.items() if k in Style.model_fields})
    return Style.model_validate(loose)


class ExecutionEngine:
    """Stateless. `stream` yields events lazily; `execute` collects them."""

    def execute(self, graph: DocumentGraph, batch: ActionBatch) -> ExecutionResult:
        events: list[Event] = []
        working = graph.clone()
        try:
            for ev in self._run(working, batch):
                events.append(ev)
            return ExecutionResult(working, events, ok=True)
        except ExecutionError as exc:
            events.append(Event(name=EventName.BATCH_FAILED,
                                payload={"index": exc.action_index, "error": exc.message}))
            # rollback: return the untouched original graph
            return ExecutionResult(graph, events, ok=False, error=exc.message)

    def stream(self, graph: DocumentGraph, batch: ActionBatch) -> Iterator[Event]:
        """Yield events against a clone. The final graph is available via `execute`;
        this variant is for pure event streaming where the caller re-runs `execute`
        to obtain the committed graph."""
        yield from self._run(graph.clone(), batch)

    # ── core loop ───────────────────────────────────────────────────────────
    def _run(self, g: DocumentGraph, batch: ActionBatch) -> Iterator[Event]:
        yield Event(name=EventName.BATCH_STARTED,
                    payload={"count": len(batch.actions), "reasoning": batch.reasoning})
        selection: list[str] = []

        for i, action in enumerate(batch.actions):
            handler = self._HANDLERS.get(action.type)
            if handler is None:
                raise ExecutionError(i, f"unsupported action '{action.type.value}'")
            selection = yield from handler(self, g, action, i, selection)

        yield Event(name=EventName.BATCH_FINISHED, payload={"count": len(batch.actions)})

    # ── scope resolution ────────────────────────────────────────────────────
    def scope_of(self, g: DocumentGraph, action: Action) -> list[Node]:
        """What an action would work on. Lets a caller tell "found nothing to do"
        from "found nothing", which read the same to anyone watching."""
        return self._scope(g, action, [])

    @staticmethod
    def _scope(g: DocumentGraph, action: Action, selection: list[str]) -> list[Node]:
        if action.node_ids:
            return [n for nid in action.node_ids if (n := g.get(nid))]
        if action.target:
            return g.resolve_target(action.target)
        if selection:
            return [n for nid in selection if (n := g.get(nid))]
        return []

    # ── handlers (each yields events and returns the new selection) ─────────
    def _h_select(self, g, action, i, selection) -> Iterator[Event]:
        nodes = self._scope(g, action, selection)
        yield Event(name=EventName.SELECTION_STARTED,
                    payload={"target": action.target, "total": len(nodes)})
        ids = []
        for k, n in enumerate(nodes):
            ids.append(n.id)
            yield Event(name=EventName.SELECTION_ITEM,
                        payload={"id": n.id, "type": n.type.value,
                                 "index": k, "preview": n.content[:80]})
        yield Event(name=EventName.SELECTION_FINISHED, payload={"ids": ids})
        return ids

    def _h_format(self, g, action, i, selection) -> Iterator[Event]:
        nodes = self._scope(g, action, selection)
        patch = _style_of(action)
        yield Event(name=EventName.FORMAT_STARTED,
                    payload={"target": action.target, "total": len(nodes),
                             "style": patch.model_dump(exclude_none=True)})
        # A phrase, or the whole paragraph. "Bold results in the abstract" means
        # the word; styling the node was all an action could do, so it bolded
        # the paragraph the word sits in and everything else in it.
        find = str(action.params.get("find") or "").strip()
        # Spans a model picked out for a description the request gave instead of
        # a quotation — "the results", rather than "the word results". Resolved
        # before execution and recorded on the action, so replaying this version
        # formats the same words without asking again.
        described: dict[str, list[str]] = {}
        for span in action.params.get("spans") or []:
            if isinstance(span, dict) and span.get("id") and span.get("text"):
                described.setdefault(str(span["id"]), []).append(str(span["text"]))

        for k, n in enumerate(nodes):
            if described:
                if not sum(n.style_span(text, patch) for text in described.get(n.id, [])):
                    continue
            elif find:
                if not n.style_span(find, patch):
                    continue
            else:
                n.apply_style(patch)
            yield Event(name=EventName.FORMAT_PROGRESS,
                        payload={"id": n.id, "index": k, "total": len(nodes),
                                 "style": n.style.model_dump(exclude_none=True)})
        yield Event(name=EventName.FORMAT_FINISHED, payload={"count": len(nodes)})
        return [n.id for n in nodes]

    def _h_highlight(self, g, action, i, selection) -> Iterator[Event]:
        color = action.params.get("color") or (action.style.highlight if action.style else None) or "#fff59d"
        nodes = self._scope(g, action, selection)
        yield Event(name=EventName.FORMAT_STARTED,
                    payload={"target": action.target, "total": len(nodes), "highlight": color})
        for k, n in enumerate(nodes):
            n.apply_style(Style(highlight=color))
            yield Event(name=EventName.FORMAT_PROGRESS,
                        payload={"id": n.id, "index": k, "highlight": color})
        yield Event(name=EventName.FORMAT_FINISHED, payload={"count": len(nodes)})
        return [n.id for n in nodes]

    def _h_align(self, g, action, i, selection) -> Iterator[Event]:
        alignment = action.params.get("alignment") or (action.style.alignment if action.style else "left")
        return (yield from self._apply_style(g, action, selection, Style(alignment=alignment)))

    def _h_justify(self, g, action, i, selection) -> Iterator[Event]:
        return (yield from self._apply_style(g, action, selection, Style(alignment="justify")))

    def _h_resize(self, g, action, i, selection) -> Iterator[Event]:
        size = action.params.get("font_size") or (action.style.font_size if action.style else None)
        return (yield from self._apply_style(g, action, selection, Style(font_size=size)))

    def _apply_style(self, g, action, selection, patch: Style) -> Iterator[Event]:
        nodes = self._scope(g, action, selection)
        yield Event(name=EventName.FORMAT_STARTED,
                    payload={"target": action.target, "total": len(nodes),
                             "style": patch.model_dump(exclude_none=True)})
        for k, n in enumerate(nodes):
            n.apply_style(patch)
            yield Event(name=EventName.FORMAT_PROGRESS, payload={"id": n.id, "index": k})
        yield Event(name=EventName.FORMAT_FINISHED, payload={"count": len(nodes)})
        return [n.id for n in nodes]

    def _h_delete(self, g, action, i, selection) -> Iterator[Event]:
        nodes = self._scope(g, action, selection)
        yield Event(name=EventName.DELETE_STARTED,
                    payload={"target": action.target, "total": len(nodes)})
        removed = 0
        for n in nodes:
            if g.remove(n.id):
                removed += 1
                yield Event(name=EventName.DELETE_ITEM, payload={"id": n.id, "type": n.type.value})
        yield Event(name=EventName.DELETE_FINISHED, payload={"count": removed})
        return []

    def _h_replace(self, g, action, i, selection) -> Iterator[Event]:
        find = str(action.params.get("find", ""))
        repl = str(action.params.get("with", ""))
        nodes = self._scope(g, action, selection)
        yield Event(name=EventName.REPLACE_STARTED,
                    payload={"find": find, "with": repl, "total": len(nodes)})
        changed = 0
        for n in nodes:
            if find and n.replace_text(find, repl):
                changed += 1
                yield Event(name=EventName.REPLACE_ITEM, payload={"id": n.id, "preview": n.content[:80]})
        yield Event(name=EventName.REPLACE_FINISHED, payload={"count": changed})
        return [n.id for n in nodes]

    def _h_insert(self, g, action, i, selection) -> Iterator[Event]:
        p = action.params
        try:
            ntype = NodeType(p.get("node_type", "body"))
        except ValueError:
            raise ExecutionError(i, f"invalid node_type '{p.get('node_type')}'")
        node = Node(type=ntype, content=str(p.get("content", "")),
                    style=action.style or Style())
        yield Event(name=EventName.INSERT_STARTED, payload={"node_type": ntype.value})
        after = p.get("after_id") or (action.node_ids[0] if action.node_ids else None)
        if after and g.insert_after(after, node):
            pass
        else:
            g.root.children.append(node)
        yield Event(name=EventName.INSERT_ITEM, payload={"id": node.id, "type": ntype.value})
        yield Event(name=EventName.INSERT_FINISHED, payload={"id": node.id})
        return [node.id]

    def _h_move(self, g, action, i, selection) -> Iterator[Event]:
        to = action.params.get("to_id")
        nodes = self._scope(g, action, selection)
        yield Event(name=EventName.MOVE_STARTED, payload={"total": len(nodes), "to_id": to})
        moved = 0
        for n in nodes:
            if to and g.move_to_end(n.id, to):
                moved += 1
                yield Event(name=EventName.MOVE_ITEM, payload={"id": n.id, "to_id": to})
        yield Event(name=EventName.MOVE_FINISHED, payload={"count": moved})
        return [n.id for n in nodes]

    def _h_render_maths(self, g, action, i, selection) -> Iterator[Event]:
        """Draw the document's LaTeX as mathematics, or stop drawing it.

        Nothing about the words changes: the same characters are still there,
        and turning this off gives back exactly what the author typed. That is
        the whole point of doing it this way — asking a model to convert the
        equations rewrote them into prose, which cannot be undone by looking
        at the result.
        """
        on = action.params.get("on", True) is not False
        page = g.root.metadata.setdefault("page", {})
        if isinstance(page, dict):
            page["render_maths"] = on
        g.root.metadata["render_maths"] = on
        yield Event(name=EventName.FORMAT_FINISHED,
                    payload={"render_maths": on, "count": 1})
        return []

    def _h_normalize(self, g, action, i, selection) -> Iterator[Event]:
        # Clear highlight and unify to a base style across the scope.
        nodes = self._scope(g, action, selection)
        yield Event(name=EventName.FORMAT_STARTED, payload={"normalize": True, "total": len(nodes)})
        for k, n in enumerate(nodes):
            n.style.highlight = None
            yield Event(name=EventName.FORMAT_PROGRESS, payload={"id": n.id, "index": k})
        yield Event(name=EventName.FORMAT_FINISHED, payload={"count": len(nodes)})
        return [n.id for n in nodes]

    def _h_rewrite(self, g, action, i, selection) -> Iterator[Event]:
        """Apply the new text a rewrite resolved to.

        The text itself comes from a model that had to be shown the document,
        which is I/O the executor does not do — so the service resolves it first
        and records the result in `params.edits`. Carrying the resolved text
        rather than the instruction is what makes the action replayable: a
        version is stored as its action log and replayed to materialise the
        graph, and asking a model again would give different words every time.
        """
        edits = action.params.get("edits") or {}
        if not isinstance(edits, dict):
            edits = {}

        yield Event(name=EventName.FORMAT_STARTED,
                    payload={"rewrite": True, "total": len(edits)})
        touched: list[str] = []
        for node_id, text in edits.items():
            node = g.get(node_id)
            if node is not None and isinstance(text, str) and text.strip():
                # New words: whatever formatted the old ones no longer applies.
                node.set_text(text)
                touched.append(node_id)
                yield Event(name=EventName.FORMAT_PROGRESS,
                            payload={"id": node_id, "index": len(touched) - 1})
        yield Event(name=EventName.FORMAT_FINISHED, payload={"count": len(touched)})
        return touched

    def _h_merge(self, g, action, i, selection) -> Iterator[Event]:
        nodes = self._scope(g, action, selection)
        if len(nodes) < 2:
            raise ExecutionError(i, "merge needs at least two nodes")
        first, rest = nodes[0], nodes[1:]
        first.set_text(" ".join([first.content, *[n.content for n in rest]]).strip())
        for n in rest:
            g.remove(n.id)
        yield Event(name=EventName.FORMAT_FINISHED, payload={"merged_into": first.id, "count": len(rest)})
        return [first.id]

    def _h_split(self, g, action, i, selection) -> Iterator[Event]:
        sep = str(action.params.get("separator", ". "))
        nodes = self._scope(g, action, selection)
        new_ids: list[str] = []
        for n in nodes:
            parts = [p for p in n.content.split(sep) if p.strip()]
            if len(parts) < 2:
                continue
            n.set_text(parts[0])
            prev = n.id
            for part in parts[1:]:
                clone = Node(type=n.type, content=part, style=n.style.model_copy())
                g.insert_after(prev, clone)
                prev = clone.id
                new_ids.append(clone.id)
        yield Event(name=EventName.INSERT_FINISHED, payload={"created": new_ids})
        return new_ids

    def _h_copy(self, g, action, i, selection) -> Iterator[Event]:
        nodes = self._scope(g, action, selection)
        yield Event(name=EventName.SELECTION_FINISHED,
                    payload={"ids": [n.id for n in nodes], "clipboard": True})
        return [n.id for n in nodes]

    def _h_paste(self, g, action, i, selection) -> Iterator[Event]:
        after = action.params.get("after_id")
        for nid in list(selection):
            src = g.get(nid)
            if not src:
                continue
            dup = Node(type=src.type, content=src.content, style=src.style.model_copy(),
                       metadata=dict(src.metadata),
                       # A copy of a paragraph is formatted like the original.
                       runs=[r.model_copy(deep=True) for r in src.runs])
            if after and g.insert_after(after, dup):
                after = dup.id
            else:
                g.root.children.append(dup)
            yield Event(name=EventName.INSERT_ITEM, payload={"id": dup.id, "type": dup.type.value})
        return selection

    _HANDLERS = {
        ActionType.SELECT: _h_select,
        ActionType.FORMAT: _h_format,
        ActionType.HIGHLIGHT: _h_highlight,
        ActionType.ALIGN: _h_align,
        ActionType.JUSTIFY: _h_justify,
        ActionType.RESIZE: _h_resize,
        ActionType.DELETE: _h_delete,
        ActionType.REPLACE: _h_replace,
        ActionType.INSERT: _h_insert,
        ActionType.MOVE: _h_move,
        ActionType.NORMALIZE: _h_normalize,
        ActionType.RENDER_MATHS: _h_render_maths,
        ActionType.REWRITE: _h_rewrite,
        ActionType.MERGE: _h_merge,
        ActionType.SPLIT: _h_split,
        ActionType.COPY: _h_copy,
        ActionType.PASTE: _h_paste,
    }
