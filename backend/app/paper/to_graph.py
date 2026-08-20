"""PaperSpec → DocumentGraph, without going through a .docx.

Handing a composed document to the editor as a rendered .docx loses everything
the format has no word for. A code listing arrives as a run of ordinary
paragraphs, an equation as the characters that happened to be typeset, a chart
as an anonymous picture — because DOCX marks none of those as what they are. Once
that has happened the editor cannot put them back, and neither can an export.

Converting the spec directly keeps what the spec knows. The parts that are
*drawn* — charts, editor screenshots, console screenshots, typeset equations —
are rendered here exactly as the DOCX renderer would render them and carried as
images, so the editor shows the same picture the document would. The parts that
are text stay text, and stay editable.
"""
from __future__ import annotations

import base64
import tempfile
from pathlib import Path
from typing import Optional

from app.docos.graph import DocumentGraph, Node, NodeType, Style as GraphStyle
from app.paper.codeshot import render_code_image, render_terminal_image
from app.paper.equations import looks_like_math, render_equation_png
from app.paper.figures import render_figure
from app.paper.references import format_reference
from app.paper.schema import (
    Code, Equation, Figure, Heading, ListBlock, PageBreak,
    Paragraph as PBlock, PaperSpec, Style as PaperStyle, Table,
)
from app.paper.styles import resolve_style
from app.paper.stylesheet import resolve

_HEADING_TYPES = {1: NodeType.HEADING, 2: NodeType.SUBHEADING, 3: NodeType.SUBHEADING}


def spec_to_graph(spec: PaperSpec, *, title: str = "",
                  assets_dir: Optional[Path] = None) -> DocumentGraph:
    """Build a DocumentGraph from a PaperSpec, drawing what needs drawing."""
    if not spec.resolved:
        spec = resolve(spec, spec.meta.style or None)
    sheet = resolve_style(spec.meta.style or "report")

    assets = Path(assets_dir) if assets_dir else Path(tempfile.mkdtemp(prefix="spec_graph_"))
    assets.mkdir(parents=True, exist_ok=True)

    root = Node(type=NodeType.DOCUMENT, metadata={"source": "compose"})
    graph = DocumentGraph(root=root, title=title or spec.meta.title or "Untitled")

    _front_matter(root, spec)

    counters = {"figure": 0, "code": 0, "equation": 0}
    for block in spec.blocks:
        node = _block_node(block, spec, sheet, assets, counters)
        if node is not None:
            root.children.append(node)

    for i, ref in enumerate((format_reference(r) for r in spec.references), start=1):
        if ref:
            root.children.append(Node(type=NodeType.REFERENCE, content=f"[{i}] {ref}"))

    return graph


# ── front matter ────────────────────────────────────────────────────────────

def _front_matter(root: Node, spec: PaperSpec) -> None:
    m = spec.meta
    if m.title:
        root.children.append(Node(type=NodeType.HEADING, content=m.title,
                                  style=GraphStyle(bold=True, alignment="center"),
                                  metadata={"level": 0, "role": "title"}))
    for author in m.authors:
        line = ", ".join(x for x in (author.name, author.affiliation, author.email) if x)
        if line:
            root.children.append(Node(type=NodeType.BODY, content=line,
                                      style=GraphStyle(alignment="center")))
    for line in m.title_page_lines:
        if line.strip():
            root.children.append(Node(type=NodeType.BODY, content=line,
                                      style=GraphStyle(alignment="center")))
    if m.title_page:
        root.children.append(Node(type=NodeType.PAGE_BREAK, metadata={"breaks": 1}))
    if m.abstract:
        root.children.append(Node(type=NodeType.HEADING, content="Abstract",
                                  metadata={"level": 1}))
        root.children.append(Node(type=NodeType.BODY, content=m.abstract))
    if m.keywords:
        root.children.append(Node(type=NodeType.BODY,
                                  content="Keywords: " + ", ".join(m.keywords),
                                  style=GraphStyle(italic=True)))


# ── blocks ──────────────────────────────────────────────────────────────────

def _block_node(block, spec: PaperSpec, sheet, assets: Path,
                counters: dict[str, int]) -> Optional[Node]:
    if isinstance(block, Heading):
        level = max(1, min(3, block.level))
        return Node(type=_HEADING_TYPES[level], content=block.text,
                    style=_style(block.style), metadata={"level": level})

    if isinstance(block, PBlock):
        return Node(type=NodeType.BODY, content=block.text, style=_style(block.style))

    if isinstance(block, ListBlock):
        # One node per item: a list the editor cannot address item by item is
        # just a paragraph with bullets typed into it.
        items = [
            Node(type=NodeType.BODY,
                 content=f"{i}. {text}" if block.ordered else f"• {text}",
                 style=_style(block.style), metadata={"list_item": True})
            for i, text in enumerate(block.items, start=1)
        ]
        return Node(type=NodeType.PARAGRAPH, children=items,
                    metadata={"list": True, "ordered": block.ordered}) if items else None

    if isinstance(block, PageBreak):
        return Node(type=NodeType.PAGE_BREAK, metadata={"breaks": 1})

    if isinstance(block, Table):
        return _table_node(block)

    if isinstance(block, Figure):
        counters["figure"] += 1
        return _figure_node(block, counters["figure"], assets, sheet)

    if isinstance(block, Code):
        counters["code"] += 1
        return _code_node(block, counters["code"], assets, sheet)

    if isinstance(block, Equation):
        counters["equation"] += 1
        return _equation_node(block, counters["equation"], assets, sheet)

    return None


def _table_node(block: Table) -> Optional[Node]:
    columns = block.columns or (block.rows[0] if block.rows else [])
    if not columns:
        return None

    rows: list[Node] = []
    if block.columns:
        rows.append(Node(type=NodeType.TABLE_ROW, metadata={"header": True}, children=[
            Node(type=NodeType.TABLE_CELL, content=str(c),
                 style=GraphStyle(bold=True)) for c in block.columns
        ]))
    for row in block.rows:
        rows.append(Node(type=NodeType.TABLE_ROW, children=[
            Node(type=NodeType.TABLE_CELL,
                 content=str(row[i]) if i < len(row) else "")
            for i in range(len(columns))
        ]))

    children = rows
    if block.caption:
        children = children + [Node(type=NodeType.CAPTION, content=block.caption)]
    return Node(type=NodeType.TABLE, children=children,
                metadata={"rows": len(rows), "cols": len(columns),
                          "caption": block.caption})


def _figure_node(block: Figure, number: int, assets: Path, sheet) -> Optional[Node]:
    image: Optional[Path] = None
    if block.chart:
        try:
            image = render_figure(block.chart, assets / f"fig_{number}.png")
        except Exception:
            image = None
    elif block.image_path and Path(block.image_path).exists():
        image = Path(block.image_path)

    if not (image and image.exists()):
        return None     # the same rule the DOCX renderer follows: no blank figures

    children = [_image_node(image, block.caption)]
    if block.caption:
        children.append(Node(type=NodeType.CAPTION,
                             content=f"{sheet.figure_caption_prefix.format(num=number)}"
                                     f"{sheet.figure_caption_separator}{block.caption}"))
    return Node(type=NodeType.FIGURE, children=children,
                metadata={"number": number, "kind": "chart"})


def _code_node(block: Code, number: int, assets: Path, sheet) -> Optional[Node]:
    if not (block.text or "").strip():
        return None

    caption = " — ".join(x for x in (block.filename, block.caption) if x)
    label = sheet.code_caption_prefix.format(num=number)

    if block.render == "image":
        try:
            from app.paper.renderer import _is_terminal
            if _is_terminal(block):
                shot = render_terminal_image(block.text, assets / f"code_{number}.png",
                                             title=block.filename or "Command Prompt",
                                             theme=block.theme)
            else:
                shot = render_code_image(block.text, assets / f"code_{number}.png",
                                         language=block.language,
                                         filename=block.filename, theme=block.theme)
        except Exception:
            shot = None
        if shot and shot.exists():
            children = [_image_node(shot, caption)]
            if caption:
                children.append(Node(type=NodeType.CAPTION, content=f"{label} {caption}"))
            return Node(type=NodeType.FIGURE, children=children,
                        metadata={"number": number, "kind": "code_screenshot",
                                  "language": block.language, "code": block.text})

    # Text listing: one node per line so it never reflows, and the code itself is
    # kept on the parent so an export can still tell this was a listing.
    lines = [
        Node(type=NodeType.BODY, content=line or " ",
             style=GraphStyle(font_family="Courier New"),
             metadata={"code_line": True})
        for line in block.text.splitlines()
    ]
    if caption:
        lines.insert(0, Node(type=NodeType.CAPTION, content=f"{label} {caption}"))
    return Node(type=NodeType.PARAGRAPH, children=lines,
                metadata={"kind": "code", "language": block.language,
                          "code": block.text})


def _equation_node(block: Equation, number: int, assets: Path, sheet) -> Node:
    wants_image = block.render == "image" or (
        block.render == "auto" and looks_like_math(block.text))
    if wants_image:
        try:
            image, _width = render_equation_png(
                block.text, assets / f"eq_{number}.png",
                size_pt=sheet.equation.size_pt or 11)
            node = _image_node(image, block.text)
            # The markup travels with the picture, so the equation stays editable
            # and an export can typeset it again rather than shipping the bitmap.
            node.metadata.update({"equation": block.text, "number": number})
            return Node(type=NodeType.FIGURE, children=[node],
                        metadata={"kind": "equation", "equation": block.text,
                                  "number": number})
        except Exception:
            pass    # unparseable markup falls through to text, as in the document

    return Node(type=NodeType.BODY, content=block.text,
                style=GraphStyle(italic=True, alignment="center"),
                metadata={"kind": "equation", "equation": block.text,
                          "number": number})


# ── helpers ─────────────────────────────────────────────────────────────────

def _image_node(path: Path, caption: str = "") -> Node:
    data = path.read_bytes()
    suffix = path.suffix.lower().lstrip(".") or "png"
    content_type = f"image/{'jpeg' if suffix in ('jpg', 'jpeg') else suffix}"
    return Node(
        type=NodeType.IMAGE,
        content=caption,
        metadata={
            "is_figure": True,
            "src": f"data:{content_type};base64," + base64.b64encode(data).decode("ascii"),
            "bytes": len(data),
        },
    )


def _style(style: Optional[PaperStyle]) -> GraphStyle:
    """Carry across the formatting the graph has a word for."""
    if style is None:
        return GraphStyle()
    return GraphStyle(
        bold=bool(style.bold),
        italic=bool(style.italic),
        underline=bool(style.underline),
        font_size=style.size_pt,
        font_family=style.font,
        color=style.color,
        alignment=style.alignment,
    )
