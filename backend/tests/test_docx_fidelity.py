"""Rendering an imported document the way the file actually specifies it.

A document imported in the viewer's default font, at the viewer's default line
spacing, does not look like the document — and the wrong metrics need more room
than the page has, which is how text ended up cut off at the foot of a page.
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

from docx import Document
from docx.oxml import parse_xml
from docx.shared import Pt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.docos.graph import NodeType  # noqa: E402
from app.docos.parser.docx_parser import parse_docx_bytes  # noqa: E402

_NS = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
       'xmlns:v="urn:schemas-microsoft-com:vml" '
       'xmlns:o="urn:schemas-microsoft-com:office:office"')


def _render(doc):
    buf = io.BytesIO()
    doc.save(buf)
    return parse_docx_bytes(buf.getvalue(), title="t")


# ── typeface ────────────────────────────────────────────────────────────────

def test_the_documents_own_font_is_carried():
    """python-docx's template names its font by theme, as Word does."""
    graph = _render(Document())
    page = graph.root.metadata["page"]
    assert page["default_font"], "a theme font must be resolved to a real typeface"
    assert page["default_size_pt"] > 0


def test_a_font_set_on_the_style_is_found_without_run_formatting():
    """Most documents set their typeface once, on a style, never on a run."""
    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = "Garamond"
    normal.font.size = Pt(13)
    doc.add_paragraph("styled by the style, not the run")

    body = next(n for n in _render(doc).root.children if n.type == NodeType.BODY)
    assert body.style.font_family == "Garamond"
    assert body.style.font_size == 13


def test_run_formatting_still_wins_over_the_style():
    doc = Document()
    doc.styles["Normal"].font.name = "Garamond"
    p = doc.add_paragraph()
    run = p.add_run("directly formatted")
    run.font.name = "Consolas"

    body = next(n for n in _render(doc).root.children if n.type == NodeType.BODY)
    assert body.style.font_family == "Consolas"


# ── spacing ─────────────────────────────────────────────────────────────────

def test_line_spacing_is_carried():
    doc = Document()
    p = doc.add_paragraph("double spaced")
    p.paragraph_format.line_spacing = 2.0

    body = next(n for n in _render(doc).root.children if n.type == NodeType.BODY)
    assert body.metadata["line_spacing"] == 2.0
    assert body.metadata["line_spacing_exact"] is False


def test_exact_line_spacing_is_marked_as_exact():
    doc = Document()
    p = doc.add_paragraph("exactly 18pt")
    p.paragraph_format.line_spacing = Pt(18)

    body = next(n for n in _render(doc).root.children if n.type == NodeType.BODY)
    assert body.metadata["line_spacing_exact"] is True
    assert body.metadata["line_spacing"] == 18.0


def test_paragraph_gaps_are_carried():
    doc = Document()
    p = doc.add_paragraph("spaced")
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(6)

    body = next(n for n in _render(doc).root.children if n.type == NodeType.BODY)
    assert body.metadata["space_before_pt"] == 12.0
    assert body.metadata["space_after_pt"] == 6.0


# ── page boundaries around a rule ───────────────────────────────────────────

def test_a_rule_keeps_the_page_marker_it_sits_on():
    """The rule branch used to drop it, which moved every later page boundary
    and truncated the pages that held one."""
    doc = Document()
    doc.add_paragraph("before")
    p = doc.add_paragraph()
    p._p.append(parse_xml(
        f'<w:r {_NS}><w:lastRenderedPageBreak/>'
        '<w:pict><v:rect style="width:0;height:1.5pt" o:hr="t"/></w:pict></w:r>'))
    doc.add_paragraph("after")

    nodes = _render(doc).root.children
    marked = [n for n in nodes if n.metadata.get("page_break_before")]
    assert marked, "the page boundary must survive whatever the paragraph became"
