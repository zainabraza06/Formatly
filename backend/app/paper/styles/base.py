"""A StyleSheet fully describes how a document style looks AND behaves.

Everything the renderer needs is data here — fonts/sizes per element plus the
structural conventions (heading numbering, caption position and wording, table
rules, column count). Adding a new style (Chicago, Harvard, a company template)
means adding one module, not touching the renderer.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.paper.schema import PageSetup, Style

HeadingScheme = Literal["roman_alpha", "decimal", "none"]
NumberStyle = Literal["roman", "arabic"]
CaptionPos = Literal["above", "below"]
BorderStyle = Literal["horizontal", "grid", "none"]


@dataclass(frozen=True)
class StyleSheet:
    id: str
    name: str
    page: PageSetup

    # element styles
    title: Style
    author: Style
    affiliation: Style
    abstract: Style
    keywords: Style
    body: Style
    heading1: Style
    heading2: Style
    heading3: Style
    list_item: Style
    equation: Style
    table_caption: Style
    table_header: Style
    table_cell: Style
    figure_caption: Style
    figure_body: Style
    code: Style
    reference: Style
    references_heading: Style

    # structural conventions
    heading_scheme: HeadingScheme = "decimal"
    table_number_style: NumberStyle = "arabic"
    table_caption_prefix: str = "Table {num}."      # {num} substituted
    table_caption_position: CaptionPos = "above"
    figure_caption_prefix: str = "Figure {num}."
    figure_caption_position: CaptionPos = "below"
    # what separates the "Table 1"/"Fig. 1." label from the caption text ("" | "\n").
    # Tables often put the title on its own line; figure captions usually run inline.
    table_caption_separator: str = ""
    figure_caption_separator: str = ""
    caption_title_italic: bool = False   # APA italicises the caption title line
    table_borders: BorderStyle = "grid"
    references_title: str = "References"
    abstract_lead: str = ""            # inline lead-in, e.g. "Abstract—"
    abstract_as_heading: bool = False  # render "Abstract" as its own heading
    keywords_lead: str = "Keywords: "
    number_references: bool = True     # "[1] ..." vs plain hanging entries

    def heading_style(self, level: int) -> Style:
        return {1: self.heading1, 2: self.heading2, 3: self.heading3}.get(level, self.heading3)
