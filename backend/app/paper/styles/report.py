"""General technical / business report: single column, Calibri, decimal-numbered
headings, gridded tables, captions below figures. The sensible default when the
user just asks for "a report" rather than a specific academic style."""
from __future__ import annotations

from app.paper.schema import PageSetup, Style
from app.paper.styles.base import StyleSheet

F = "Calibri"
HEAD_COLOR = "#1F3864"

REPORT = StyleSheet(
    id="report",
    name="Technical Report",
    page=PageSetup(width_in=8.5, height_in=11.0, margin_top_in=1.0, margin_bottom_in=1.0,
                   margin_left_in=1.0, margin_right_in=1.0, columns=1, column_spacing_in=0.0),

    title=Style(font=F, size_pt=26, bold=True, alignment="center", color="#1F3864",
                space_after_pt=10, line_spacing=1.0),
    author=Style(font=F, size_pt=12, alignment="center", space_after_pt=0, line_spacing=1.15),
    affiliation=Style(font=F, size_pt=10, italic=True, alignment="center",
                      space_after_pt=10, line_spacing=1.15),
    abstract=Style(font=F, size_pt=11, italic=True, alignment="justify",
                   space_after_pt=8, line_spacing=1.15),
    keywords=Style(font=F, size_pt=10, italic=True, alignment="justify",
                   space_after_pt=12, line_spacing=1.15),
    body=Style(font=F, size_pt=11, alignment="justify", first_line_indent_in=0.0,
               space_after_pt=8, line_spacing=1.15),
    heading1=Style(font=F, size_pt=16, bold=True, alignment="left", color=HEAD_COLOR,
                   space_before_pt=14, space_after_pt=6, line_spacing=1.15, keep_with_next=True),
    heading2=Style(font=F, size_pt=13, bold=True, alignment="left", color=HEAD_COLOR,
                   space_before_pt=10, space_after_pt=4, line_spacing=1.15, keep_with_next=True),
    heading3=Style(font=F, size_pt=11, bold=True, italic=True, alignment="left",
                   space_before_pt=8, space_after_pt=3, line_spacing=1.15, keep_with_next=True),
    list_item=Style(font=F, size_pt=11, alignment="left", left_indent_in=0.3,
                    hanging_indent_in=0.2, space_after_pt=3, line_spacing=1.15),
    equation=Style(font=F, size_pt=11, alignment="center", space_before_pt=8,
                   space_after_pt=8, line_spacing=1.15),
    table_caption=Style(font=F, size_pt=10, bold=True, alignment="left",
                        space_before_pt=10, space_after_pt=3, line_spacing=1.15, keep_with_next=True),
    table_header=Style(font=F, size_pt=10, bold=True, alignment="center", color="#FFFFFF",
                       line_spacing=1.0, first_line_indent_in=0.0, space_after_pt=0),
    table_cell=Style(font=F, size_pt=10, alignment="left", line_spacing=1.0,
                     first_line_indent_in=0.0, space_after_pt=0),
    figure_caption=Style(font=F, size_pt=10, italic=True, alignment="center",
                         space_before_pt=4, space_after_pt=10, line_spacing=1.15),
    figure_body=Style(alignment="center", space_before_pt=8, space_after_pt=0,
                      first_line_indent_in=0.0),
    code=Style(font="Consolas", size_pt=9, alignment="left", left_indent_in=0.2,
               space_before_pt=6, space_after_pt=6, line_spacing=1.0, first_line_indent_in=0.0),
    reference=Style(font=F, size_pt=10, alignment="left", left_indent_in=0.3,
                    hanging_indent_in=0.3, space_after_pt=4, line_spacing=1.15),
    references_heading=Style(font=F, size_pt=16, bold=True, alignment="left", color=HEAD_COLOR,
                             space_before_pt=14, space_after_pt=6, line_spacing=1.15),

    heading_scheme="decimal",
    table_number_style="arabic",
    table_caption_prefix="Table {num}. ",
    table_caption_position="above",
    figure_caption_prefix="Figure {num}. ",
    figure_caption_position="below",
    table_borders="grid",
    table_header_fill="1F3864",
    references_title="References",
    abstract_lead="",
    abstract_as_heading=True,
    keywords_lead="Keywords: ",
    number_references=True,
)
