"""Detect a document's *structural conventions* from a reference DOCX.

Fonts and sizes are only half of a style. The rest is convention: how many columns,
how headings are numbered, whether captions sit above or below, how tables are ruled.
This module reads those from the sample so a derived style is genuinely the user's
format — not a base style they had to guess at.

Every probe is conservative: it returns a value only when the sample actually says
so, and `None` otherwise, so the caller keeps its fallback. Detection reads both the
raw XML (columns, borders, shading) and the parsed graph (heading/caption patterns).
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Any, Optional

from docx.document import Document as _Doc
from docx.oxml.ns import qn

from app.docos.graph import DocumentGraph, NodeType
from app.docos.graph.model import Node

# "TABLE I", "Table 1:", "Table 1." — number may be roman or arabic
_TABLE_CAP = re.compile(r"^\s*(TABLE|Table|TAB\.)\s+([IVXLCDM]+|\d+)\s*([:.—-]?)\s*(.*)$")
# "Fig. 1.", "Figure 1:", "FIGURE 1"
_FIG_CAP = re.compile(r"^\s*(Fig\.|Figure|FIGURE|FIG\.)\s*(\d+)\s*([:.—-]?)\s*(.*)$")

_ROMAN_HEAD = re.compile(r"^\s*([IVXLCDM]+)\.\s+\S")
_DECIMAL_HEAD = re.compile(r"^\s*(\d+(?:\.\d+)*)[.)]?\s+\S")
_ALPHA_HEAD = re.compile(r"^\s*([A-Z])\.\s+\S")

_REFERENCES_TITLES = ("references", "bibliography", "works cited", "literature cited")
_NUMBERED_REF = re.compile(r"^\s*\[\d+\]")
_ABSTRACT_LEAD = re.compile(r"^\s*(Abstract)\s*([—–:-])\s*\S")
_KEYWORDS_LEAD = re.compile(r"^\s*(Index Terms|Keywords|Key words)\s*([—–:-])\s*\S")

_NO_BORDER = (None, "none", "nil")


# A blank document still reports one column, Times New Roman, etc. — Word's
# defaults. Readings that merely match a default are only evidence if the sample
# is a real document, so weak signals need this much content behind them.
_MIN_CONTENT_FOR_DEFAULTS = 5


def detect_conventions(doc: _Doc, graph: DocumentGraph) -> dict[str, Any]:
    """Return only the conventions the sample actually reveals."""
    found: dict[str, Any] = {}

    _put(found, "columns", _columns(doc, graph))
    _put(found, "column_spacing_in", _column_spacing(doc))
    _put(found, "heading_scheme", _heading_scheme(graph))
    _put(found, "table_borders", _table_borders(doc))
    _put(found, "table_header_fill", _header_fill(doc))
    _put(found, "number_references", _numbered_references(graph))
    _put(found, "references_title", _references_title(graph))

    found.update(_captions(graph))
    found.update(_front_matter(graph))
    return found


def _put(d: dict[str, Any], key: str, value: Any) -> None:
    if value is not None:
        d[key] = value


# ── page / columns ──────────────────────────────────────────────────────────

def _cols_elements(doc: _Doc) -> list:
    out = []
    for section in doc.sections:
        cols = section._sectPr.find(qn("w:cols"))
        if cols is not None:
            out.append(cols)
    return out


def _content_nodes(graph: DocumentGraph) -> int:
    return sum(1 for n in graph.nodes() if (n.content or "").strip())


def _columns(doc: _Doc, graph: DocumentGraph) -> Optional[int]:
    """Body column count. A title block often spans 1 column while the body uses N,
    so the maximum across sections is what characterises the style.

    Multi-column is always an explicit authorial choice, so it is trusted outright.
    Single-column is Word's default and is only believed when the sample has enough
    content to show that the author actually wrote it that way.
    """
    counts = []
    for cols in _cols_elements(doc):
        num = cols.get(qn("w:num"))
        counts.append(int(num) if num and num.isdigit() else 1)
    if not counts:
        return None

    top = max(counts)
    if top > 1:
        return top
    return 1 if _content_nodes(graph) >= _MIN_CONTENT_FOR_DEFAULTS else None


def _column_spacing_in(cols) -> Optional[float]:
    space = cols.get(qn("w:space"))
    if space and space.isdigit():
        return round(int(space) / 1440.0, 3)  # twips → inches
    return None


def _column_spacing(doc: _Doc) -> Optional[float]:
    for cols in _cols_elements(doc):
        num = cols.get(qn("w:num"))
        if num and num.isdigit() and int(num) > 1:
            return _column_spacing_in(cols)
    return None


# ── headings ────────────────────────────────────────────────────────────────

def _heading_nodes(graph: DocumentGraph) -> tuple[list[Node], list[Node]]:
    l1 = [n for n in graph.nodes() if n.type == NodeType.HEADING and n.content.strip()]
    l2 = [n for n in graph.nodes() if n.type == NodeType.SUBHEADING and n.content.strip()]
    return l1, l2


def _heading_scheme(graph: DocumentGraph) -> Optional[str]:
    """roman_alpha ("I." / "A."), decimal ("1." / "1.1"), or none (unnumbered).

    Only decides when the sample's headings carry literal numbering; Word
    auto-numbering lives in numbering.xml and leaves no text to read, so we
    stay silent rather than guess.
    """
    l1, l2 = _heading_nodes(graph)
    if not l1:
        return None

    roman = sum(1 for n in l1 if _ROMAN_HEAD.match(n.content))
    decimal = sum(1 for n in l1 if _DECIMAL_HEAD.match(n.content))
    total = len(l1)

    # "I." also matches nothing else, but a lone "I" heading is ambiguous;
    # require a clear majority before committing.
    if roman and roman >= max(2, total * 0.6):
        return "roman_alpha"
    if decimal and decimal >= max(2, total * 0.6):
        return "decimal"
    if roman == 0 and decimal == 0:
        # unnumbered level-1s; confirm level-2s aren't numbered either
        if not l2 or not any(_DECIMAL_HEAD.match(n.content) or _ALPHA_HEAD.match(n.content)
                             for n in l2):
            return "none"
    return None


# ── captions ────────────────────────────────────────────────────────────────

def _captions(graph: DocumentGraph) -> dict[str, Any]:
    """Caption position, wording and numbering, inferred from where caption-looking
    paragraphs sit relative to the tables/figures they describe."""
    blocks = list(graph.root.children)
    out: dict[str, Any] = {}

    table_votes: Counter[str] = Counter()
    fig_votes: Counter[str] = Counter()
    table_fmt: list[tuple[str, str, bool, bool]] = []
    fig_fmt: list[tuple[str, str, bool, bool]] = []

    for i, node in enumerate(blocks):
        text = (node.content or "").strip()
        if not text or node.type in (NodeType.TABLE, NodeType.FIGURE):
            continue
        first, _, remainder = text.partition("\n")

        m = _TABLE_CAP.match(first)
        if m:
            pos = _position(blocks, i, NodeType.TABLE)
            if pos:
                table_votes[pos] += 1
                word, num, sep, tail = m.groups()
                table_fmt.append((word, sep, bool(tail), bool(remainder.strip())))
            continue

        m = _FIG_CAP.match(first)
        if m:
            pos = _position(blocks, i, NodeType.FIGURE)
            if pos:
                fig_votes[pos] += 1
                word, num, sep, tail = m.groups()
                fig_fmt.append((word, sep, bool(tail), bool(remainder.strip())))

    if table_votes:
        out["table_caption_position"] = table_votes.most_common(1)[0][0]
        _put(out, "table_number_style", _number_style(blocks, _TABLE_CAP))
        prefix, sep = _prefix_from(table_fmt)
        _put(out, "table_caption_prefix", prefix)
        _put(out, "table_caption_separator", sep)

    if fig_votes:
        out["figure_caption_position"] = fig_votes.most_common(1)[0][0]
        prefix, sep = _prefix_from(fig_fmt)
        _put(out, "figure_caption_prefix", prefix)
        _put(out, "figure_caption_separator", sep)

    return out


def _position(blocks: list[Node], i: int, target: NodeType) -> Optional[str]:
    """Is this caption above or below the thing it describes?"""
    if i + 1 < len(blocks) and blocks[i + 1].type == target:
        return "above"
    if i - 1 >= 0 and blocks[i - 1].type == target:
        return "below"
    return None


def _number_style(blocks: list[Node], pattern: re.Pattern) -> Optional[str]:
    romans = arabics = 0
    for node in blocks:
        first = (node.content or "").strip().partition("\n")[0]
        m = pattern.match(first)
        if not m:
            continue
        num = m.group(2)
        if num.isdigit():
            arabics += 1
        else:
            romans += 1
    if romans and romans >= arabics:
        return "roman"
    if arabics:
        return "arabic"
    return None


def _prefix_from(fmts: list[tuple[str, str, bool, bool]]) -> tuple[Optional[str], Optional[str]]:
    """Rebuild the caption prefix template and label/title separator."""
    if not fmts:
        return None, None
    word, sep, inline_tail, next_line = Counter(fmts).most_common(1)[0][0]
    prefix = f"{word} {{num}}{sep}"
    if inline_tail:
        prefix += " "          # "Table 1: " / "Fig. 1. "
    separator = "\n" if next_line and not inline_tail else ""
    return prefix, separator


# ── tables ──────────────────────────────────────────────────────────────────

def _first_table(doc: _Doc):
    return doc.tables[0] if doc.tables else None


def _table_borders(doc: _Doc) -> Optional[str]:
    table = _first_table(doc)
    if table is None:
        return None
    borders = table._tbl.tblPr.find(qn("w:tblBorders"))
    if borders is None:
        return None  # styled via tblStyle — nothing explicit to read

    def val(edge: str) -> Optional[str]:
        el = borders.find(qn(f"w:{edge}"))
        return el.get(qn("w:val")) if el is not None else None

    vertical = val("insideV") not in _NO_BORDER or val("left") not in _NO_BORDER
    horizontal = val("insideH") not in _NO_BORDER or val("top") not in _NO_BORDER

    if vertical and horizontal:
        return "grid"
    if horizontal:
        return "horizontal"
    return "none"


def _header_fill(doc: _Doc) -> Optional[str]:
    table = _first_table(doc)
    if table is None or not table.rows:
        return None
    cell = table.rows[0].cells[0]
    tc_pr = cell._tc.tcPr
    if tc_pr is None:
        return None
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        return None
    fill = shd.get(qn("w:fill"))
    if not fill or fill.lower() in ("auto", "ffffff"):
        return None
    return fill.upper()


# ── references / front matter ───────────────────────────────────────────────

def _numbered_references(graph: DocumentGraph) -> Optional[bool]:
    refs = [n for n in graph.nodes() if n.type == NodeType.REFERENCE and n.content.strip()]
    if not refs:
        return None
    numbered = sum(1 for n in refs if _NUMBERED_REF.match(n.content))
    return numbered >= max(1, len(refs) * 0.6)


def _references_title(graph: DocumentGraph) -> Optional[str]:
    for node in graph.nodes():
        if node.type not in (NodeType.HEADING, NodeType.SUBHEADING):
            continue
        # strip any numbering the sample used ("VI. References")
        text = re.sub(r"^\s*(?:[IVXLCDM]+\.|\d+(?:\.\d+)*[.)]?)\s+", "", node.content).strip()
        if text.lower() in _REFERENCES_TITLES:
            return text
    return None


def _front_matter(graph: DocumentGraph) -> dict[str, Any]:
    """How the abstract and keyword lists are introduced."""
    out: dict[str, Any] = {}
    for node in graph.nodes():
        text = (node.content or "").strip()
        if not text:
            continue

        m = _ABSTRACT_LEAD.match(text)
        if m and "abstract_lead" not in out:
            out["abstract_lead"] = f"{m.group(1)}{m.group(2)}"
            out["abstract_as_heading"] = False

        m = _KEYWORDS_LEAD.match(text)
        if m and "keywords_lead" not in out:
            sep = m.group(2)
            out["keywords_lead"] = f"{m.group(1)}{sep}" + (" " if sep == ":" else "")

    if "abstract_lead" not in out:
        for node in graph.nodes():
            if (node.type in (NodeType.HEADING, NodeType.SUBHEADING)
                    and node.content.strip().lower().rstrip(":") == "abstract"):
                out["abstract_as_heading"] = True
                out["abstract_lead"] = ""
                break
    return out
