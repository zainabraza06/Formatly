"""Derive a StyleSheet from a reference DOCX.

When a user says "follow this example", we should learn the example's *actual*
formatting — not just feed its text to the LLM. This reuses the DocOS parser,
which already reads fonts, sizes, bold/italic and alignment per node, plus the
real page geometry, and folds them into a StyleSheet.

Whatever the sample doesn't reveal falls back to a chosen base style, so the
result is always complete and renderable.
"""
from __future__ import annotations

from collections import Counter
from typing import Iterable, Optional

from app.docos.graph import DocumentGraph, NodeType
from app.docos.parser import parse_docx_bytes
from app.paper.schema import PageSetup, Style
from app.paper.styles.base import StyleSheet


def derive_stylesheet_from_docx(
    data: bytes,
    *,
    name: str,
    base: StyleSheet,
    source_filename: str = "",
) -> StyleSheet:
    """Learn a stylesheet from a reference document, backfilling from `base`."""
    graph = parse_docx_bytes(data, title=name)
    sheet = base.model_copy(deep=True)
    sheet.name = name
    sheet.builtin = False
    sheet.id = ""  # the store assigns one
    sheet.derived_from = source_filename or "reference.docx"

    sheet.page = _page_from(graph, base.page)

    body = _style_for(graph, (NodeType.BODY, NodeType.PARAGRAPH), base.body)
    sheet.body = body
    sheet.heading1 = _style_for(graph, (NodeType.HEADING,), base.heading1)
    sheet.heading2 = _style_for(graph, (NodeType.SUBHEADING,), base.heading2)
    # level 3 rarely appears explicitly; derive from level 2 so the family matches
    sheet.heading3 = base.heading3.merged(
        Style(font=sheet.heading2.font, size_pt=sheet.heading2.size_pt)
    )

    caption = _style_for(graph, (NodeType.CAPTION,), base.figure_caption)
    sheet.figure_caption = caption
    sheet.table_caption = base.table_caption.merged(
        Style(font=caption.font, size_pt=caption.size_pt)
    )
    sheet.reference = _style_for(graph, (NodeType.REFERENCE,), base.reference)

    # keep the rest of the family on the sample's dominant body font
    if body.font:
        for field in ("title", "author", "affiliation", "abstract", "keywords",
                      "list_item", "equation", "table_header", "table_cell",
                      "references_heading"):
            current: Style = getattr(sheet, field)
            setattr(sheet, field, current.merged(Style(font=body.font)))

    return sheet


def _page_from(graph: DocumentGraph, fallback: PageSetup) -> PageSetup:
    page = graph.root.metadata.get("page") or {}
    if not isinstance(page, dict) or not page.get("width_in"):
        return fallback.model_copy()
    margin = page.get("margin") or {}
    return PageSetup(
        width_in=float(page.get("width_in", fallback.width_in)),
        height_in=float(page.get("height_in", fallback.height_in)),
        margin_top_in=float(margin.get("top", fallback.margin_top_in)),
        margin_bottom_in=float(margin.get("bottom", fallback.margin_bottom_in)),
        margin_left_in=float(margin.get("left", fallback.margin_left_in)),
        margin_right_in=float(margin.get("right", fallback.margin_right_in)),
        # python-docx cannot read the column count reliably; keep the base's
        columns=fallback.columns,
        column_spacing_in=fallback.column_spacing_in,
    )


def _style_for(graph: DocumentGraph, types: tuple[NodeType, ...], fallback: Style) -> Style:
    """Majority-vote the formatting of all nodes of the given types."""
    nodes = [n for n in graph.nodes() if n.type in types and n.content.strip()]
    if not nodes:
        return fallback.model_copy()

    learned = Style(
        font=_majority(n.style.font_family for n in nodes),
        size_pt=_majority(n.style.font_size for n in nodes),
        bold=_majority(n.style.bold for n in nodes),
        italic=_majority(n.style.italic for n in nodes),
        color=_majority(n.style.color for n in nodes),
        alignment=_majority(n.style.alignment for n in nodes),
    )
    # learned values win; anything the sample didn't reveal stays from the base
    return fallback.merged(learned)


def _majority(values: Iterable) -> Optional[object]:
    present = [v for v in values if v is not None]
    if not present:
        return None
    return Counter(present).most_common(1)[0][0]
