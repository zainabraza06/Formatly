"""Rewriting the text of a document, a page at a time.

The command planner never sees the document's prose — it is given node counts and
headings so the prompt stays small. That is fine for "centre the images", and
useless for "replace the LaTeX with readable mathematics", which cannot be
answered without reading the text. The planner would emit something plausible,
nothing would match, and the run reported Done.

So a text instruction is planned as one `rewrite` action and resolved here
instead: the nodes in scope are cut into passes small enough to send whole, each
pass goes to the model with its text, and the returned text is applied. Splitting
by pass is what makes it work on a long document — one prompt carrying an entire
paper would truncate, and truncating is how the middle of a document silently
goes unedited.
"""
from __future__ import annotations

import json
import threading
from typing import Any, Callable, Optional

from app.docos.graph import DocumentGraph, Node, NodeType
from app.paper.jsonx import extract_json

# How much text one pass may carry. Small enough that the reply cannot truncate,
# large enough that a normal page goes in a single pass.
_PASS_CHARS = 5000

# Bounded so a reply cannot run past the ceiling and lose the pass.
_MAX_TOKENS = 4000

# Node types whose text is prose the user meant. A caption is included; a table
# cell is not, because rewriting one in isolation loses the row it belonged to.
_TEXT_TYPES = {
    NodeType.BODY, NodeType.PARAGRAPH, NodeType.HEADING, NodeType.SUBHEADING,
    NodeType.CAPTION, NodeType.REFERENCE, NodeType.FOOTNOTE,
}

SYSTEM = """You rewrite the text of a document, one page at a time.

Return ONLY strict JSON. No markdown fences, no commentary.

{"edits": [{"id": "<node id>", "text": "<the rewritten text>"}]}

Rules:
- Apply the instruction to every passage that needs it, including passages in the
  MIDDLE of a paragraph. A single paragraph often contains several.
- Return an entry ONLY for a node whose text you actually changed. A node you
  would return unchanged must be left out — an empty list is the right answer for
  a page the instruction does not touch.
- Change nothing else. Keep the wording, the order, the facts and the punctuation
  of everything the instruction does not cover.
- Never summarise, never shorten, never merge nodes, never drop a sentence.
- The text is plain text, not markdown. Do not add formatting the original did
  not have.
"""


Progress = Callable[[dict[str, Any]], Any]


def rewritable(graph: DocumentGraph, node_ids: list[str], target: Optional[str]) -> list[Node]:
    """The nodes a rewrite applies to: those in scope that actually hold prose."""
    if node_ids:
        nodes = [n for nid in node_ids if (n := graph.get(nid))]
    elif target:
        nodes = graph.resolve_target(target)
    else:
        nodes = list(graph.nodes())
    return [n for n in nodes if n.type in _TEXT_TYPES and (n.content or "").strip()]


def passes(nodes: list[Node], budget: int = _PASS_CHARS) -> list[list[Node]]:
    """Cut the nodes into passes small enough to send whole.

    A node that starts a new page starts a new pass, so a pass is a page wherever
    the document says where its pages are.
    """
    out: list[list[Node]] = []
    current: list[Node] = []
    used = 0
    for node in nodes:
        size = len(node.content or "")
        starts_page = bool((node.metadata or {}).get("page_break_before"))
        if current and (starts_page or used + size > budget):
            out.append(current)
            current, used = [], 0
        current.append(node)
        used += size
    if current:
        out.append(current)
    return out


def rewrite_nodes(
    graph: DocumentGraph,
    nodes: list[Node],
    instruction: str,
    *,
    router: Any,
    on_progress: Optional[Progress] = None,
    cancel: Optional[threading.Event] = None,
) -> tuple[dict[str, str], list[str]]:
    """Return (edits by node id, failed pass descriptions).

    A pass that fails is reported rather than swallowed: the caller needs to be
    able to say which part of the document was not edited.
    """
    edits: dict[str, str] = {}
    failures: list[str] = []
    batches = passes(nodes)

    for index, batch in enumerate(batches, start=1):
        if cancel is not None and cancel.is_set():
            failures.append(f"pass {index} of {len(batches)}: cancelled")
            break

        if on_progress:
            on_progress({"pass": index, "of": len(batches), "nodes": len(batch)})

        payload = {
            "instruction": instruction,
            "page": [{"id": n.id, "type": n.type.value, "text": n.content} for n in batch],
        }
        try:
            text, _provider, _elapsed = router.chat(
                [{"role": "system", "content": SYSTEM},
                 {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
                max_tokens=_MAX_TOKENS,
                cancel=cancel,
            )
        except Exception as exc:
            failures.append(f"pass {index} of {len(batches)}: {exc}")
            continue

        data = extract_json(text)
        if not data:
            failures.append(f"pass {index} of {len(batches)}: no usable reply")
            continue

        allowed = {n.id for n in batch}
        for edit in data.get("edits") or []:
            if not isinstance(edit, dict):
                continue
            nid, new_text = edit.get("id"), edit.get("text")
            # Only nodes in this pass, and only real replacements: a model that
            # returns an empty string would otherwise erase a paragraph.
            if nid in allowed and isinstance(new_text, str) and new_text.strip():
                node = graph.get(nid)
                if node is not None and new_text != node.content:
                    edits[nid] = new_text

    return edits, failures
