"""The file we write has to be one Word will open.

Word validates the ORDER of the elements inside a property container, not just
their presence. `w:tblBorders` appended after `w:tblLayout` is well-formed XML
and an invalid document, and Word says only that it "found a problem with the
contents" — it does not say where. Nothing in this project noticed: the file
round-tripped through our own parser, and LibreOffice opened it.

So the order is asserted here, against the sequence the schema states.
"""
from __future__ import annotations

import io
import re
import zipfile

import pytest

from app.docos.export import graph_to_docx_bytes
from app.docos.graph import DocumentGraph, Node, NodeType, Style

# The order each container's children must appear in, from the ECMA-376
# schema. Only the elements this project writes need to be listed, but the
# neighbours are kept so a new one can be placed among them.
ORDERS = {
    "w:tblPr": ["w:tblStyle", "w:tblpPr", "w:tblOverlap", "w:bidiVisual",
                "w:tblStyleRowBandSize", "w:tblStyleColBandSize", "w:tblW",
                "w:jc", "w:tblCellSpacing", "w:tblInd", "w:tblBorders", "w:shd",
                "w:tblLayout", "w:tblCellMar", "w:tblLook"],
    "w:tcPr": ["w:cnfStyle", "w:tcW", "w:gridSpan", "w:hMerge", "w:vMerge",
               "w:tcBorders", "w:shd", "w:noWrap", "w:tcMar", "w:textDirection",
               "w:tcFitText", "w:vAlign", "w:hideMark"],
    "w:pPr": ["w:pStyle", "w:keepNext", "w:keepLines", "w:pageBreakBefore",
              "w:framePr", "w:widowControl", "w:numPr", "w:suppressLineNumbers",
              "w:pBdr", "w:shd", "w:tabs", "w:spacing", "w:ind",
              "w:contextualSpacing", "w:jc", "w:textDirection",
              "w:textAlignment", "w:outlineLvl", "w:rPr", "w:sectPr"],
}


def everything() -> DocumentGraph:
    """A document using every part of the exporter at once."""
    cells = [[Node(type=NodeType.TABLE_CELL, content=c,
                   metadata={"shade": "#d9d9d9", "valign": "middle"} if r == 0 else {})
              for c in row]
             for r, row in enumerate((("Component", "Configuration"),
                                      ("LSTM", "h = 16")))]
    table = Node(type=NodeType.TABLE, children=[
        Node(type=NodeType.TABLE_ROW, children=cells[0], metadata={"header_row": True}),
        Node(type=NodeType.TABLE_ROW, children=cells[1])],
        metadata={"columns_in": [2.5, 3.0], "align": "center",
                  "cell_pad_in": {"top": 0.0, "left": 0.075,
                                  "bottom": 0.0, "right": 0.075},
                  "borders": {"top": 1.5, "bottom": 1.5, "header": 1.0,
                              "left": 0.0, "right": 0.0,
                              "inside_h": 0.0, "inside_v": 0.0}})

    root = Node(type=NodeType.DOCUMENT,
                metadata={"page": {"render_maths": True}, "render_maths": True})
    root.children = [
        Node(type=NodeType.HEADING, content="I. Introduction",
             style=Style(bold=True, font_size=12, alignment="center")),
        Node(type=NodeType.BODY, content=r"Unit cost is $C = \frac{F + vQ}{Q}$ here.",
             metadata={"line_spacing": 2.0, "space_after_pt": 6.0,
                       "indent_first_line_pt": 18.0}),
        Node(type=NodeType.BODY, content="A bulleted point.",
             metadata={"list": {"kind": "bullet", "level": 0}}),
        Node(type=NodeType.HORIZONTAL_RULE),
        table,
        Node(type=NodeType.CAPTION, content="Table 1. Everything at once."),
        Node(type=NodeType.REFERENCE, content="[1] A reference, 2025."),
    ]
    return DocumentGraph(root=root, title="everything")


def document_xml(graph: DocumentGraph) -> str:
    with zipfile.ZipFile(io.BytesIO(graph_to_docx_bytes(graph))) as archive:
        return archive.read("word/document.xml").decode("utf-8")


@pytest.mark.parametrize("container", sorted(ORDERS))
def test_property_children_are_in_the_order_the_schema_states(container: str):
    xml = document_xml(everything())
    order = ORDERS[container]

    for match in re.finditer(rf"<{container}>(.*?)</{container}>", xml, re.DOTALL):
        children = [c for c in re.findall(r"<(w:[a-zA-Z]+)[ />]", match.group(1))
                    if c in order]
        ranks = [order.index(c) for c in children]
        assert ranks == sorted(ranks), (
            f"{container} children are out of order — Word will refuse the "
            f"file and say only that it found a problem: {children}")


def test_the_file_is_a_zip_word_could_open():
    with zipfile.ZipFile(io.BytesIO(graph_to_docx_bytes(everything()))) as archive:
        assert archive.testzip() is None
        assert "word/document.xml" in archive.namelist()
        assert "[Content_Types].xml" in archive.namelist()
