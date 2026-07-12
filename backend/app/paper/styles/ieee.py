"""IEEE conference paper: two columns, Times New Roman, Roman-numeral sections,
"TABLE I" above tables, "Fig. n." below figures, numbered references."""
from __future__ import annotations

from app.paper.schema import PageSetup, Style
from app.paper.styles.base import StyleSheet

F = "Times New Roman"

IEEE = StyleSheet(
    id="ieee",
    name="IEEE Conference",
    page=PageSetup(width_in=8.5, height_in=11.0, margin_top_in=0.75, margin_bottom_in=1.0,
                   margin_left_in=0.625, margin_right_in=0.625, columns=2, column_spacing_in=0.25),

    title=Style(font=F, size_pt=24, bold=False, alignment="center", space_after_pt=6, line_spacing=1.0),
    author=Style(font=F, size_pt=11, alignment="center", space_after_pt=0, line_spacing=1.0),
    affiliation=Style(font=F, size_pt=10, italic=True, alignment="center", space_after_pt=6, line_spacing=1.0),
    abstract=Style(font=F, size_pt=9, bold=True, italic=True, alignment="justify",
                   space_after_pt=6, line_spacing=1.0),
    keywords=Style(font=F, size_pt=9, bold=True, italic=True, alignment="justify",
                   space_after_pt=10, line_spacing=1.0),
    body=Style(font=F, size_pt=10, alignment="justify", first_line_indent_in=0.2,
               space_after_pt=0, line_spacing=1.0),
    heading1=Style(font=F, size_pt=10, small_caps=True, bold=False, alignment="center",
                   space_before_pt=12, space_after_pt=4, line_spacing=1.0, keep_with_next=True),
    heading2=Style(font=F, size_pt=10, italic=True, alignment="left",
                   space_before_pt=8, space_after_pt=3, line_spacing=1.0, keep_with_next=True),
    heading3=Style(font=F, size_pt=10, italic=True, alignment="left", left_indent_in=0.2,
                   space_before_pt=6, space_after_pt=2, line_spacing=1.0, keep_with_next=True),
    list_item=Style(font=F, size_pt=10, alignment="justify", left_indent_in=0.25,
                    hanging_indent_in=0.15, space_after_pt=0, line_spacing=1.0),
    equation=Style(font=F, size_pt=10, italic=True, alignment="center",
                   space_before_pt=6, space_after_pt=6, line_spacing=1.0),
    table_caption=Style(font=F, size_pt=8, small_caps=True, alignment="center",
                        space_before_pt=8, space_after_pt=2, line_spacing=1.0, keep_with_next=True),
    table_header=Style(font=F, size_pt=8, bold=True, alignment="center", line_spacing=1.0,
                       first_line_indent_in=0.0, space_after_pt=0),
    table_cell=Style(font=F, size_pt=8, alignment="center", line_spacing=1.0,
                     first_line_indent_in=0.0, space_after_pt=0),
    figure_caption=Style(font=F, size_pt=8, alignment="center", space_before_pt=4,
                         space_after_pt=8, line_spacing=1.0),
    figure_body=Style(alignment="center", space_before_pt=6, space_after_pt=0,
                      first_line_indent_in=0.0),
    code=Style(font="Courier New", size_pt=8, alignment="left", left_indent_in=0.1,
               space_before_pt=4, space_after_pt=4, line_spacing=1.0, first_line_indent_in=0.0),
    reference=Style(font=F, size_pt=8, alignment="justify", left_indent_in=0.2,
                    hanging_indent_in=0.2, space_after_pt=0, line_spacing=1.0),
    references_heading=Style(font=F, size_pt=10, small_caps=True, alignment="center",
                             space_before_pt=12, space_after_pt=4, line_spacing=1.0),

    heading_scheme="roman_alpha",
    table_number_style="roman",
    table_caption_prefix="TABLE {num}",
    table_caption_position="above",
    figure_caption_prefix="Fig. {num}. ",
    figure_caption_position="below",
    table_caption_separator="\n",   # "TABLE I" then the title on the next line
    figure_caption_separator="",    # "Fig. 1. Caption text" runs inline
    table_borders="horizontal",
    references_title="References",
    abstract_lead="Abstract—",
    abstract_as_heading=False,
    keywords_lead="Index Terms—",
    number_references=True,
)
