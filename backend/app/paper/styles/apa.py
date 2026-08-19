"""APA 7th edition: single column, Times New Roman 12pt, double-spaced,
unnumbered headings, "Table 1" above tables, "Figure 1" above figures,
hanging-indent (unnumbered) reference list."""
from __future__ import annotations

from app.paper.schema import PageSetup, Style
from app.paper.styles.base import StyleSheet

F = "Times New Roman"
LS = 2.0  # APA is double-spaced throughout

APA = StyleSheet(
    id="apa",
    name="APA 7th Edition",
    page=PageSetup(width_in=8.5, height_in=11.0, margin_top_in=1.0, margin_bottom_in=1.0,
                   margin_left_in=1.0, margin_right_in=1.0, columns=1, column_spacing_in=0.0),

    title=Style(font=F, size_pt=12, bold=True, alignment="center", space_after_pt=12, line_spacing=LS),
    author=Style(font=F, size_pt=12, alignment="center", space_after_pt=0, line_spacing=LS),
    affiliation=Style(font=F, size_pt=12, alignment="center", space_after_pt=12, line_spacing=LS),
    abstract=Style(font=F, size_pt=12, alignment="left", first_line_indent_in=0.0,
                   space_after_pt=0, line_spacing=LS),
    keywords=Style(font=F, size_pt=12, italic=False, alignment="left", first_line_indent_in=0.5,
                   space_after_pt=12, line_spacing=LS),
    body=Style(font=F, size_pt=12, alignment="left", first_line_indent_in=0.5,
               space_after_pt=0, line_spacing=LS),
    heading1=Style(font=F, size_pt=12, bold=True, alignment="center",
                   space_before_pt=12, space_after_pt=0, line_spacing=LS, keep_with_next=True),
    heading2=Style(font=F, size_pt=12, bold=True, alignment="left",
                   space_before_pt=12, space_after_pt=0, line_spacing=LS, keep_with_next=True),
    heading3=Style(font=F, size_pt=12, bold=True, italic=True, alignment="left",
                   space_before_pt=12, space_after_pt=0, line_spacing=LS, keep_with_next=True),
    list_item=Style(font=F, size_pt=12, alignment="left", left_indent_in=0.5,
                    hanging_indent_in=0.25, space_after_pt=0, line_spacing=LS),
    equation=Style(font=F, size_pt=12, alignment="center", space_before_pt=12,
                   space_after_pt=12, line_spacing=LS),
    table_caption=Style(font=F, size_pt=12, bold=True, alignment="left",
                        space_before_pt=12, space_after_pt=0, line_spacing=LS, keep_with_next=True),
    table_header=Style(font=F, size_pt=12, bold=True, alignment="center", line_spacing=1.0,
                       first_line_indent_in=0.0, space_after_pt=0),
    table_cell=Style(font=F, size_pt=12, alignment="center", line_spacing=1.0,
                     first_line_indent_in=0.0, space_after_pt=0),
    figure_caption=Style(font=F, size_pt=12, bold=True, alignment="left", space_before_pt=12,
                         space_after_pt=0, line_spacing=LS),
    figure_body=Style(alignment="center", space_before_pt=6, space_after_pt=12,
                      first_line_indent_in=0.0),
    code_caption=Style(font=F, size_pt=10, alignment="left", space_before_pt=8, space_after_pt=2,
                       line_spacing=1.0, first_line_indent_in=0.0, keep_with_next=True),
    code=Style(font="Courier New", size_pt=10, alignment="left", left_indent_in=0.5,
               space_before_pt=6, space_after_pt=6, line_spacing=1.0, first_line_indent_in=0.0),
    reference=Style(font=F, size_pt=12, alignment="left", left_indent_in=0.5,
                    hanging_indent_in=0.5, space_after_pt=0, line_spacing=LS),
    references_heading=Style(font=F, size_pt=12, bold=True, alignment="center",
                             space_before_pt=12, space_after_pt=0, line_spacing=LS),

    heading_scheme="none",
    table_number_style="arabic",
    table_caption_prefix="Table {num}",
    table_caption_position="above",
    figure_caption_prefix="Figure {num}",
    figure_caption_position="above",
    table_caption_separator="\n",    # APA: "Table 1" then the italic title line
    figure_caption_separator="\n",   # APA: "Figure 1" then the italic title line
    caption_title_italic=True,
    table_borders="horizontal",
    references_title="References",
    abstract_lead="",
    abstract_as_heading=True,
    keywords_lead="Keywords: ",
    number_references=False,
)
