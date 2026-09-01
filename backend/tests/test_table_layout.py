"""A table's layout, as against what it says.

The parser read a table's rows, its columns and its edges, and nothing else, so
an imported table was drawn as evenly spaced columns on white whatever the
document did — a narrow first column, a shaded header row and a centred table
all came back as a plain full-width grid.
"""
from __future__ import annotations

import io

import pytest
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches

from app.docos.export import graph_to_docx_bytes
from app.docos.graph import DocumentGraph, NodeType
from app.docos.parser import parse_docx_bytes


def built(*, widths=(2.5, 1.0, 1.0), shade_header=True, centred=True,
          merge_last_row=False) -> bytes:
    doc = Document()
    table = doc.add_table(rows=3, cols=3)
    table.style = "Table Grid"
    if centred:
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for column, inches in enumerate(widths):
        table.columns[column].width = Inches(inches)
        for row in table.rows:
            row.cells[column].width = Inches(inches)
    for r, row in enumerate(table.rows):
        for c, cell in enumerate(row.cells):
            cell.text = f"r{r}c{c}"
    if shade_header:
        for cell in table.rows[0].cells:
            shd = OxmlElement("w:shd")
            shd.set(qn("w:fill"), "D9D9D9")
            cell._tc.get_or_add_tcPr().append(shd)
    if merge_last_row:
        table.rows[2].cells[0].merge(table.rows[2].cells[1])

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def table_of(graph: DocumentGraph):
    return next(n for n in graph.nodes() if n.type is NodeType.TABLE)


def cells_of(graph: DocumentGraph):
    return [n for n in graph.nodes() if n.type is NodeType.TABLE_CELL]


# ── read from the document ───────────────────────────────────────────────────

def test_column_widths_are_read():
    assert table_of(parse_docx_bytes(built(), title="t")).metadata["columns_in"] == [2.5, 1.0, 1.0]


def test_where_the_table_sits_is_read():
    assert table_of(parse_docx_bytes(built(), title="t")).metadata["align"] == "center"


def test_a_shaded_header_row_is_read():
    shaded = [c for c in cells_of(parse_docx_bytes(built(), title="t"))
              if c.metadata.get("shade")]
    assert [c.metadata["shade"] for c in shaded] == ["#d9d9d9"] * 3


def test_an_unshaded_table_says_nothing_about_shading():
    graph = parse_docx_bytes(built(shade_header=False), title="t")
    assert all(not c.metadata.get("shade") for c in cells_of(graph))


def test_a_merged_cell_is_one_cell_not_two():
    """python-docx hands the same cell back once per column it covers, so the
    row used to come out a column too wide with its text repeated."""
    graph = parse_docx_bytes(built(merge_last_row=True), title="t")
    rows = [n for n in graph.nodes() if n.type is NodeType.TABLE_ROW]
    assert [len(r.children) for r in rows] == [3, 3, 2]
    merged = rows[2].children[0]
    assert merged.metadata["span"] == 2


def test_a_table_that_states_no_edges_reports_its_styles():
    """Most tables say only "Table Grid"; reading the table's own XML found
    nothing, so the page fell back to drawing every edge whatever the style."""
    borders = table_of(parse_docx_bytes(built(), title="t")).metadata["borders"]
    assert borders == {"top": 0.5, "bottom": 0.5, "left": 0.5,
                       "right": 0.5, "inside_h": 0.5, "inside_v": 0.5}


def test_the_room_inside_a_cell_is_read():
    """Word leaves 0.075in at the sides and none above; the editor was drawing
    its own padding, which over ten rows is a table of a different height."""
    pad = table_of(parse_docx_bytes(built(), title="t")).metadata["cell_pad_in"]
    assert pad == {"top": 0.0, "left": 0.075, "bottom": 0.0, "right": 0.075}


# ── and written back to one ──────────────────────────────────────────────────

@pytest.mark.parametrize("key, expected", [
    ("columns_in", [2.5, 1.0, 1.0]),
    ("align", "center"),
])
def test_the_layout_survives_a_round_trip(key, expected):
    once = parse_docx_bytes(built(), title="t")
    twice = parse_docx_bytes(graph_to_docx_bytes(once), title="t")
    assert twice_value(twice, key) == expected


def twice_value(graph: DocumentGraph, key: str):
    return table_of(graph).metadata.get(key)


def test_shading_survives_a_round_trip():
    once = parse_docx_bytes(built(), title="t")
    twice = parse_docx_bytes(graph_to_docx_bytes(once), title="t")
    assert [c.metadata.get("shade") for c in cells_of(twice)][:3] == ["#d9d9d9"] * 3
