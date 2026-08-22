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


# ── emphasis that lives on the style, not the runs ──────────────────────────

def _emphasis_docx() -> bytes:
    """Four paragraphs, each a different way of saying (or not saying) italic."""
    import io
    from docx import Document
    from docx.shared import Pt

    d = Document()
    p = d.add_paragraph(); r = p.add_run("Every run italic. " * 6); r.italic = True

    style = d.styles.add_style("AbstractStyle", 1)
    style.font.italic = True
    style.font.size = Pt(9)
    d.add_paragraph("Italic from the paragraph style. " * 6, style="AbstractStyle")

    p = d.add_paragraph()
    lead = p.add_run("A long italic lead. " * 6); lead.italic = True
    tail = p.add_run("Short roman tail."); tail.italic = False

    p = d.add_paragraph()
    label = p.add_run("Index Terms— "); label.italic = True
    body = p.add_run("A much longer upright body of text. " * 6); body.italic = False

    buf = io.BytesIO(); d.save(buf); return buf.getvalue()


def test_italic_is_read_from_the_paragraph_style_too():
    """An IEEE abstract is italic because its *style* is, and no run says so."""
    graph = parse_docx_bytes(_emphasis_docx(), title="E")
    paras = [n for n in graph.nodes() if n.content and "Italic from the paragraph style" in n.content]
    assert paras and paras[0].style.italic is True
    assert paras[0].style.font_size == 9.0


def test_mixed_runs_are_weighted_by_how_much_text_carries_them():
    graph = parse_docx_bytes(_emphasis_docx(), title="E")
    by_text = {n.content[:20]: n.style for n in graph.nodes() if n.content}

    # A long italic lead outweighs a short upright tail...
    lead = next(s for t, s in by_text.items() if t.startswith("A long italic lead"))
    assert lead.italic is True
    # ...and a three-word italic label does not make a whole paragraph italic.
    label = next(s for t, s in by_text.items() if t.startswith("Index Terms—"))
    assert label.italic is False


def test_every_run_italic_still_reads_as_italic():
    graph = parse_docx_bytes(_emphasis_docx(), title="E")
    para = next(n for n in graph.nodes() if n.content and n.content.startswith("Every run italic"))
    assert para.style.italic is True
