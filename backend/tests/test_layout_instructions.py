"""Layout a user can ask for: a cover sheet, a page break, per-block formatting.

A formatting instruction can only be obeyed if the schema can express it. These
cover the primitives that make open-ended requests answerable rather than
needing a new rule per phrasing.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from docx import Document

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.paper.renderer import render_paper  # noqa: E402
from app.paper.schema import PaperSpec  # noqa: E402

_BODY = [{"type": "heading", "level": 1, "text": "Introduction"},
         {"type": "paragraph", "text": "Body text."}]


def _breaks(path) -> int:
    """Explicit page breaks in the document."""
    from docx.oxml.ns import qn
    doc = Document(str(path))
    return sum(1 for p in doc.paragraphs
               for br in p._p.iter(qn("w:br"))
               if br.get(qn("w:type")) == "page")


def _texts(path) -> list[str]:
    return [p.text for p in Document(str(path)).paragraphs if p.text.strip()]


# ── cover sheet ─────────────────────────────────────────────────────────────

def test_no_cover_sheet_unless_asked(tmp_path):
    """A paper must not suddenly grow a title page."""
    spec = PaperSpec.model_validate({
        "meta": {"title": "A Paper", "style": "ieee"}, "blocks": _BODY})
    out = render_paper(spec, tmp_path / "d.docx")
    assert _breaks(out) == 0


def test_cover_sheet_holds_only_what_was_named(tmp_path):
    spec = PaperSpec.model_validate({
        "meta": {"title": "Number Guessing Game", "style": "assignment",
                 "title_page": True,
                 "title_page_lines": ["Student ID: 503840", "Course: FOCP"],
                 "authors": [{"name": "zainab", "affiliation": "NUST"}]},
        "blocks": _BODY,
    })
    out = render_paper(spec, tmp_path / "d.docx")
    texts = _texts(out)
    cover = texts[:texts.index("1. Introduction")] if "1. Introduction" in texts else texts[:5]
    assert "Number Guessing Game" in cover
    assert "zainab" in cover and "NUST" in cover
    assert "Student ID: 503840" in cover and "Course: FOCP" in cover
    assert _breaks(out) == 1, "the document should start on the page after the cover"


def test_cover_sheet_keeps_an_abstract_off_the_cover(tmp_path):
    """An abstract the brief did ask for belongs after the cover, not on it."""
    spec = PaperSpec.model_validate({
        "meta": {"title": "T", "style": "assignment", "title_page": True,
                 "abstract": "A summary that was asked for."},
        "blocks": _BODY,
    })
    out = render_paper(spec, tmp_path / "d.docx")
    texts = _texts(out)
    assert texts.index("T") < texts.index("A summary that was asked for.")
    assert _breaks(out) == 1


def test_empty_title_page_lines_are_skipped(tmp_path):
    spec = PaperSpec.model_validate({
        "meta": {"title": "T", "style": "assignment", "title_page": True,
                 "title_page_lines": ["Course: FOCP", "", "   "]},
        "blocks": _BODY,
    })
    out = render_paper(spec, tmp_path / "d.docx")
    assert "Course: FOCP" in _texts(out)


# ── page break ──────────────────────────────────────────────────────────────

def test_page_break_block_starts_a_new_page(tmp_path):
    spec = PaperSpec.model_validate({
        "meta": {"title": "T", "style": "assignment"},
        "blocks": [*_BODY, {"type": "page_break"},
                   {"type": "heading", "level": 1, "text": "Conclusion"}],
    })
    out = render_paper(spec, tmp_path / "d.docx")
    assert _breaks(out) == 1


def test_cover_sheet_and_page_breaks_coexist(tmp_path):
    spec = PaperSpec.model_validate({
        "meta": {"title": "T", "style": "assignment", "title_page": True},
        "blocks": [*_BODY, {"type": "page_break"},
                   {"type": "heading", "level": 1, "text": "Appendix"}],
    })
    out = render_paper(spec, tmp_path / "d.docx")
    assert _breaks(out) == 2


# ── per-block formatting overrides ──────────────────────────────────────────

@pytest.mark.parametrize("override,check", [
    ({"line_spacing": 2.0}, lambda p: p.paragraph_format.line_spacing == 2.0),
    ({"alignment": "center"}, lambda p: p.paragraph_format.alignment is not None),
    ({"bold": True}, lambda p: p.runs[0].bold is True),
    ({"font": "Arial"}, lambda p: p.runs[0].font.name == "Arial"),
    ({"size_pt": 14}, lambda p: p.runs[0].font.size.pt == 14),
])
def test_a_block_style_override_reaches_the_document(override, check, tmp_path):
    """"Double-space it", "use Arial", "centre that" must be expressible."""
    spec = PaperSpec.model_validate({
        "meta": {"title": "T", "style": "assignment"},
        "blocks": [{"type": "paragraph", "text": "Styled text.", "style": override}],
    })
    out = render_paper(spec, tmp_path / "d.docx")
    para = next(p for p in Document(str(out)).paragraphs if p.text == "Styled text.")
    assert check(para)
