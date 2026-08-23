"""What the document is, read from the document.

The planner used to be handed a pile of node counts and six sample paragraphs
and asked to decide what an instruction meant. That is enough to guess with and
not enough to know: it could not say whether the file was a paper or a report,
which section an instruction was about, or that the equations it was asked to
convert live in table cells three sections in.

This builds that knowledge instead, from the graph alone — no model call, so it
costs nothing and cannot be wrong about the document in the way a summary can.
What it cannot know (what a section *argues*) is left to `about`, which a model
fills in later.
"""
from __future__ import annotations

import re
from typing import Any, Optional

from app.docos.graph import DocumentGraph, Node, NodeType

# LaTeX, or the shapes maths takes when it is written as text.
_MATHS = re.compile(r"\\[a-zA-Z]{2,}|\$[^$]+\$|\$\$|\\frac|\\sum|\\int|_\{|\^\{|≤|≥|∑|√")
# A numbered citation, the convention most papers use.
_CITATION = re.compile(r"\[\d+\](?:[-–,]\s*\[?\d+\]?)*")

_HEADINGS = (NodeType.HEADING, NodeType.SUBHEADING)


def _page_of(node: Node) -> Optional[int]:
    page = (node.metadata or {}).get("page_index")
    return page + 1 if isinstance(page, int) else None


def _numbering_scheme(headings: list[Node]) -> Optional[str]:
    """How the document numbers its sections, in its own words."""
    for node in headings:
        text = node.content.strip()
        if re.match(r"^[IVXLCDM]+[.)]\s", text):
            return "roman numerals (I., II., III.)"
        if re.match(r"^\d+\.\d+", text):
            return "decimal (1.1, 1.2)"
        if re.match(r"^\d+[.)]\s", text):
            return "numbered (1., 2., 3.)"
        if re.match(r"^Chapter\s+\d+", text, re.IGNORECASE):
            return "chapters"
    return None


def _kind(graph: DocumentGraph, headings: list[Node]) -> str:
    """A paper, a thesis, or just a document — by what it carries."""
    opening = " ".join(n.content[:200] for n in list(graph.nodes())[:12]).lower()
    heading_text = " ".join(n.content.lower() for n in headings)

    if re.search(r"^\s*abstract\b|abstract—|abstract-", opening) or "index terms" in opening:
        return "research paper"
    if "chapter" in heading_text:
        return "thesis or book"
    if any(n.type is NodeType.REFERENCE for n in graph.nodes()):
        return "report with references"
    return "document"


def document_brief(graph: DocumentGraph) -> dict[str, Any]:
    """A structural account of the document: what it is and what it holds where.

    Sections are cut at headings, so each entry says what is inside that part of
    the document rather than only that a heading exists. An instruction that
    names a section, or a thing that only appears in one, can then be placed.
    """
    nodes = list(graph.nodes())
    headings = [n for n in nodes if n.type in _HEADINGS]

    inventory = {
        "paragraphs": sum(1 for n in nodes if n.type in (NodeType.BODY, NodeType.PARAGRAPH)),
        "headings": sum(1 for n in nodes if n.type is NodeType.HEADING),
        "subheadings": sum(1 for n in nodes if n.type is NodeType.SUBHEADING),
        "tables": sum(1 for n in nodes if n.type is NodeType.TABLE),
        "figures": sum(1 for n in nodes if n.type in (NodeType.FIGURE, NodeType.IMAGE)),
        "captions": sum(1 for n in nodes if n.type is NodeType.CAPTION),
        "references": sum(1 for n in nodes if n.type is NodeType.REFERENCE),
        "footnotes": sum(1 for n in nodes if n.type is NodeType.FOOTNOTE),
    }

    # Where the maths actually lives, which is rarely where you would guess:
    # a display equation is usually a table cell, and inline maths is prose.
    maths_in: dict[str, int] = {}
    for node in nodes:
        if node.content and _MATHS.search(node.content):
            key = node.type.value
            maths_in[key] = maths_in.get(key, 0) + 1

    sections = _sections(graph, headings)
    page_meta = (graph.root.metadata or {}).get("page") or {}

    brief: dict[str, Any] = {
        "kind": _kind(graph, headings),
        "title": graph.title,
        "pages": page_meta.get("count"),
        "inventory": inventory,
        "sections": sections,
    }

    conventions: dict[str, Any] = {}
    scheme = _numbering_scheme(headings)
    if scheme:
        conventions["heading_numbering"] = scheme
    if maths_in:
        conventions["maths_appears_in"] = maths_in
    if any(_CITATION.search(n.content or "") for n in nodes):
        conventions["citation_style"] = "numbered, [n]"
    if conventions:
        brief["conventions"] = conventions

    return brief


def _sections(graph: DocumentGraph, headings: list[Node]) -> list[dict[str, Any]]:
    """The document cut at its headings, each part described by what it holds."""
    top_level = list(graph.root.children)
    starts = {n.id: i for i, n in enumerate(top_level)}
    boundaries = [starts[h.id] for h in headings if h.id in starts]

    sections: list[dict[str, Any]] = []
    for position, start in enumerate(boundaries):
        end = boundaries[position + 1] if position + 1 < len(boundaries) else len(top_level)
        head = top_level[start]
        body = top_level[start + 1:end]

        words = sum(len((n.content or "").split()) for n in body)
        holds = {
            "paragraphs": sum(1 for n in body if n.type in (NodeType.BODY, NodeType.PARAGRAPH)),
            "tables": sum(1 for n in body if n.type is NodeType.TABLE),
            "figures": sum(1 for n in body if n.type in (NodeType.FIGURE, NodeType.IMAGE)),
            "captions": sum(1 for n in body if n.type is NodeType.CAPTION),
            "references": sum(1 for n in body if n.type is NodeType.REFERENCE),
            "maths": sum(1 for n in body
                         if any(_MATHS.search(x.content or "")
                                for x in [n, *n.walk()])),
        }
        # The ids of what is in the section, so an instruction about a part of
        # the document can act on that part. Capped: a planner's prompt is not
        # the place to list a thesis node by node, and a request that means more
        # than thirty paragraphs is better served by a target.
        contents = [head.id] + [n.id for n in body][:30]
        sections.append({
            "id": head.id,
            "level": 1 if head.type is NodeType.HEADING else 2,
            "heading": head.content[:80],
            "page": _page_of(head),
            "words": words,
            "holds": {k: v for k, v in holds.items() if v},
            "node_ids": contents,
        })
    return sections
