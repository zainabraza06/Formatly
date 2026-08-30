"""Last resort: asking what the instruction was about.

Every other way of finding an instruction's target is a rule — a node class, a
named section, a quoted phrase — and a rule only covers what it was written
for. People do not write to the rules: "centre the fig captions wherever
present", "bullet the contributions", "make the header cells capitalised". When
none of the rules match, the honest options are to say nothing matched, or to
look at the document and work out what was meant.

This does the latter, and only then: it runs after a plan has reached nothing,
so its cost is paid on the requests that would otherwise have failed. Ids that
are not in the document are dropped, so a wrong answer narrows to nothing
rather than editing the wrong paragraph.
"""
from __future__ import annotations

import threading
from typing import Any, Optional

import json

from app.docos.command.rewriter import _strict_json
from app.docos.graph import DocumentGraph, NodeType

# One request's worth of document. Several are sent for a long file.
_CHARS_PER_PASS = 6000

# How far to read before giving up. A request that names nothing findable
# should not cost a walk of a ninety-page report.
_MAX_PASSES = 8

_MAX_TOKENS = 500

# Nodes that hold no text of their own; their children are listed instead.
_STRUCTURAL = (NodeType.DOCUMENT, NodeType.TABLE, NodeType.TABLE_ROW,
               NodeType.FIGURE)

SYSTEM = """You are finding which parts of a document an instruction is about.

You are given an instruction and a numbered list of the document's parts, each
with an id, a kind, and its opening words.

Return ONLY JSON: {"ids": ["<id>", ...]}

Rules:
- List every part the instruction would change, and nothing else.
- Judge by what the part IS, not by words it shares with the instruction: an
  instruction about captions means the captions, not a paragraph that says the
  word "caption".
- If none of these parts are what the instruction is about, return {"ids": []}.
- No prose outside the JSON, no markdown fences.
"""


def resolve_nodes(
    command: str,
    graph: DocumentGraph,
    *,
    router: Any,
    cancel: Optional[threading.Event] = None,
) -> list[str]:
    """Ids of the nodes `command` is about, read from the document itself."""
    known = {n.id for n in graph.nodes()}
    found: list[str] = []

    for part in _passes(graph):
        if cancel is not None and cancel.is_set():
            break
        try:
            text, _provider, _elapsed = router.chat(
                [{"role": "system", "content": SYSTEM},
                 {"role": "user", "content": json.dumps(
                     {"instruction": command, "parts": part},
                     ensure_ascii=False, separators=(",", ":"))}],
                max_tokens=_MAX_TOKENS,
                cancel=cancel,
                wait_on_rate_limit=True,
            )
        except Exception:
            # A provider that is down is not an answer, but it is also not a
            # reason to lose the ids the earlier passes already found.
            break
        for nid in (_strict_json(text) or {}).get("ids") or []:
            if isinstance(nid, str) and nid in known and nid not in found:
                found.append(nid)

    return found


def _passes(graph: DocumentGraph) -> list[list[dict[str, str]]]:
    """The document as request-sized lists of its parts."""
    passes: list[list[dict[str, str]]] = []
    current: list[dict[str, str]] = []
    used = 0
    for node in graph.nodes():
        if node.type in _STRUCTURAL:
            continue
        text = (node.content or "").strip()
        if not text:
            continue
        entry = {"id": node.id, "kind": node.type.value, "text": text[:160]}
        current.append(entry)
        used += len(entry["text"])
        if used >= _CHARS_PER_PASS:
            passes.append(current)
            current, used = [], 0
            if len(passes) >= _MAX_PASSES:
                return passes
    if current:
        passes.append(current)
    return passes[:_MAX_PASSES]
