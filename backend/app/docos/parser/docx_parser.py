"""DOCX → DocumentGraph.

Walks the document body in document order (paragraphs and tables interleaved),
classifies each block into a typed node, and aggregates run-level formatting into
a paragraph-level Style. Images, captions, horizontal rules, page breaks and
references are detected heuristically from styles and XML markers.
"""
from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Any, NamedTuple, Optional

from docx import Document
from docx.document import Document as _Doc
from docx.oxml.ns import qn
from docx.table import Table as _Table
from docx.text.paragraph import Paragraph as _Paragraph

from app.docos.graph import DocumentGraph, Node, NodeType, Style

_HEADING_STYLES = ("heading", "title")
_REFERENCE_HINTS = ("reference", "bibliography", "works cited")

# VML lives outside python-docx's namespace map, so these are spelled in full.
_V_NS = "urn:schemas-microsoft-com:vml"
_O_NS = "urn:schemas-microsoft-com:office:office"
_V_IMAGEDATA = f"{{{_V_NS}}}imagedata"
_V_RECT = f"{{{_V_NS}}}rect"
_O_HR = f"{{{_O_NS}}}hr"

# Images travel inline as data URIs so the editor can show the real picture
# without a second round trip. Past this size that stops being reasonable and
# the node keeps its place in the document without the bytes.
_MAX_INLINE_IMAGE_BYTES = 4 * 1024 * 1024


def parse_docx_bytes(data: bytes, *, title: str = "") -> DocumentGraph:
    return _parse(Document(io.BytesIO(data)), title=title)


def parse_docx(path: str | Path, *, title: str = "") -> DocumentGraph:
    p = Path(path)
    return _parse(Document(str(p)), title=title or p.stem)


# ── core ────────────────────────────────────────────────────────────────────

def _parse(doc: _Doc, *, title: str) -> DocumentGraph:
    root = Node(type=NodeType.DOCUMENT, metadata={"source": "docx"})
    graph = DocumentGraph(root=root, title=title)

    page = _page_geometry(doc)
    default_font, default_size = _document_default_font(doc)
    # Carried so the sheet is laid out in the document's own typeface. Rendering
    # it in the viewer's default is what made an imported file look shifted, and
    # the wrong metrics are what pushed text past the bottom of the page.
    page["default_font"] = default_font or ""
    page["default_size_pt"] = default_size or 11.0
    root.metadata["page"] = page

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

    images = _images(para)
    is_rule = not text.strip() and (_has_bottom_border(para) or _is_vml_rule(para))

    # A rule drawn as a picture, or decoration whose image will not resolve: an
    # empty paragraph with nothing readable in it is not a figure, and showing
    # it as a broken one puts a false alarm in the middle of the text.
    #
    # This is decided before the page-break case on purpose. A rule frequently
    # sits exactly where Word broke the page, and treating that paragraph as a
    # bare break threw the rule away — so the line vanished from precisely the
    # pages a reader would notice. The rule keeps the marker instead.
    if is_rule:
        meta: dict = {"style_name": style_name}
        _apply_breaks(meta, breaks_before)
        return Node(type=NodeType.HORIZONTAL_RULE, metadata=meta)

    # dedicated page-break paragraph (a break with no real content)
    if breaks_before and not text.strip() and not images:
        return Node(type=NodeType.PAGE_BREAK,
                    metadata={"style_name": style_name, "breaks": breaks_before})

    # figure: a paragraph carrying one or more actual pictures
    if images:
        style = _paragraph_style(para)
        children = [
            Node(
                type=NodeType.IMAGE,
                content=text.strip() if len(images) == 1 else "",
                style=style,
                metadata={"style_name": style_name, "is_figure": True, **img},
            )
            for img in images
        ]
        fig = Node(type=NodeType.FIGURE, children=children,
                   metadata={"style_name": style_name})
        _apply_breaks(fig.metadata, breaks_before)
        return fig

    # skip truly empty spacer paragraphs (keep them out of the graph)
    if not text.strip():
        return None

    node_type = _classify_paragraph(lname, in_references)
    meta: dict = {"style_name": style_name, "level": _heading_level(lname)}
    meta.update(_spacing(para))
    _apply_breaks(meta, breaks_before)
    return Node(
        type=node_type,
        content=text,
        style=_paragraph_style(para),
        metadata=meta,
    )


def _spacing(para: _Paragraph) -> dict:
    """Line spacing and the gaps around a paragraph, in the units CSS wants.

    A document set single-spaced and rendered at 1.5 needs half again as much
    room as it has, which is how text ended up cut off at the foot of a page.
    """
    out: dict = {}
    try:
        pf = para.paragraph_format
        if pf.line_spacing is not None:
            # a float is a multiple; a Length is an exact height
            out["line_spacing"] = (float(pf.line_spacing)
                                   if isinstance(pf.line_spacing, float)
                                   else round(pf.line_spacing.pt, 1))
            out["line_spacing_exact"] = not isinstance(pf.line_spacing, float)
        if pf.space_before is not None:
            out["space_before_pt"] = round(pf.space_before.pt, 1)
        if pf.space_after is not None:
            out["space_after_pt"] = round(pf.space_after.pt, 1)
    except Exception:
        pass
    return out


def _apply_breaks(meta: dict, breaks_before: int) -> None:
    """Encode page-boundary metadata: `page_break_before` starts a new page before
    this node; `extra_pages` is how many *additional* pages the node spans (a long
    paragraph or a table that Word split across pages)."""
    if breaks_before >= 1:
        meta["page_break_before"] = True
    if breaks_before > 1:
        meta["extra_pages"] = breaks_before - 1


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


class StyleFont(NamedTuple):
    """What a paragraph style, and the styles it inherits from, say about type."""
    name: Optional[str] = None
    size: Optional[float] = None
    bold: Optional[bool] = None
    italic: Optional[bool] = None
    underline: Optional[bool] = None
    color: Optional[str] = None


def _style_font(style) -> StyleFont:
    """Walk a paragraph style and the styles it inherits from for its type.

    Most documents set their typeface once, on a style, and never touch a run.
    Reading only run formatting therefore finds nothing and the document renders
    in whatever the viewer defaults to — which is why an imported file came out
    in the wrong face at the wrong size.

    Emphasis works the same way and was read only off the runs, so a paragraph
    that is italic because its style is italic — an IEEE abstract, a block
    quotation — arrived with no italic at all.
    """
    found: dict[str, Any] = {}
    seen = 0
    while style is not None and seen < 10:      # guard a cyclic base_style chain
        font = getattr(style, "font", None)
        if font is not None:
            if found.get("name") is None and font.name:
                found["name"] = font.name
            if found.get("size") is None and font.size is not None:
                try:
                    found["size"] = float(font.size.pt)
                except (AttributeError, TypeError):
                    pass
            # None means "inherit from the style I am based on", so only a real
            # True/False here settles the question.
            for attr in ("bold", "italic", "underline"):
                if found.get(attr) is None and getattr(font, attr, None) is not None:
                    found[attr] = bool(getattr(font, attr))
            if found.get("color") is None:
                rgb = getattr(getattr(font, "color", None), "rgb", None)
                if rgb is not None:
                    found["color"] = f"#{rgb}"
        if len(found) == 6:
            break
        style = getattr(style, "base_style", None)
        seen += 1
    return StyleFont(**found)


def _document_default_font(doc: _Doc) -> tuple[Optional[str], Optional[float]]:
    """The typeface a document falls back to: the Normal style, then docDefaults."""
    try:
        name, size = _style_font(doc.styles["Normal"])[:2]
    except (KeyError, AttributeError):
        name = size = None

    if name and size:
        return name, size

    try:
        rpr = doc.styles.element.find(qn("w:docDefaults"))
        if rpr is not None:
            fonts = rpr.find(".//" + qn("w:rFonts"))
            if name is None and fonts is not None:
                # A literal face if there is one; otherwise the document names a
                # *theme* font, and the actual typeface lives in theme1.xml.
                name = (fonts.get(qn("w:ascii")) or fonts.get(qn("w:hAnsi"))
                        or _theme_font(doc, fonts.get(qn("w:asciiTheme"))
                                       or fonts.get(qn("w:hAnsiTheme"))))
            sz = rpr.find(".//" + qn("w:sz"))
            if size is None and sz is not None and sz.get(qn("w:val")):
                size = float(sz.get(qn("w:val"))) / 2   # half-points
    except Exception:
        pass
    return name, size


_A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"


def _theme_font(doc: _Doc, theme_ref: Optional[str]) -> Optional[str]:
    """Resolve "minorHAnsi" / "majorHAnsi" to the typeface the theme names."""
    if not theme_ref:
        return None
    scheme = "majorFont" if theme_ref.startswith("major") else "minorFont"
    try:
        for rel in doc.part.rels.values():
            if not rel.reltype.endswith("/theme") or rel.is_external:
                continue
            part = rel.target_part
            # The theme is an opaque part in python-docx, so it usually has to
            # be parsed from its bytes rather than read as an element tree.
            root = getattr(part, "element", None)
            if root is None:
                from lxml import etree
                root = etree.fromstring(part.blob)
            element = root.find(f".//{{{_A_NS}}}{scheme}/{{{_A_NS}}}latin")
            if element is not None:
                return element.get("typeface") or None
    except Exception:
        pass
    return None


def _paragraph_style(para: _Paragraph) -> Style:
    """Aggregate run formatting to a paragraph-level style (majority wins)."""
    # Each entry is (value, weight), the weight being how many characters carry
    # it. Counting runs instead let a three-word italic label outvote the
    # paragraph it introduces.
    sizes: list[tuple[float, int]] = []
    bolds: list[tuple[bool, int]] = []
    italics: list[tuple[bool, int]] = []
    underlines: list[tuple[bool, int]] = []
    colors: list[tuple[str, int]] = []
    families: list[tuple[str, int]] = []

    for run in para.runs:
        f = run.font
        weight = len(run.text or "")
        if not weight:
            continue                      # an empty run describes no text
        if f.size is not None:
            sizes.append((f.size.pt, weight))
        if run.bold is not None:
            bolds.append((bool(run.bold), weight))
        if run.italic is not None:
            italics.append((bool(run.italic), weight))
        if run.underline is not None:
            underlines.append((bool(run.underline), weight))
        if f.color is not None and f.color.rgb is not None:
            colors.append((f"#{str(f.color.rgb)}", weight))
        if f.name:
            families.append((f.name, weight))

    # Runs win where they say something; otherwise the paragraph's own style,
    # and the styles it inherits from, decide. Emphasis is included: a run that
    # says nothing about italic is not a run that is upright.
    if not (families and sizes and bolds and italics and underlines and colors):
        from_style = _style_font(getattr(para, "style", None))
        length = len(para.text or "") or 1
        if not families and from_style.name:
            families.append((from_style.name, length))
        if not sizes and from_style.size:
            sizes.append((from_style.size, length))
        if not bolds and from_style.bold is not None:
            bolds.append((from_style.bold, length))
        if not italics and from_style.italic is not None:
            italics.append((from_style.italic, length))
        if not underlines and from_style.underline is not None:
            underlines.append((from_style.underline, length))
        if not colors and from_style.color:
            colors.append((from_style.color, length))

    align = None
    if para.alignment is not None:
        align = {0: "left", 1: "center", 2: "right", 3: "justify"}.get(int(para.alignment), None)

    def _majority(weighted: list[tuple[Any, int]]) -> Optional[Any]:
        """The value carrying the most text, and on a tie the one that came first.

        `max(set(...))` used to leave a tie to set ordering, so a paragraph split
        evenly between italic and upright runs came out one way on one import and
        the other way on the next.
        """
        if not weighted:
            return None
        totals: dict[Any, int] = {}
        for value, weight in weighted:
            totals[value] = totals.get(value, 0) + weight
        order = [value for value, _ in weighted]
        return max(totals, key=lambda v: (totals[v], -order.index(v)))

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
            # A cell's pictures come with it. Reading only c.text dropped any
            # screenshot placed in a table — a common way to lay out figures.
            pictures: list[Node] = []
            for para in c.paragraphs:
                for img in _images(para):
                    pictures.append(Node(type=NodeType.IMAGE,
                                         metadata={"is_figure": True, **img}))
            cells.append(
                Node(
                    type=NodeType.TABLE_CELL,
                    content=c.text,
                    children=pictures,
                    metadata={},
                )
            )
        rows.append(Node(type=NodeType.TABLE_ROW, children=cells))
    meta: dict = {"rows": len(table.rows), "cols": len(table.columns)}
    # A long table Word split across pages carries lastRenderedPageBreak markers
    # inside its cells; count them so the total page count stays accurate.
    internal_breaks = len(table._tbl.findall(".//" + qn("w:lastRenderedPageBreak")))
    if internal_breaks:
        meta["extra_pages"] = internal_breaks
    return Node(type=NodeType.TABLE, children=rows, metadata=meta)


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
    """Any drawing markup at all — a picture, but also a shape or a rule."""
    return bool(para._p.findall(".//" + qn("w:drawing"))) or bool(
        para._p.findall(".//" + qn("w:pict"))
    )


def _image_rel_ids(para: _Paragraph) -> list[str]:
    """Relationship ids of the *pictures* in this paragraph.

    A picture is markup that points at an image part: a DrawingML blip, or a VML
    shape with imagedata. Drawing markup on its own proves nothing — Word writes
    a horizontal rule as a VML rect inside w:pict, and treating that as a picture
    is what turned every rule in an imported document into a figure.
    """
    ids: list[str] = []
    for blip in para._p.findall(".//" + qn("a:blip")):
        rid = blip.get(qn("r:embed")) or blip.get(qn("r:link"))
        if rid:
            ids.append(rid)
    for imagedata in para._p.findall(".//" + _V_IMAGEDATA):
        rid = imagedata.get(qn("r:id")) or imagedata.get(qn("r:href"))
        if rid:
            ids.append(rid)
    return ids


def _images(para: _Paragraph) -> list[dict[str, Any]]:
    """The pictures in this paragraph, each with its bytes inlined as a data URI.

    A picture whose part cannot be read, or that is too large to inline, still
    yields a node — the document keeps its shape, and only the pixels are
    missing.
    """
    out: list[dict[str, Any]] = []
    for rid in _image_rel_ids(para):
        item: dict[str, Any] = {"rel_id": rid}
        try:
            item.update(_resolve_image(para.part, rid))
        except Exception:
            item["unreadable"] = True   # the node still holds the picture's place
        out.append(item)
    return out


def _resolve_image(part: Any, rid: str) -> dict[str, Any]:
    """Read one image relationship.

    Two kinds arrive. An *embedded* image has its bytes inside the file and is
    inlined as a data URI. A *linked* image has none — the document only points
    at where the picture lives, which is what LibreOffice writes when it converts
    HTML and what Word writes for "Link to File". Those are not corrupt, and
    reporting them as unreadable was wrong: an http(s) target is passed through
    for the browser to load, exactly as Word would, and anything else is marked
    as linked so the reader is told the picture is not in the document.
    """
    rel = part.rels[rid]

    if getattr(rel, "is_external", False):
        target = str(getattr(rel, "target_ref", "") or "")
        if target.lower().startswith(("http://", "https://")):
            return {"src": target, "external": True}
        return {"linked_to": target, "external": True}

    blob = rel.target_part.blob
    if len(blob) > _MAX_INLINE_IMAGE_BYTES:
        return {"too_large": len(blob)}

    content_type = getattr(rel.target_part, "content_type", "") or "image/png"
    return {
        "src": f"data:{content_type};base64," + base64.b64encode(blob).decode("ascii"),
        "bytes": len(blob),
    }


def _is_vml_rule(para: _Paragraph) -> bool:
    """Is this paragraph one of Word's horizontal rules?

    Word writes a rule two ways, and both are drawing markup. The plain one is a
    VML rect. The one from the Horizontal Line gallery is a *picture of a line* —
    a VML shape carrying imagedata — so "it references an image" cannot be the
    test. What both share is the o:hr flag, which says outright that the shape is
    a rule, wherever it sits in the markup.
    """
    for pict in para._p.findall(".//" + qn("w:pict")):
        for element in pict.iter():
            if element.get(_O_HR) is not None:
                return True
        # a rect with no image behind it is decoration, not a picture
        if not pict.findall(".//" + _V_IMAGEDATA) and pict.findall(".//" + _V_RECT):
            return True
    return False


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
