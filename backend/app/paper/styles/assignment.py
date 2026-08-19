"""Formal assignment / official document style.

The house style for submitted work: coursework, lab reports, technical write-ups,
problem sets. A conference two-column layout is the wrong shape for these — code
listings, worked derivations and wide tables all need the full measure, and a
marker reads them as a document, not as a paper.

So: one column, generous margins, decimal section numbering, and captions that
say "Listing 2." and "Table 3." rather than "TABLE III". Code sits on a shaded
ground so an embedded snippet reads as a snippet.
"""
from __future__ import annotations

from app.paper.schema import PageSetup, Style
from app.paper.styles.base import StyleSheet

F = "Times New Roman"
MONO = "Consolas"

ASSIGNMENT = StyleSheet(
    id="assignment",
    name="Formal Assignment",
    page=PageSetup(width_in=8.5, height_in=11.0, margin_top_in=1.0, margin_bottom_in=1.0,
                   margin_left_in=1.0, margin_right_in=1.0, columns=1, column_spacing_in=0.0),

    title=Style(font=F, size_pt=18, bold=True, alignment="center",
                space_before_pt=0, space_after_pt=6, line_spacing=1.0),
    author=Style(font=F, size_pt=12, alignment="center", space_after_pt=0, line_spacing=1.0),
    affiliation=Style(font=F, size_pt=11, italic=True, alignment="center",
                      space_after_pt=4, line_spacing=1.0),
    abstract=Style(font=F, size_pt=11, alignment="justify", space_after_pt=8,
                   line_spacing=1.15, first_line_indent_in=0.0),
    keywords=Style(font=F, size_pt=11, alignment="left", space_after_pt=12, line_spacing=1.15),

    body=Style(font=F, size_pt=12, alignment="justify", first_line_indent_in=0.0,
               space_after_pt=8, line_spacing=1.15),
    heading1=Style(font=F, size_pt=14, bold=True, alignment="left",
                   space_before_pt=14, space_after_pt=6, line_spacing=1.0, keep_with_next=True),
    heading2=Style(font=F, size_pt=12, bold=True, alignment="left",
                   space_before_pt=10, space_after_pt=4, line_spacing=1.0, keep_with_next=True),
    heading3=Style(font=F, size_pt=12, bold=False, italic=True, alignment="left",
                   space_before_pt=8, space_after_pt=3, line_spacing=1.0, keep_with_next=True),

    list_item=Style(font=F, size_pt=12, alignment="left", left_indent_in=0.35,
                    hanging_indent_in=0.2, space_after_pt=4, line_spacing=1.15),
    equation=Style(font=F, size_pt=12, italic=True, alignment="center",
                   space_before_pt=8, space_after_pt=8, line_spacing=1.0),

    table_caption=Style(font=F, size_pt=10, bold=True, alignment="left",
                        space_before_pt=10, space_after_pt=3, line_spacing=1.0,
                        first_line_indent_in=0.0, keep_with_next=True),
    table_header=Style(font=F, size_pt=10, bold=True, alignment="left", line_spacing=1.0,
                       first_line_indent_in=0.0, space_after_pt=0),
    table_cell=Style(font=F, size_pt=10, alignment="left", line_spacing=1.0,
                     first_line_indent_in=0.0, space_after_pt=0),

    figure_caption=Style(font=F, size_pt=10, alignment="center", space_before_pt=4,
                         space_after_pt=10, line_spacing=1.0, first_line_indent_in=0.0),
    figure_body=Style(alignment="center", space_before_pt=8, space_after_pt=0,
                      first_line_indent_in=0.0),

    # A listing is read line by line, so it is never justified and never indented
    # away from the caption above it; wrapped lines hang so a wrap cannot be
    # mistaken for a new statement.
    code=Style(font=MONO, size_pt=9.5, alignment="left", left_indent_in=0.35,
               hanging_indent_in=0.2, space_before_pt=4, space_after_pt=4, line_spacing=1.0),
    code_caption=Style(font=F, size_pt=10, bold=True, alignment="left", space_before_pt=10,
                       space_after_pt=3, line_spacing=1.0, first_line_indent_in=0.0,
                       keep_with_next=True),

    reference=Style(font=F, size_pt=11, alignment="left", left_indent_in=0.35,
                    hanging_indent_in=0.35, space_after_pt=6, line_spacing=1.15),
    references_heading=Style(font=F, size_pt=14, bold=True, alignment="left",
                             space_before_pt=16, space_after_pt=6, line_spacing=1.0),

    heading_scheme="decimal",           # 1., 1.1, 1.1.1 — what a marker expects
    table_number_style="arabic",
    table_caption_prefix="Table {num}.",
    table_caption_position="above",
    table_caption_separator=" ",
    figure_caption_prefix="Figure {num}.",
    figure_caption_position="below",
    figure_caption_separator=" ",
    code_caption_prefix="Listing {num}.",
    code_caption_position="above",
    code_caption_separator=" ",
    code_background="#F4F5F7",
    table_borders="grid",
    table_header_fill="#EDEFF2",
    references_title="References",
    abstract_lead="",
    abstract_as_heading=True,           # a labelled section, not a run-in lead
    keywords_lead="Keywords: ",
    number_references=True,
)
