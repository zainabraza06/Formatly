"""Style resolver: stamps a complete, explicit style onto every block.

The LLM emits semantic blocks; this fills in the full formatting for the chosen
stylesheet (IEEE, APA, ACM, report, …) so the JSON alone fully describes the
document and the renderer stays a deterministic executor. Any style the model
supplied is kept as an override on top of the base, so deliberate deviations
survive.
"""
from __future__ import annotations

from app.paper.schema import (
    Block, Code, Equation, Figure, Heading, ListBlock, Paragraph, PaperSpec, Table,
)
from app.paper.styles import DEFAULT_STYLE, StyleLike, resolve_style
from app.paper.styles.base import StyleSheet


def resolve(spec: PaperSpec, style: StyleLike = None,
            owner_id: str | None = None) -> PaperSpec:
    """Return a copy of `spec` fully resolved against the requested stylesheet.

    `style` may be a built-in id/alias, a user's custom style id/name, or a
    StyleSheet object outright.
    """
    out = spec.model_copy(deep=True)
    chosen = style if style is not None else (out.meta.style or DEFAULT_STYLE)
    sheet = resolve_style(chosen, owner_id)

    out.meta.style = sheet.id
    out.meta.page = sheet.page.model_copy()
    out.blocks = [_resolve_block(b, sheet) for b in out.blocks]
    out.resolved = True
    return out


def _resolve_block(block: Block, sheet: StyleSheet) -> Block:
    b = block.model_copy(deep=True)

    if isinstance(b, Heading):
        b.style = sheet.heading_style(max(1, min(3, b.level))).merged(b.style)
    elif isinstance(b, Paragraph):
        b.style = sheet.body.merged(b.style)
    elif isinstance(b, ListBlock):
        b.style = sheet.list_item.merged(b.style)
    elif isinstance(b, Equation):
        b.style = sheet.equation.merged(b.style)
    elif isinstance(b, Code):
        b.style = sheet.code.merged(b.style)
    elif isinstance(b, Table):
        b.style = sheet.table_cell.merged(b.style)
        b.caption_style = sheet.table_caption.merged(b.caption_style)
        b.header_style = sheet.table_header.merged(b.header_style)
        b.cell_style = sheet.table_cell.merged(b.cell_style)
    elif isinstance(b, Figure):
        b.style = sheet.figure_body.merged(b.style)
        b.caption_style = sheet.figure_caption.merged(b.caption_style)

    return b


# ── numbering helpers ───────────────────────────────────────────────────────

_ROMAN = [
    (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"),
    (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"),
]


def roman(n: int) -> str:
    if n <= 0:
        return ""
    out, rest = "", n
    for value, sym in _ROMAN:
        while rest >= value:
            out += sym
            rest -= value
    return out


def alpha(n: int) -> str:
    """1 -> A, 2 -> B, … (IEEE level-2 headings)."""
    out = ""
    while n > 0:
        n, rem = divmod(n - 1, 26)
        out = chr(65 + rem) + out
    return out


def heading_label(sheet: StyleSheet, level: int, counters: dict[str, int]) -> str:
    """Compute the numbering prefix for a heading under the sheet's scheme."""
    if sheet.heading_scheme == "none":
        return ""
    if sheet.heading_scheme == "roman_alpha":
        if level == 1:
            return f"{roman(counters['h1'])}. "
        if level == 2:
            return f"{alpha(counters['h2'])}. "
        return f"{counters['h3']}) "
    # decimal: 1.  /  1.1  /  1.1.1
    if level == 1:
        return f"{counters['h1']}. "
    if level == 2:
        return f"{counters['h1']}.{counters['h2']} "
    return f"{counters['h1']}.{counters['h2']}.{counters['h3']} "


def number_for(sheet: StyleSheet, n: int, kind: str) -> str:
    if kind == "table" and sheet.table_number_style == "roman":
        return roman(n)
    return str(n)
