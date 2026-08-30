"""Finding the words a request describes but does not quote.

"Bold the word results" names its target exactly, and a literal search is both
faster and more reliable than any model. "Bold the results in the abstract"
does not: it describes them — the figures the paper reports — and the only way
to find those is to read the text.

So the description is resolved to exact substrings, which are then formatted the
same way a quoted phrase is. A span the model invents is dropped rather than
guessed at, because formatting text that is not there is worse than formatting
nothing.
"""
from __future__ import annotations

import json
import threading
from typing import Any, Optional

from app.docos.command.rewriter import _strict_json
from app.docos.graph import Node

# The reply is a short list of quotations, whatever the passage holds.
_MAX_TOKENS = 700

# Long enough for a section, short enough to stay one request.
_MAX_CHARS = 6000

SYSTEM = """You are marking the parts of a passage that match a description.

Return ONLY JSON:
{"spans": [{"id": "<the node id the text is in>", "text": "<the exact substring>"}]}

Rules:
- `text` must appear in that node character for character. Copy it, do not retype it.
- Mark the shortest span that satisfies the description — a figure and its unit,
  not the sentence around it.
- Several spans per node is normal. None is a valid answer: say {"spans": []}.
- Do not mark whole paragraphs. If the description covers everything, mark nothing.
- No prose outside the JSON, no markdown fences.
"""


def find_spans(
    nodes: list[Node],
    description: str,
    *,
    router: Any,
    cancel: Optional[threading.Event] = None,
) -> list[dict[str, str]]:
    """Exact substrings within `nodes` matching `description`.

    Returns `[{"id": node id, "text": substring}]`, only for text that really
    occurs in that node.
    """
    passage: list[dict[str, str]] = []
    used = 0
    for node in nodes:
        text = (node.content or "").strip()
        if not text:
            continue
        passage.append({"id": node.id, "text": text[:_MAX_CHARS]})
        used += len(text)
        if used >= _MAX_CHARS:
            break
    if not passage:
        return []

    payload = {"description": description, "passage": passage}
    text, _provider, _elapsed = router.chat(
        [{"role": "system", "content": SYSTEM},
         {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
        max_tokens=_MAX_TOKENS,
        cancel=cancel,
        wait_on_rate_limit=True,
    )

    data = _strict_json(text) or {}
    by_id = {node.id: (node.content or "") for node in nodes}
    spans: list[dict[str, str]] = []
    for span in data.get("spans") or []:
        if not isinstance(span, dict):
            continue
        node_id, wanted = span.get("id"), span.get("text")
        if not isinstance(node_id, str) or not isinstance(wanted, str):
            continue
        wanted = wanted.strip()
        # Only text that is actually there. A model that retypes a figure
        # instead of copying it would otherwise have us format nothing, or
        # worse, format the wrong thing.
        if wanted and wanted in by_id.get(node_id, ""):
            spans.append({"id": node_id, "text": wanted})
    return spans
