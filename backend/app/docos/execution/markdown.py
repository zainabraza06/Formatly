"""Emphasis a model typed because it could not apply it.

Asked to make the table headers bold and capitalised, the rewriter returns
`**COMPONENT**`. It is answering in the only notation it has, and in a
Markdown document that would be bold — but this document is a Word document,
where a run carries `bold` and an asterisk is an asterisk. Stored as it came,
the header reads `**COMPONENT**` on the page.

So the markers are read as what they mean: the text loses them, and the
emphasis they asked for becomes real formatting.
"""
from __future__ import annotations

import re
from typing import Optional

from app.docos.graph import Style

# `**bold**`, `__bold__`, `*italic*`, `_italic_`, `` `code` ``. The inner text
# may not start or end with a space — "2 * 3 * 4" is arithmetic, not emphasis.
_EMPHASIS = re.compile(
    r"(?<!\w)(\*\*\*|\*\*|__|\*|_|`)(?!\s)(.+?)(?<!\s)\1(?!\w)",
    re.DOTALL)

# What each marker means.
_MEANS = {
    "***": Style(bold=True, italic=True),
    "**": Style(bold=True),
    "__": Style(bold=True),
    "*": Style(italic=True),
    "_": Style(italic=True),
    "`": Style(),          # code: the markers go, nothing is claimed by them
}


def strip_emphasis(text: str) -> tuple[str, list[tuple[str, Style]]]:
    """`(text without markers, [(the emphasised words, what they asked for)])`.

    Nothing is guessed: a string with no markers comes back unchanged, and the
    spans are exactly what was between them, so the caller can format those
    words and nothing else.
    """
    if not text or not any(c in text for c in "*_`"):
        return text, []

    spans: list[tuple[str, Style]] = []

    def take(match: re.Match) -> str:
        inner, marker = match.group(2), match.group(1)
        style = _MEANS.get(marker)
        # Nested markers — `**a *b* c**` — resolve innermost-first on the way
        # back through, so the inner text is cleaned before it is recorded.
        inner, deeper = strip_emphasis(inner)
        spans.extend(deeper)
        if style is not None and style.model_dump(exclude_none=True):
            spans.append((inner, style))
        return inner

    cleaned = _EMPHASIS.sub(take, text)
    return cleaned, spans


def apply_typed_emphasis(node, text: str) -> Optional[str]:
    """Set `text` on `node`, turning any typed emphasis into real formatting.

    Returns the text that was stored, or None if there was nothing to store.
    """
    cleaned, spans = strip_emphasis(text)
    if not cleaned.strip():
        return None

    node.set_text(cleaned)
    for words, style in spans:
        # Whole-string emphasis is the common case — a header the model
        # returned as `**COMPONENT**` — and styling the node itself keeps it
        # one run rather than one run that happens to be all of it.
        if words == cleaned:
            node.apply_style(style)
        else:
            node.style_span(words, style)
    return cleaned
