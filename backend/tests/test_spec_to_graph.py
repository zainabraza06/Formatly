"""Carrying a composed document into the editor without going through a .docx.

Rendering to a file first flattens everything the format has no word for: a
listing becomes loose paragraphs, an equation becomes whatever characters it
typeset to, a chart becomes an anonymous picture. These pin what the direct
route keeps.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.docos.graph import NodeType  # noqa: E402
from app.paper.schema import PaperSpec  # noqa: E402
from app.paper.to_graph import spec_to_graph  # noqa: E402

FRACTION = "d = " + chr(92) + "frac{a - b}{" + chr(92) + "sqrt{c}}"


def _graph(blocks, meta=None, references=None):
    spec = PaperSpec.model_validate({
        "meta": {"title": "T", "style": "assignment", **(meta or {})},
        "blocks": blocks,
        "references": references or [],
    })
    return spec_to_graph(spec, title="T")


def _nodes(graph, node_type):
    return [n for n in graph.root.walk() if n.type == node_type]


def _kinds(graph) -> list[str]:
    return [n.metadata.get("kind") for n in graph.root.walk() if n.metadata.get("kind")]


# ── the things a .docx round trip loses ─────────────────────────────────────

def test_a_code_screenshot_stays_a_picture():
    g = _graph([{"type": "code", "language": "cpp", "text": "int main(){}",
                 "render": "image", "filename": "g.cpp", "caption": "the program"}])
    images = _nodes(g, NodeType.IMAGE)
    assert len(images) == 1
    assert images[0].metadata["src"].startswith("data:image/")
    assert "code_screenshot" in _kinds(g)


def test_a_listing_keeps_its_source_so_an_export_can_rebuild_it():
    g = _graph([{"type": "code", "language": "cpp", "text": "int main(){}",
                 "render": "image", "filename": "g.cpp"}])
    figure = next(n for n in g.root.walk() if n.metadata.get("kind") == "code_screenshot")
    assert figure.metadata["code"] == "int main(){}"
    assert figure.metadata["language"] == "cpp"


def test_a_text_listing_stays_addressable_line_by_line():
    g = _graph([{"type": "code", "language": "py", "text": "a = 1\nb = 2\nc = 3"}])
    lines = [n for n in g.root.walk() if n.metadata.get("code_line")]
    assert [n.content for n in lines] == ["a = 1", "b = 2", "c = 3"]


def test_an_equation_keeps_its_markup_beside_the_picture():
    """A bitmap alone cannot be re-typeset; the markup is what makes it editable."""
    g = _graph([{"type": "equation", "text": FRACTION}])
    figure = next(n for n in g.root.walk() if n.metadata.get("kind") == "equation")
    assert figure.metadata["equation"] == FRACTION
    assert _nodes(g, NodeType.IMAGE)[0].metadata["src"].startswith("data:image/")


def test_a_plain_equation_stays_text():
    g = _graph([{"type": "equation", "text": "y = mx + c"}])
    assert not _nodes(g, NodeType.IMAGE)
    assert any(n.content == "y = mx + c" for n in g.root.walk())


def test_a_chart_arrives_drawn_and_captioned():
    g = _graph([{"type": "figure", "caption": "Values",
                 "chart": {"kind": "bar", "labels": ["A", "B"], "values": [3.0, 5.0]}}])
    assert _nodes(g, NodeType.IMAGE)[0].metadata["src"].startswith("data:image/")
    assert any("Values" in n.content for n in _nodes(g, NodeType.CAPTION))


def test_a_table_keeps_its_shape():
    g = _graph([{"type": "table", "caption": "Results", "columns": ["Case", "Result"],
                 "rows": [["1", "pass"], ["2", "fail"]]}])
    table = _nodes(g, NodeType.TABLE)[0]
    rows = [n for n in table.children if n.type == NodeType.TABLE_ROW]
    assert len(rows) == 3, "a header row plus two data rows"
    assert [c.content for c in rows[0].children] == ["Case", "Result"]
    assert [c.content for c in rows[2].children] == ["2", "fail"]


# ── structure and front matter ──────────────────────────────────────────────

def test_headings_keep_their_level():
    g = _graph([{"type": "heading", "level": 1, "text": "One"},
                {"type": "heading", "level": 2, "text": "Two"}])
    levels = {n.content: n.metadata.get("level") for n in g.root.walk()
              if n.type in (NodeType.HEADING, NodeType.SUBHEADING)}
    assert levels["One"] == 1 and levels["Two"] == 2


def test_a_cover_sheet_becomes_a_page_break():
    g = _graph([{"type": "paragraph", "text": "body"}],
               meta={"title_page": True, "title_page_lines": ["Course: FOCP"]})
    assert _nodes(g, NodeType.PAGE_BREAK)
    assert any("Course: FOCP" in n.content for n in g.root.walk())


def test_list_items_are_addressable_individually():
    g = _graph([{"type": "list", "ordered": True, "items": ["first", "second"]}])
    items = [n for n in g.root.walk() if n.metadata.get("list_item")]
    assert [n.content for n in items] == ["1. first", "2. second"]


def test_references_are_numbered_once():
    g = _graph([{"type": "paragraph", "text": "x"}],
               references=["[1] B. Stroustrup, Programming, 2014."])
    ref = _nodes(g, NodeType.REFERENCE)[0]
    assert ref.content == "[1] B. Stroustrup, Programming, 2014."


def test_a_figure_with_no_data_is_dropped_here_too():
    """The same rule the document renderer follows: no blank figures."""
    g = _graph([{"type": "figure", "caption": "Nothing",
                 "chart": {"kind": "bar", "labels": ["A"], "values": []}}])
    assert not _nodes(g, NodeType.FIGURE)


@pytest.mark.parametrize("style", ["ieee", "assignment", "ieee_1col"])
def test_every_built_in_style_converts(style):
    g = _graph([{"type": "heading", "level": 1, "text": "H"},
                {"type": "paragraph", "text": "p"}], meta={"style": style})
    assert g.root.children
