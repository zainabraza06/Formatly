"""How a table is laid out, as against what it says.

The parser read a table's rows, its columns and (lately) its edges, and nothing
else — so an imported table was drawn as evenly spaced columns on a white
ground whatever the document did. A table whose first column is narrow and
whose header row is shaded came back looking like a different table.

None of this is inferred. Every value here is one Word stated, converted to the
units the rest of the model uses: inches for widths, points for rules, hex for
colour.
"""
from __future__ import annotations

from typing import Any, Optional

from docx.oxml.ns import qn

# Word measures in twentieths of a point. 1440 of them to the inch.
_TWIPS_PER_INCH = 1440.0

# `w:jc` on a table says where it sits between the margins.
_ALIGNMENTS = {"left": "left", "start": "left", "center": "center",
               "centre": "center", "right": "right", "end": "right"}


def _edges(borders: Any) -> dict[str, float]:
    """A `w:tblBorders` element read into widths in points, 0 for an edge that
    is not drawn. Word measures the width in eighths of a point."""
    if borders is None:
        return {}

    out: dict[str, float] = {}
    for side, tag in _BORDER_TAGS.items():
        edge = borders.find(qn(tag))
        if edge is None:
            continue
        if (edge.get(qn("w:val")) or "").lower() in ("none", "nil"):
            out[side] = 0.0
            continue
        try:
            out[side] = round(int(edge.get(qn("w:sz")) or 4) / 8, 2)
        except ValueError:
            out[side] = 0.5
    return out


_BORDER_TAGS = {"top": "w:top", "bottom": "w:bottom", "left": "w:left",
                "right": "w:right", "inside_h": "w:insideH",
                "inside_v": "w:insideV"}


def table_layout(table: Any) -> dict[str, Any]:
    """Column widths, overall width and placement, as the document has them."""
    out: dict[str, Any] = {}
    grid = table._tbl.find(qn("w:tblGrid"))
    if grid is not None:
        widths = []
        for col in grid.findall(qn("w:gridCol")):
            try:
                widths.append(round(int(col.get(qn("w:w")) or 0) / _TWIPS_PER_INCH, 3))
            except ValueError:
                widths.append(0.0)
        if any(widths):
            out["columns_in"] = widths

    properties = table._tbl.find(qn("w:tblPr"))
    if properties is None:
        return out

    width = properties.find(qn("w:tblW"))
    if width is not None:
        kind = (width.get(qn("w:type")) or "").lower()
        value = width.get(qn("w:w")) or "0"
        try:
            number = int(value)
        except ValueError:
            number = 0
        if kind == "pct" and number:
            # Word writes a percentage in fiftieths of a per cent.
            out["width_pct"] = round(number / 50.0, 1)
        elif kind == "dxa" and number:
            out["width_in"] = round(number / _TWIPS_PER_INCH, 3)

    # What the table states, and failing that what its style states.
    pad = _margins(properties.find(qn("w:tblCellMar"))) or style_cell_padding(table)
    if pad:
        out["cell_pad_in"] = pad

    placement = properties.find(qn("w:jc"))
    if placement is not None:
        wanted = _ALIGNMENTS.get((placement.get(qn("w:val")) or "").lower())
        if wanted:
            out["align"] = wanted
    return out


def style_cell_padding(table: Any) -> dict[str, float]:
    """The room a table's style leaves inside each cell.

    Word states this once for the table, usually in the style rather than on
    the table, and the editor was drawing its own padding instead — enough
    difference over ten rows to make an imported table a different height.
    """
    try:
        element = table.style.element
    except Exception:
        return {}
    if element is None:
        return {}
    properties = element.find(qn("w:tblPr"))
    margins = properties.find(qn("w:tblCellMar")) if properties is not None else None
    return _margins(margins)


def _margins(margins: Any) -> dict[str, float]:
    if margins is None:
        return {}
    out: dict[str, float] = {}
    for side in ("top", "left", "bottom", "right"):
        edge = margins.find(qn(f"w:{side}"))
        if edge is None:
            continue
        try:
            out[side] = round(int(edge.get(qn("w:w")) or 0) / _TWIPS_PER_INCH, 3)
        except ValueError:
            continue
    return out


def style_borders(table: Any) -> dict[str, float]:
    """The edges a table's style gives it, when the table states none itself.

    Most tables say `Table Grid` and leave it at that, so reading only the
    table's own XML reported nothing and the page fell back to drawing every
    edge — which happens to look right for Table Grid and wrong for every
    style that does not draw them all.
    """
    try:
        element = table.style.element
    except Exception:                       # a table with no style at all
        return {}
    if element is None:
        return {}

    properties = element.find(qn("w:tblPr"))
    borders = properties.find(qn("w:tblBorders")) if properties is not None else None
    return _edges(borders)


def cell_layout(cell: Any) -> dict[str, Any]:
    """One cell's shading, width, vertical placement and merging."""
    out: dict[str, Any] = {}
    properties = cell._tc.find(qn("w:tcPr"))
    if properties is None:
        return out

    shade = properties.find(qn("w:shd"))
    if shade is not None:
        fill = (shade.get(qn("w:fill")) or "").strip()
        if fill and fill.lower() not in ("auto", "ffffff"):
            out["shade"] = f"#{fill.lower()}"

    valign = properties.find(qn("w:vAlign"))
    if valign is not None:
        value = (valign.get(qn("w:val")) or "").lower()
        out["valign"] = {"center": "middle", "bottom": "bottom"}.get(value, "top")

    span = properties.find(qn("w:gridSpan"))
    if span is not None:
        try:
            columns = int(span.get(qn("w:val")) or 1)
        except ValueError:
            columns = 1
        if columns > 1:
            out["span"] = columns

    merge = properties.find(qn("w:vMerge"))
    if merge is not None:
        # A cell that continues the one above it holds no text of its own; the
        # row still has it, so it is marked rather than dropped.
        out["vmerge"] = "start" if (merge.get(qn("w:val")) or "").lower() == "restart" \
            else "continue"

    width = properties.find(qn("w:tcW"))
    if width is not None and (width.get(qn("w:type")) or "").lower() == "dxa":
        try:
            out["width_in"] = round(int(width.get(qn("w:w")) or 0) / _TWIPS_PER_INCH, 3)
        except ValueError:
            pass
    return out


def row_layout(row: Any) -> dict[str, Any]:
    """A row's height, when it states one."""
    out: dict[str, Any] = {}
    properties = row._tr.find(qn("w:trPr"))
    if properties is None:
        return out
    height = properties.find(qn("w:trHeight"))
    if height is not None:
        try:
            out["height_in"] = round(int(height.get(qn("w:val")) or 0) / _TWIPS_PER_INCH, 3)
        except ValueError:
            pass
    return out


def shade_of(node: Any) -> Optional[str]:
    return (node.metadata or {}).get("shade")
