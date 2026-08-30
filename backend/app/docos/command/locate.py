"""Find the part of the document an instruction is talking about.

The planner is given the document's sections and what each is about, and it
still answers "the part about the results" with target 'figure', because the
word "figure" appears in its examples. Handing a model the knowledge does not
oblige it to use it.

So the matching is done here, where it can be tested. When a request names a
part of the document — "the section on the evaluation protocol", "the part that
reports accuracy" — the section is found by comparing the request against each
section's heading and its reading, and the plan is pinned to that section's
nodes. Deterministic, and wrong in ways that can be seen and fixed.
"""
from __future__ import annotations

import re
from typing import Any, Optional

# A request only means a *place* in the document when it says so.
_CUES = ("section", "subsection", "chapter", "the part", "the portion", "the bit",
         "paragraph about", "part about", "part that", "part which", "part of the paper",
         "part of the document")

# Words that say nothing about which section is meant: the instruction's own
# verbs, and the ordinary joints of English.
_NOISE = {
    "a", "an", "and", "are", "as", "at", "be", "by", "do", "for", "from", "in", "is", "it",
    "its", "of", "on", "or", "that", "the", "their", "them", "then", "there", "these",
    "this", "to", "was", "were", "which", "with", "you", "your",
    "section", "subsection", "chapter", "part", "portion", "paper", "document", "page",
    "make", "made", "change", "set", "turn", "put", "give", "apply", "please",
    "bold", "italic", "underline", "highlight", "colour", "color", "size", "font",
    "centre", "center", "align", "justify", "left", "right", "bigger", "smaller",
    "rewrite", "reword", "shorten", "tighten", "expand", "concise", "clearer", "clear",
    "all", "every", "each", "any", "some", "more", "less", "very", "just",
}

_WORD = re.compile(r"[a-z0-9%]+")

# One word that fits a single section is enough; one that fits several is not.
_MIN_OVERLAP = 2.0


def _terms(text: str) -> set[str]:
    return {w for w in _WORD.findall((text or "").lower()) if w not in _NOISE and len(w) > 2}


def names_a_place(command: str) -> bool:
    """Is this request about a part of the document rather than a kind of thing?"""
    lowered = (command or "").lower()
    return any(cue in lowered for cue in _CUES)


def locate_section(command: str, brief: dict[str, Any]) -> Optional[dict[str, Any]]:
    """The section a request is about, or None if it does not name one clearly.

    Matched against both the heading and what the section was read to be about,
    so "the part that reports accuracy" finds III. RESULTS even though neither
    word appears in its heading.
    """
    # A request may name a place two ways: with a word that means "a part of
    # this document" — "the section on…" — or simply by naming the heading.
    # "Make the contributions in introduction bullet points" does the second,
    # and requiring the first sent it to the whole document: thirteen passes to
    # rewrite one section, and twelve of them for nothing.
    cued = names_a_place(command)

    wanted = _terms(command)
    if not wanted:
        return None

    candidates = [s for s in (brief.get("sections") or []) if s.get("node_ids")]
    if not candidates:
        return None

    # How many sections each word could be about. A word that fits one section
    # and no other settles the question by itself — "accuracy" appears in the
    # results and nowhere else — while a word spread across the document says
    # almost nothing.
    spread: dict[str, int] = {}
    for section in candidates:
        for term in _terms(section.get("heading", "")) | _terms(section.get("about", "")):
            spread[term] = spread.get(term, 0) + 1

    best: Optional[dict[str, Any]] = None
    best_score = 0.0
    best_named_heading = False
    for section in candidates:
        heading_terms = _terms(section.get("heading", ""))
        section_terms = heading_terms | _terms(section.get("about", ""))
        score = 0.0
        matched_heading = False
        for term in wanted & section_terms:
            distinctive = 2.0 if spread.get(term, 0) == 1 else 1.0
            # Naming the heading is the plainest way to mean a section.
            in_heading = term in heading_terms
            matched_heading = matched_heading or in_heading
            score += distinctive + (1.0 if in_heading else 0.0)
        if score > best_score:
            best, best_score, best_named_heading = section, score, matched_heading

    if best is None or best_score < _MIN_OVERLAP:
        return None
    # Without a cue word, only a heading will do. A word that happens to appear
    # in what a section was read to be about is too thin a reason to send an
    # instruction there and nowhere else.
    return best if cued or best_named_heading else None
