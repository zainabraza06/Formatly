"""ACM (sigconf-like): two columns, 9pt serif, decimal-numbered sections,
"Table 1:" above tables, "Figure 1:" below figures, numbered references."""
from __future__ import annotations

from app.paper.schema import PageSetup, Style
from app.paper.styles.base import StyleSheet

F = "Times New Roman"  # stands in for Linux Libertine, which Word rarely has

ACM = StyleSheet(
    id="acm",
    name="ACM (sigconf)",
    page=PageSetup(width_in=8.5, height_in=11.0, margin_top_in=0.75, margin_bottom_in=1.0,
                   margin_left_in=0.75, margin_right_in=0.75, columns=2, column_spacing_in=0.33),

    title=Style(font=F, size_pt=18, bold=True, alignment="center", space_after_pt=8, line_spacing=1.0),
    author=Style(font=F, size_pt=10, alignment="center", space_after_pt=0, line_spacing=1.0),
    affiliation=Style(font=F, size_pt=9, italic=True, alignment="center", space_after_pt=6, line_spacing=1.0),
    abstract=Style(font=F, size_pt=9, alignment="justify", space_after_pt=6, line_spacing=1.05),
    keywords=Style(font=F, size_pt=9, alignment="justify", space_after_pt=10, line_spacing=1.05),
    body=Style(font=F, size_pt=9, alignment="justify", first_line_indent_in=0.17,
               space_after_pt=0, line_spacing=1.05),
    heading1=Style(font=F, size_pt=10, bold=True, all_caps=True, alignment="left",
                   space_before_pt=10, space_after_pt=3, line_spacing=1.0, keep_with_next=True),
    heading2=Style(font=F, size_pt=9.5, bold=True, alignment="left",
                   space_before_pt=8, space_after_pt=2, line_spacing=1.0, keep_with_next=True),
    heading3=Style(font=F, size_pt=9, bold=True, italic=True, alignment="left",
                   space_before_pt=6, space_after_pt=2, line_spacing=1.0, keep_with_next=True),
    list_item=Style(font=F, size_pt=9, alignment="justify", left_indent_in=0.22,
                    hanging_indent_in=0.14, space_after_pt=0, line_spacing=1.05),
    equation=Style(font=F, size_pt=9, italic=True, alignment="center",
                   space_before_pt=6, space_after_pt=6, line_spacing=1.0),
    table_caption=Style(font=F, size_pt=8, bold=True, alignment="left",
                        space_before_pt=8, space_after_pt=2, line_spacing=1.0, keep_with_next=True),
    table_header=Style(font=F, size_pt=8, bold=True, alignment="center", line_spacing=1.0,
                       first_line_indent_in=0.0, space_after_pt=0),
    table_cell=Style(font=F, size_pt=8, alignment="center", line_spacing=1.0,
                     first_line_indent_in=0.0, space_after_pt=0),
    figure_caption=Style(font=F, size_pt=8, alignment="left", space_before_pt=4,
                         space_after_pt=8, line_spacing=1.0),
    figure_body=Style(alignment="center", space_before_pt=6, space_after_pt=0,
                      first_line_indent_in=0.0),
    code=Style(font="Courier New", size_pt=8, alignment="left", left_indent_in=0.1,
               space_before_pt=4, space_after_pt=4, line_spacing=1.0, first_line_indent_in=0.0),
    reference=Style(font=F, size_pt=8, alignment="justify", left_indent_in=0.2,
                    hanging_indent_in=0.2, space_after_pt=0, line_spacing=1.05),
    references_heading=Style(font=F, size_pt=10, bold=True, all_caps=True, alignment="left",
                             space_before_pt=10, space_after_pt=3, line_spacing=1.0),

    heading_scheme="decimal",
    table_number_style="arabic",
    table_caption_prefix="Table {num}: ",
    table_caption_position="above",
    figure_caption_prefix="Figure {num}: ",
    figure_caption_position="below",
    table_borders="horizontal",
    references_title="References",
    abstract_lead="",
    abstract_as_heading=True,
    keywords_lead="Keywords: ",
    number_references=True,
)
