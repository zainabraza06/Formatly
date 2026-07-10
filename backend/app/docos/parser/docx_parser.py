"""DOCX → DocumentGraph.

Walks the document body in document order (paragraphs and tables interleaved),
classifies each block into a typed node, and aggregates run-level formatting into
a paragraph-level Style. Images, captions, horizontal rules, page breaks and
references are detected heuristically from styles and XML markers.
"""
from __future__ import annotations

import io
from pathlib import Path
from typing import Optional

from docx import Document
from docx.document import Document as _Doc
from docx.oxml.ns import qn
from docx.table import Table as _Table
from docx.text.paragraph import Paragraph as _Paragraph

from app.docos.graph import DocumentGraph, Node, NodeType, Style

_HEADING_STYLES = ("heading", "title")
_REFERENCE_HINTS = ("reference", "bibliography", "works cited")


def parse_docx_bytes(data: bytes, *, title: str = "") -> DocumentGraph:
    return _parse(Document(io.BytesIO(data)), title=title)


def parse_docx(path: str | Path, *, title: str = "") -> DocumentGraph:
    p = Path(path)
    return _parse(Document(str(p)), title=title or p.stem)


# ── core ────────────────────────────────────────────────────────────────────

def _parse(doc: _Doc, *, title: str) -> DocumentGraph:
    root = Node(type=NodeType.DOCUMENT, metadata={"source": "docx"})
    graph = DocumentGraph(root=root, title=title)

    root.metadata["page"] = _page_geometry(doc)

    in_references = False
    body = doc.element.body

    for child in body.iterchildren():
        tag = child.tag
        if tag == qn("w:p"):
            para = _Paragraph(child, doc)
            node = _paragraph_node(para, in_references)
            if node is None:
                continue
            if node.type == NodeType.HEADING and _looks_like_references(para.text):
                in_references = True
            root.children.append(node)
        elif tag == qn("w:tbl"):
            root.children.append(_table_node(_Table(child, doc), doc))

    _attach_headers_footers(doc, root)
    return graph


def _page_geometry(doc: _Doc) -> dict:
    """Real page size + margins (inches) from the first section, so the editor can
    render the sheet at the document's actual dimensions (A4, Letter, …)."""
    def _in(v, default: float) -> float:
        try:
            return round(float(v.inches), 3)
        except Exception:
            return default

    try:
        sec = doc.sections[0]
    except (IndexError, Exception):  # noqa: B014 - defensive
        return {"width_in": 8.5, "height_in": 11.0,
                "margin": {"top": 1.0, "right": 1.0, "bottom": 1.0, "left": 1.0}}

    w = _in(sec.page_width, 8.5)
    h = _in(sec.page_height, 11.0)
    landscape = str(getattr(sec, "orientation", "")).endswith("LANDSCAPE")
    if landscape and w < h:
        w, h = h, w
    return {
        "width_in": w,
        "height_in": h,
        "landscape": landscape,
        "margin": {
            "top": _in(sec.top_margin, 1.0),
            "right": _in(sec.right_margin, 1.0),
            "bottom": _in(sec.bottom_margin, 1.0),
            "left": _in(sec.left_margin, 1.0),
        },
    }


def _looks_like_references(text: str) -> bool:
    t = (text or "").strip().lower()
    return any(h in t for h in _REFERENCE_HINTS)


def _paragraph_node(para: _Paragraph, in_references: bool) -> Optional[Node]:
    style_name = (para.style.name if para.style else "") or ""
    lname = style_name.lower()
    text = para.text or ""

    # Page-boundary signals. `lastRenderedPageBreak` markers are written by Word
    # and record where each page actually broke on the last render — we use them
    # so the editor's page count matches the real document (not a node count).
    explicit, rendered = _page_break_signals(para)
    breaks_before = (1 if explicit else 0) + rendered

    # dedicated page-break paragraph (a break with no real content)
    if breaks_before and not text.strip() and not _has_drawing(para):
        return Node(type=NodeType.PAGE_BREAK,
                    metadata={"style_name": style_name, "breaks": breaks_before})

    # image / figure: paragraph carrying a drawing
    if _has_drawing(para):
        node = Node(
            type=NodeType.IMAGE,
            content=text.strip(),
            style=_paragraph_style(para),
            metadata={"style_name": style_name, "is_figure": True},
        )
        # a figure is an image wrapped with a caption relationship
        fig = Node(type=NodeType.FIGURE, children=[node], metadata={"style_name": style_name})
        if breaks_before:
            fig.metadata["page_break_before"] = breaks_before
        return fig

    # horizontal rule: empty paragraph with a bottom border
    if not text.strip() and _has_bottom_border(para):
        return Node(type=NodeType.HORIZONTAL_RULE, metadata={"style_name": style_name})

    # skip truly empty spacer paragraphs (keep them out of the graph)
    if not text.strip() and not _has_bottom_border(para):
        return None

    node_type = _classify_paragraph(lname, in_references)
    meta: dict = {"style_name": style_name, "level": _heading_level(lname)}
    if breaks_before:
        meta["page_break_before"] = breaks_before
    return Node(
        type=node_type,
        content=text,
        style=_paragraph_style(para),
        metadata=meta,
    )


def _classify_paragraph(lname: str, in_references: bool) -> NodeType:
    if lname.startswith("title"):
        return NodeType.HEADING
    if lname.startswith("heading"):
        lvl = _heading_level(lname)
        return NodeType.HEADING if lvl <= 1 else NodeType.SUBHEADING
    if "caption" in lname:
        return NodeType.CAPTION
    if in_references:
        return NodeType.REFERENCE
    if "footnote" in lname:
        return NodeType.FOOTNOTE
    return NodeType.BODY


def _heading_level(lname: str) -> int:
    if lname.startswith("title"):
        return 0
    if lname.startswith("heading"):
        tail = lname.replace("heading", "").strip()
        return int(tail) if tail.isdigit() else 1
    return 0


def _paragraph_style(para: _Paragraph) -> Style:
    """Aggregate run formatting to a paragraph-level style (majority wins)."""
    sizes: list[float] = []
    bolds: list[bool] = []
    italics: list[bool] = []
    underlines: list[bool] = []
    colors: list[str] = []
    families: list[str] = []

    for run in para.runs:
        f = run.font
        if f.size is not None:
            sizes.append(f.size.pt)
        if run.bold is not None:
            bolds.append(bool(run.bold))
        if run.italic is not None:
            italics.append(bool(run.italic))
        if run.underline is not None:
            underlines.append(bool(run.underline))
        if f.color is not None and f.color.rgb is not None:
            colors.append(f"#{str(f.color.rgb)}")
        if f.name:
            families.append(f.name)

    align = None
    if para.alignment is not None:
        align = {0: "left", 1: "center", 2: "right", 3: "justify"}.get(int(para.alignment), None)

    def _majority(vals: list) -> Optional[object]:
        if not vals:
            return None
        return max(set(vals), key=vals.count)

    return Style(
        font_family=_majority(families),
        font_size=_majority(sizes),
        bold=_majority(bolds),
        italic=_majority(italics),
        underline=_majority(underlines),
        color=_majority(colors),
        alignment=align,
    )


def _table_node(table: _Table, doc: _Doc) -> Node:
    rows: list[Node] = []
    for r in table.rows:
        cells: list[Node] = []
        for c in r.cells:
            cells.append(
                Node(
                    type=NodeType.TABLE_CELL,
                    content=c.text,
                    metadata={},
                )
            )
        rows.append(Node(type=NodeType.TABLE_ROW, children=cells))
    return Node(
        type=NodeType.TABLE,
        children=rows,
        metadata={"rows": len(table.rows), "cols": len(table.columns)},
    )


def _attach_headers_footers(doc: _Doc, root: Node) -> None:
    for section in doc.sections:
        htext = "\n".join(p.text for p in section.header.paragraphs if p.text.strip())
        ftext = "\n".join(p.text for p in section.footer.paragraphs if p.text.strip())
        if htext:
            root.children.insert(0, Node(type=NodeType.HEADER, content=htext))
        if ftext:
            root.children.append(Node(type=NodeType.FOOTER, content=ftext))
        break  # first section only — keeps the graph clean


# ── low-level XML probes ────────────────────────────────────────────────────

def _has_drawing(para: _Paragraph) -> bool:
    return bool(para._p.findall(".//" + qn("w:drawing"))) or bool(
        para._p.findall(".//" + qn("w:pict"))
    )


def _page_break_signals(para: _Paragraph) -> tuple[bool, int]:
    """Return (has_explicit_break, rendered_break_count).

    `explicit`  — a manual page break the author inserted (w:br type=page).
    `rendered`  — how many `w:lastRenderedPageBreak` markers Word left in this
                  paragraph, i.e. how many page boundaries fall on it.
    """
    explicit = any(
        br.get(qn("w:type")) == "page"
        for br in para._p.findall(".//" + qn("w:br"))
    )
    rendered = len(para._p.findall(".//" + qn("w:lastRenderedPageBreak")))
    return explicit, rendered


def _has_bottom_border(para: _Paragraph) -> bool:
    pPr = para._p.find(qn("w:pPr"))
    if pPr is None:
        return False
    pBdr = pPr.find(qn("w:pBdr"))
    if pBdr is None:
        return False
    return pBdr.find(qn("w:bottom")) is not None or pBdr.find(qn("w:top")) is not None
