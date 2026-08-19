"""Robust JSON extraction from model output.

Models wrap JSON in prose, fence it in ```json blocks, leave trailing commas,
slip in `//` comments, and — most often — simply run out of output tokens
mid-document. A naive `\\{.*\\}` regex mishandles nested braces and dies on any
of these, so a single stray character throws away an entire generated paper.

This extractor strips fences, finds the first *balanced* object by scanning
(respecting strings and escapes), and if that fails, repairs truncated output:
it closes an unterminated string, drops a dangling key, appends the missing
closing brackets, and — if the result still will not parse — walks backwards
through earlier value boundaries until something does. Whatever the model
managed to write before it was cut off is kept.
"""
from __future__ import annotations

import json
import re
from typing import Any, Iterator, Optional

_FENCE_OPEN = re.compile(r"^\s*```(?:json|javascript|js)?\s*", re.IGNORECASE)
_FENCE_CLOSE = re.compile(r"\s*```\s*$")
_TRAILING_COMMA = re.compile(r",(\s*[}\]])")

# How many value boundaries to walk back through when repairing truncated
# output. Each step back sacrifices a little content, so the first hit wins.
_MAX_BACKOFF = 600


def extract_json(text: str) -> Optional[dict[str, Any]]:
    """The first JSON *object* in the model's reply, repaired if need be."""
    return _extract(text, "{", dict)


def extract_json_array(text: str) -> Optional[list[Any]]:
    """The first JSON *array* in the model's reply, repaired if need be."""
    return _extract(text, "[", list)


def _extract(text: str, opener: str, want: type) -> Optional[Any]:
    if not text:
        return None
    s = _FENCE_CLOSE.sub("", _FENCE_OPEN.sub("", text.strip()))

    for attempt in _variants(_first_balanced(s, opener)):
        obj = _loads(attempt, want)
        if obj is not None:
            return obj

    # Nothing balanced parsed — the reply was cut off, or its tail is corrupt.
    for repaired in _repairs(s, opener):
        for attempt in _variants(repaired):
            obj = _loads(attempt, want)
            if obj is not None:
                return obj
    return None


def _loads(s: Optional[str], want: type) -> Optional[Any]:
    if not s:
        return None
    try:
        obj = json.loads(s, strict=False)
    except (json.JSONDecodeError, ValueError, RecursionError):
        return None
    return obj if isinstance(obj, want) else None


def _variants(s: Optional[str]) -> Iterator[str]:
    """The same candidate, progressively de-linted: as written, without trailing
    commas, and without JS comments. Cheapest first, so untouched output is
    never rewritten needlessly."""
    if not s:
        return
    seen = {s}
    yield s
    for transform in (
        lambda t: _TRAILING_COMMA.sub(r"\1", t),
        lambda t: _TRAILING_COMMA.sub(r"\1", _strip_comments(t)),
    ):
        out = transform(s)
        if out not in seen:
            seen.add(out)
            yield out


def _strip_comments(s: str) -> str:
    """Remove // and /* */ comments that fall outside string literals."""
    out: list[str] = []
    i, n = 0, len(s)
    in_str = escaped = False
    while i < n:
        c = s[i]
        if in_str:
            out.append(c)
            if escaped:
                escaped = False
            elif c == "\\":
                escaped = True
            elif c == '"':
                in_str = False
            i += 1
            continue
        if c == '"':
            in_str = True
            out.append(c)
        elif c == "/" and i + 1 < n and s[i + 1] == "/":
            while i < n and s[i] != "\n":
                i += 1
            continue
        elif c == "/" and i + 1 < n and s[i + 1] == "*":
            end = s.find("*/", i + 2)
            i = n if end < 0 else end + 2
            continue
        else:
            out.append(c)
        i += 1
    return "".join(out)


def _first_balanced(s: str, opener: str = "{") -> Optional[str]:
    """Return the first balanced {...} (or [...]) substring, or None if it was
    never closed.

    Scans character by character so nested containers and braces inside strings
    do not confuse the match — the failure mode of a greedy regex.
    """
    closer = "}" if opener == "{" else "]"
    start = s.find(opener)
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
            elif c == opener:
                depth += 1
            elif c == closer:
                depth -= 1
                if depth == 0:
                    return s[start:i + 1]
    return None  # never closed → the response was truncated


# ── truncation repair ───────────────────────────────────────────────────────

def _scan(s: str) -> tuple[list[str], bool, bool]:
    """Structural state at the end of `s`: which containers are still open, and
    whether we stopped inside a string / on an escape."""
    stack: list[str] = []
    in_str = escaped = False
    for c in s:
        if in_str:
            if escaped:
                escaped = False
            elif c == "\\":
                escaped = True
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c in "{[":
            stack.append(c)
        elif c == "}":
            if stack and stack[-1] == "{":
                stack.pop()
        elif c == "]":
            if stack and stack[-1] == "[":
                stack.pop()
    return stack, in_str, escaped


_NUMERIC_END = set("0123456789")


def _value_boundaries(s: str) -> list[int]:
    """Indices just past every point where a complete JSON value could end — a
    closed string, a `}` or `]`, or the last digit of a number. Cutting a
    truncated document anywhere else leaves a fragment that cannot parse."""
    bounds: list[int] = []
    in_str = escaped = False
    for i, c in enumerate(s):
        if in_str:
            if escaped:
                escaped = False
            elif c == "\\":
                escaped = True
            elif c == '"':
                in_str = False
                bounds.append(i + 1)
        elif c == '"':
            in_str = True
        elif c in "}]":
            bounds.append(i + 1)
        elif c in _NUMERIC_END and (i + 1 >= len(s) or s[i + 1] in " \t\r\n,}]"):
            bounds.append(i + 1)
    return bounds


def _close(prefix: str) -> Optional[str]:
    """Turn `prefix` into a parseable object: finish an open string, refuse a
    dangling `key:` with no value, and append the missing closers."""
    stack, in_str, escaped = _scan(prefix)
    if not stack:
        return None  # already balanced — _first_balanced_object handled it
    if escaped:
        prefix = prefix[:-1]        # a lone trailing backslash escapes nothing
    if in_str:
        prefix += '"'               # keep the partial text the model did write

    prefix = prefix.rstrip()
    while prefix.endswith(","):
        prefix = prefix[:-1].rstrip()
    if prefix.endswith(":"):
        # a key whose value never arrived; an earlier cut point drops the key
        return None

    closing = "".join("}" if c == "{" else "]" for c in reversed(stack))
    return prefix + closing


def _repairs(s: str, opener: str = "{") -> Iterator[str]:
    """Candidate repairs of truncated output, most content first."""
    start = s.find(opener)
    if start < 0:
        return
    body = s[start:]

    seen: set[str] = set()
    first = _close(body)
    if first:
        seen.add(first)
        yield first

    # Walk back through value boundaries, discarding whatever tail will not
    # parse — a half-written key, a corrupt number, an unbalanced nested object.
    for cut in reversed(_value_boundaries(body)[-_MAX_BACKOFF:]):
        candidate = _close(body[:cut])
        if candidate and candidate not in seen:
            seen.add(candidate)
            yield candidate
