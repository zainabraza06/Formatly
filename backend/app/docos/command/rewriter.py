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

# How much text one pass may carry. Small enough that the reply cannot truncate,
# large enough that a normal page goes in a single pass.
_PASS_CHARS = 5000

# Bounded so a reply cannot run past the ceiling and lose the pass.
_MAX_TOKENS = 4000

# Node types whose text is prose the user meant. A caption is included; a table
# cell is not, because rewriting one in isolation loses the row it belonged to.
# Everything that holds words a rewrite could be about. Table cells belong
# here: a paper's display equations are usually laid out in a one-row table,
# equation in the left cell and its number in the right, so leaving cells out
# meant "convert every equation" reached none of the equations.
_TEXT_TYPES = {
    NodeType.BODY, NodeType.PARAGRAPH, NodeType.HEADING, NodeType.SUBHEADING,
    NodeType.CAPTION, NodeType.REFERENCE, NodeType.FOOTNOTE, NodeType.TABLE_CELL,
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


def _strict_json(text: str) -> Optional[dict[str, Any]]:
    """The reply, parsed only if it is complete.

    `extract_json` repairs a truncated reply by closing it at the last value
    boundary, which is right for a plan and wrong for text: it would hand back
    a paragraph cut off mid-sentence as though the model had meant it, and the
    document would quietly lose the rest. Rewriting takes whole replies only.
    """
    if not text:
        return None
    start = text.find("{")
    if start < 0:
        return None
    try:
        value, _end = json.JSONDecoder().raw_decode(text, start)
    except ValueError:
        return None
    return value if isinstance(value, dict) else None


def salvage_edits(text: str) -> Optional[dict[str, Any]]:
    """The edits a reply managed to finish before it was cut off.

    `extract_json` repairs a truncated object where it can; when even that
    fails, the reply is still likely to hold several complete `{"id": ...,
    "text": ...}` entries before the point it stopped. Taking those turns a lost
    pass into a partly finished one, and the nodes it did not reach are asked
    for again rather than left as they were.
    """
    if not text:
        return None
    edits: list[dict[str, str]] = []
    decoder = json.JSONDecoder()
    index = 0
    while True:
        start = text.find('{"id"', index)
        if start < 0:
            start = text.find('{ "id"', index)
        if start < 0:
            break
        try:
            value, end = decoder.raw_decode(text, start)
        except ValueError:
            index = start + 1
            continue
        index = end
        if isinstance(value, dict) and isinstance(value.get("id"), str)                 and isinstance(value.get("text"), str):
            edits.append({"id": value["id"], "text": value["text"]})
    return {"edits": edits} if edits else None


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

    def collect(data: Any, batch: list[Node]) -> set[str]:
        """Take the edits a reply offers for this pass. Returns the ids it covered."""
        covered: set[str] = set()
        allowed = {n.id for n in batch}
        for edit in (data or {}).get("edits") or []:
            if not isinstance(edit, dict):
                continue
            nid, new_text = edit.get("id"), edit.get("text")
            # Only nodes in this pass, and only real replacements: a model that
            # returns an empty string would otherwise erase a paragraph.
            if nid in allowed and isinstance(new_text, str) and new_text.strip():
                covered.add(nid)
                node = graph.get(nid)
                if node is not None and new_text != node.content:
                    edits[nid] = new_text
        return covered

    def run(batch: list[Node], label: str) -> None:
        """One pass, halved and retried if the reply does not survive.

        A reply carries the full new text of every node in the pass, and a
        conversion can be longer than what it converts — spelling a fraction out
        in words is — so a pass that fits going in can overrun the reply ceiling
        coming back. The reply is then cut mid-JSON. Dropping the pass there is
        what left half a document converted and half untouched, so what did
        arrive is kept and whatever it missed is asked for again in smaller
        pieces, down to one node at a time.
        """
        if cancel is not None and cancel.is_set():
            failures.append(f"{label}: cancelled")
            return

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
            text = ""
            error: Optional[str] = str(exc)
        else:
            error = None

        covered = collect(_strict_json(text) or salvage_edits(text), batch) if text else set()
        missed = [n for n in batch if n.id not in covered]

        if not missed:
            return
        if len(batch) == 1 or not text:
            failures.append(f"{label}: {error or 'no usable reply'}")
            return

        # Ask again for what did not come back, in halves.
        half = max(1, len(missed) // 2)
        run(missed[:half], f"{label}a")
        run(missed[half:], f"{label}b")

    for index, batch in enumerate(batches, start=1):
        if cancel is not None and cancel.is_set():
            failures.append(f"pass {index} of {len(batches)}: cancelled")
            break
        if on_progress:
            # The ids travel with the progress so the editor can turn to the
            # page being read rather than leaving the reader to guess where the
            # work is happening.
            on_progress({"pass": index, "of": len(batches), "nodes": len(batch),
                         "ids": [n.id for n in batch]})
        run(batch, f"pass {index} of {len(batches)}")

    return edits, failures
