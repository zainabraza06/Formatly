"""Robust JSON extraction from model output.

Models wrap JSON in prose, fence it in ```json blocks, and leave trailing commas.
A naive `\\{.*\\}` regex mishandles nested braces and dies on any of the above, so
a single stray character throws away an entire generated document. This extractor
strips fences, finds the first *balanced* object by scanning (respecting strings
and escapes), and retries after removing trailing commas before giving up.
"""
from __future__ import annotations

import json
import re
from typing import Any, Optional

_FENCE_OPEN = re.compile(r"^\s*```(?:json)?\s*", re.IGNORECASE)
_FENCE_CLOSE = re.compile(r"\s*```\s*$")
_TRAILING_COMMA = re.compile(r",(\s*[}\]])")


def extract_json(text: str) -> Optional[dict[str, Any]]:
    if not text:
        return None
    s = _FENCE_CLOSE.sub("", _FENCE_OPEN.sub("", text.strip()))

    candidate = _first_balanced_object(s)
    for attempt in filter(None, (candidate, _TRAILING_COMMA.sub(r"\1", candidate or ""))):
        try:
            obj = json.loads(attempt)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            continue
    return None


def _first_balanced_object(s: str) -> Optional[str]:
    """Return the first brace-balanced {...} substring, or None if truncated.

    Scans character by character so nested objects and braces inside strings do
    not confuse the match — the failure mode of a greedy regex.
    """
    start = s.find("{")
    if start < 0:
        return None
    depth = 0
    in_str = False
    escaped = False
    for i in range(start, len(s)):
        c = s[i]
        if in_str:
            if escaped:
                escaped = False
            elif c == "\\":
                escaped = True
            elif c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return s[start:i + 1]
    return None  # never closed → the response was truncated
