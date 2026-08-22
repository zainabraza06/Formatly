"""Node-level diff between two document graphs.

The diff answers "what changed with what", not just "how many things changed",
so every entry carries the text it is talking about. Changed text also carries
word-level segments so a reader can see the exact words that moved.
"""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from typing import Any

from app.docos.graph import DocumentGraph

# Text longer than this is trimmed for transport; the entry says so via
# `truncated` rather than pretending the shorter text is the whole node.
MAX_TEXT = 2000

# Split on whitespace but keep it, so rejoining the segments reproduces the
# text exactly and a word swap does not look like a whole-line rewrite.
_TOKENS = re.compile(r"\s+|\S+")


def _clip(text: str) -> tuple[str, bool]:
    return (text[:MAX_TEXT], True) if len(text) > MAX_TEXT else (text, False)


def word_segments(before: str, after: str) -> list[dict[str, str]]:
    """Word-level runs describing how `before` becomes `after`.

    Each segment is `{"op": "equal"|"insert"|"delete", "text": ...}`. Joining
    the equal+delete text gives back `before`; equal+insert gives back `after`.
    """
    a, b = _TOKENS.findall(before), _TOKENS.findall(after)
    segments: list[dict[str, str]] = []

    def push(op: str, text: str) -> None:
        if not text:
            return
        if segments and segments[-1]["op"] == op:
            segments[-1]["text"] += text
        else:
            segments.append({"op": op, "text": text})

    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == "equal":
            push("equal", "".join(a[i1:i2]))
        else:
            # `replace` is a delete and an insert in the same place; emitting
            # both keeps the rendering rule simple (red then green).
            push("delete", "".join(a[i1:i2]))
            push("insert", "".join(b[j1:j2]))
    return segments


def style_fields(before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
    """The individual style properties that differ, one entry each."""
    return [
        {"field": key, "before": before.get(key), "after": after.get(key)}
        for key in sorted(set(before) | set(after))
        if before.get(key) != after.get(key)
    ]


@dataclass
class GraphDiff:
    added: list[dict[str, Any]] = field(default_factory=list)
    removed: list[dict[str, Any]] = field(default_factory=list)
    changed: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "added": self.added,
            "removed": self.removed,
            "changed": self.changed,
            "summary": self.summary(),
        }

    def summary(self) -> dict[str, int]:
        """Counts the timeline can show before anyone opens the detail."""
        text_changed = sum(1 for c in self.changed if "content" in c)
        return {
            "added": len(self.added),
            "removed": len(self.removed),
            "changed": len(self.changed),
            "text_changed": text_changed,
            "style_changed": sum(1 for c in self.changed if "style" in c),
            "words_added": sum(
                len(seg["text"].split())
                for c in self.changed if "content" in c
                for seg in c["content"]["segments"] if seg["op"] == "insert"
            ),
            "words_removed": sum(
                len(seg["text"].split())
                for c in self.changed if "content" in c
                for seg in c["content"]["segments"] if seg["op"] == "delete"
            ),
        }


def _entry(node) -> dict[str, Any]:
    text, truncated = _clip(node.content)
    return {"id": node.id, "type": node.type.value, "content": text, "truncated": truncated}


def diff_graphs(a: DocumentGraph, b: DocumentGraph) -> GraphDiff:
    """Diff `a` (before) against `b` (after) by node id."""
    ia = {n.id: n for n in a.nodes()}
    ib = {n.id: n for n in b.nodes()}
    diff = GraphDiff()

    for nid, nb in ib.items():
        if nid not in ia:
            diff.added.append(_entry(nb))

    for nid, na in ia.items():
        nb = ib.get(nid)
        if nb is None:
            diff.removed.append(_entry(na))
            continue
        changes: dict[str, Any] = {}
        if na.content != nb.content:
            before, before_cut = _clip(na.content)
            after, after_cut = _clip(nb.content)
            changes["content"] = {
                "before": before,
                "after": after,
                "segments": word_segments(before, after),
                "truncated": before_cut or after_cut,
            }
        sa = na.style.model_dump(exclude_none=True)
        sb = nb.style.model_dump(exclude_none=True)
        if sa != sb:
            changes["style"] = {"before": sa, "after": sb, "fields": style_fields(sa, sb)}
        if changes:
            diff.changed.append({"id": nid, "type": nb.type.value, **changes})

    return diff
