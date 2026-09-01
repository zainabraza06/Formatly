"""The names a document uses for its own things.

A rewrite that refers to the document — "rephrase the title around the
architecture", "say this in the terms the method section uses" — has to be able
to name what the document names. Given only the paragraph and the instruction,
a model can do nothing but repeat the instruction's own words, which is how
"around the architecture" produced "Architecture of <the old title>".

So the document's vocabulary travels with the request: the abbreviations it
defines, and the capitalised names it uses often enough to be its own. Nothing
is invented — every term here is one the document spells out.
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Any

# "subject-independent classifier (SIC)" — a definition the author wrote out.
_DEFINED = re.compile(
    r"([A-Za-z][A-Za-z0-9-]*(?:\s+[A-Za-z][A-Za-z0-9-]*){0,5})\s*"
    r"\(\s*([A-Z][A-Za-z0-9-]{1,7})\s*\)")

# A bare abbreviation used on its own: LOSO, MobiAct, BiLSTM.
_ABBREVIATION = re.compile(r"\b(?:[A-Z]{2,8}\d?|[A-Z][a-z]+[A-Z][A-Za-z]*)\b")

# Words that look like abbreviations and name nothing in particular.
_NOT_A_TERM = {
    "THE", "AND", "FOR", "WITH", "THIS", "THAT", "FROM", "NOT", "ALL", "ARE",
    "WAS", "HAS", "CAN", "USE", "USED", "ONE", "TWO", "III", "II", "IV", "VI",
    "PDF", "DOI", "ISBN", "HTTP", "HTTPS", "IEEE", "ACM",
}

# Enough to be the document's own word rather than a passing mention.
_MIN_USES = 2

# What is worth sending. Beyond this it is a glossary, not a hint.
_MAX_TERMS = 24


def document_terms(texts: list[str]) -> list[str]:
    """The abbreviations and names this document uses, commonest first.

    A defined abbreviation is returned as the author wrote it — "subject-
    independent classifier (SIC)" — so a rewrite can use either half.
    """
    joined = "\n".join(t for t in texts if t)
    if not joined:
        return []

    defined: dict[str, str] = {}
    for phrase, short in _DEFINED.findall(joined):
        if short.upper() in _NOT_A_TERM:
            continue
        spelled = _spelled_out(phrase, short)
        # The first definition wins: a paper defines a term once, and a later
        # bracket after the same letters is usually a coincidence.
        defined.setdefault(short, f"{spelled} ({short})" if spelled else short)

    uses = Counter(m for m in _ABBREVIATION.findall(joined)
                   if m.upper() not in _NOT_A_TERM)

    out: list[str] = []
    for term, count in uses.most_common():
        if count < _MIN_USES and term not in defined:
            continue
        out.append(defined.get(term, term))
        if len(out) >= _MAX_TERMS:
            break
    return out


def _spelled_out(phrase: str, short: str) -> str:
    """The words the abbreviation is made of, and no more.

    The text before a bracket runs back as far as the sentence does, so a plain
    capture gives "evaluated under subject-independent Leave-One-Subject-Out"
    for LOSO. The abbreviation says how many words it wants: as many as it has
    letters, taken from the end, kept only if their initials line up with it.
    """
    words = [w for w in phrase.split() if w]
    # Try the shortest tail first: "a subject-independent classifier (SIC)"
    # spells SIC with two words, not with three.
    for length in range(1, min(len(short), len(words)) + 1):
        tail = words[-length:]
        # A hyphenated term spells several letters with one word:
        # "Leave-One-Subject-Out" is all of LOSO on its own.
        parts = [p for word in tail for p in word.split("-") if p]
        if "".join(p[0] for p in parts).upper() == short.upper():
            return " ".join(tail)
    return ""


def terms_of(graph: Any) -> list[str]:
    """The document's vocabulary, read from the document."""
    return document_terms([n.content for n in graph.nodes() if n.content])
