"""Turning a sentence that enumerates things into a list of them.

"Put the contributions in bullets" is nearly always aimed at a paragraph that
already enumerates — "The contributions are: (i) a benchmark; (ii) a feature
set; and (iii) an evaluation" — and answering it by bulleting that one
paragraph produces a list of length one, which is not what was asked.

So the paragraph is cut where it enumerates. The cut is deterministic and
conservative: it happens only where the author marked the items themselves,
with numbering, letters, or semicolons between clauses. Text that merely
contains a bracket is left alone, because a wrong split rewrites the document.
"""
from __future__ import annotations

import re

# (i) (ii) (a) (1) 1) 1. — a marker at the start of a clause, not mid-word.
_MARKER = re.compile(
    r"(?:(?<=^)|(?<=[\s:;,]))"
    r"(?:\((?:[ivxlcdm]+|[a-z]|\d{1,2})\)"
    r"|(?:[ivxlcdm]+|[a-z]|\d{1,2})[.)](?=\s)"
    r"|[•‣●▪⁃])\s+",
    re.IGNORECASE)

# The words that trail an item and belong to the joint, not to the item.
_TRAILING = re.compile(r"[\s;,]*(?:and|or)?[\s;,]*$", re.IGNORECASE)

# Enough items to be a list. One "item" is a sentence with a bracket in it.
_MIN_ITEMS = 2


def split_items(text: str) -> tuple[str, list[str]]:
    """`(lead-in, items)` for an enumerating paragraph, or `("", [])`.

    The lead-in is whatever introduces the list ("The contributions are:") and
    stays an ordinary paragraph — a colon is not a bullet.
    """
    body = (text or "").strip()
    if not body:
        return "", []

    parts = _by_marker(body) or _by_semicolon(body)
    # Whatever comes before the first marker introduces the list rather than
    # being one of its items: "The contributions are:" is not a bullet.
    lead, rest = (parts[0].strip() if parts else ""), parts[1:]
    items = [i for i in (_tidy(i) for i in rest) if i]
    if len(items) < _MIN_ITEMS:
        return "", []
    return lead, items


def _by_marker(body: str) -> list[str]:
    cuts = [m for m in _MARKER.finditer(body)]
    if len(cuts) < _MIN_ITEMS:
        return []
    items: list[str] = []
    for k, cut in enumerate(cuts):
        end = cuts[k + 1].start() if k + 1 < len(cuts) else len(body)
        items.append(body[cut.end():end])
    # The text before the first marker is the lead-in, handled by `_lead_in`.
    items.insert(0, body[:cuts[0].start()])
    return items


def _by_semicolon(body: str) -> list[str]:
    # Only a paragraph that separates its items itself. Two semicolons is the
    # threshold: one is ordinary punctuation, two is a list.
    if body.count(";") < _MIN_ITEMS:
        return []
    head, _, rest = body.partition(":")
    if not rest.strip():
        head, rest = "", body
    parts = [p for p in rest.split(";") if p.strip()]
    if len(parts) < _MIN_ITEMS:
        return []
    return [head + ":" if head else "", *parts]


def _tidy(item: str) -> str:
    item = _TRAILING.sub("", item.strip())
    return item[0].upper() + item[1:] if item else item
