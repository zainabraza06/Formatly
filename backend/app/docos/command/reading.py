"""Read a document once, so later instructions are not read cold.

`brief` says what the document is made of; it cannot say what any of it means.
That takes a model, and asking one on every command would pay for the same
reading over and over — and still arrive with only a heading list, because a
planner's prompt has no room for eighteen pages of prose.

So the document is read once, a page at a time, and what each section is about
is written down in a sentence. Afterwards an instruction like "tighten the part
about the evaluation protocol" can be placed without anyone re-reading anything.
"""
from __future__ import annotations

import json
import threading
from typing import Any, Callable, Optional

from app.docos.command.brief import document_brief
from app.docos.command.rewriter import _strict_json, passes, rewritable
from app.docos.graph import DocumentGraph

Progress = Callable[[dict[str, Any]], None]

# A reading is a sentence per section, so the reply is short whatever the pass
# holds. Small enough that a page never overruns it.
_MAX_TOKENS = 700

SYSTEM = """You are reading one page of a document so that someone can act on it later.

Return ONLY JSON:
{"notes": [{"heading": "<the nearest heading above this text, verbatim, or ''>",
            "about": "<one sentence: what this part of the document says>"}]}

Rules:
- One note per distinct part of the page. Two or three is usual; never more than six.
- Describe what the text says, not what it looks like. No formatting talk.
- Quote the heading exactly as it appears so it can be matched.
- Be specific: "reports 89% accuracy on held-out subjects" beats "presents results".
- No prose outside the JSON, no markdown fences.
"""


def read_document(
    graph: DocumentGraph,
    *,
    router: Any,
    on_progress: Optional[Progress] = None,
    cancel: Optional[threading.Event] = None,
) -> tuple[dict[str, str], list[str]]:
    """Read the document page by page. Returns (about-by-heading, failures).

    Keyed by heading text rather than node id: the reading survives edits that
    rewrite paragraphs, and a heading is what a person names when they ask for
    a part of a document.
    """
    nodes = rewritable(graph, [], None)
    if not nodes:
        return {}, []

    about: dict[str, str] = {}
    failures: list[str] = []
    batches = passes(nodes)

    for index, batch in enumerate(batches, start=1):
        if cancel is not None and cancel.is_set():
            failures.append(f"page {index} of {len(batches)}: cancelled")
            break

        if on_progress:
            on_progress({"page": index, "of": len(batches), "nodes": len(batch),
                         "ids": [n.id for n in batch]})

        payload = {"page": [{"type": n.type.value, "text": n.content[:600]} for n in batch]}
        try:
            text, _provider, _elapsed = router.chat(
                [{"role": "system", "content": SYSTEM},
                 {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
                max_tokens=_MAX_TOKENS,
                cancel=cancel,
            )
        except Exception as exc:
            failures.append(f"page {index} of {len(batches)}: {exc}")
            continue

        data = _strict_json(text)
        if not data:
            failures.append(f"page {index} of {len(batches)}: no usable reply")
            continue

        for note in data.get("notes") or []:
            if not isinstance(note, dict):
                continue
            heading = str(note.get("heading") or "").strip()
            summary = str(note.get("about") or "").strip()
            if not summary:
                continue
            # A page with no heading of its own belongs to the one before it.
            key = heading or f"page {index}"
            about.setdefault(key, summary)

    return about, failures


def brief_with_reading(graph: DocumentGraph, about: dict[str, str]) -> dict[str, Any]:
    """The structural brief with each section's reading attached to it.

    Matched on the heading text the model was asked to quote; a heading it did
    not reach simply has nothing to say, which is honest and still useful.
    """
    brief = document_brief(graph)
    if not about:
        return brief

    lookup = {key.strip().lower(): value for key, value in about.items()}
    for section in brief.get("sections", []):
        summary = lookup.get(str(section.get("heading", "")).strip().lower())
        if summary:
            section["about"] = summary

    unplaced = [v for k, v in about.items() if k.lower().startswith("page ")]
    if unplaced:
        brief["also_covers"] = unplaced[:6]
    return brief
