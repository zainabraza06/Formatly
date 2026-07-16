"""A StyleSheet fully describes how a document style looks AND behaves.

It is plain serialisable data — fonts/sizes per element plus structural conventions
(heading numbering, caption position and wording, table rules, column count). The
renderer knows nothing about IEEE or APA; it just executes a StyleSheet.

Because it is a pydantic model it round-trips to JSON, which means a stylesheet can
be stored in the database, sent over the API, and **authored by a user** — not just
declared in a Python module.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.paper.schema import PageSetup, Style

HeadingScheme = Literal["roman_alpha", "decimal", "none"]
NumberStyle = Literal["roman", "arabic"]
CaptionPos = Literal["above", "below"]
BorderStyle = Literal["horizontal", "grid", "none"]


class StyleSheet(BaseModel):
    id: str
    name: str
    page: PageSetup = Field(default_factory=PageSetup)

    # element styles
    title: Style = Field(default_factory=Style)
    author: Style = Field(default_factory=Style)
    affiliation: Style = Field(default_factory=Style)
    abstract: Style = Field(default_factory=Style)
    keywords: Style = Field(default_factory=Style)
    body: Style = Field(default_factory=Style)
    heading1: Style = Field(default_factory=Style)
    heading2: Style = Field(default_factory=Style)
    heading3: Style = Field(default_factory=Style)
    list_item: Style = Field(default_factory=Style)
    equation: Style = Field(default_factory=Style)
    table_caption: Style = Field(default_factory=Style)
    table_header: Style = Field(default_factory=Style)
    table_cell: Style = Field(default_factory=Style)
    figure_caption: Style = Field(default_factory=Style)
    figure_body: Style = Field(default_factory=Style)
    code: Style = Field(default_factory=Style)
    reference: Style = Field(default_factory=Style)
    references_heading: Style = Field(default_factory=Style)

    # structural conventions
    heading_scheme: HeadingScheme = "decimal"
    table_number_style: NumberStyle = "arabic"
    table_caption_prefix: str = "Table {num}."
    table_caption_position: CaptionPos = "above"
    figure_caption_prefix: str = "Figure {num}."
    figure_caption_position: CaptionPos = "below"
    table_caption_separator: str = ""
    figure_caption_separator: str = ""
    caption_title_italic: bool = False
    table_borders: BorderStyle = "grid"
    table_header_fill: Optional[str] = None    # hex fill for header cells, e.g. "1F3864"
    references_title: str = "References"
    abstract_lead: str = ""
    abstract_as_heading: bool = False
    keywords_lead: str = "Keywords: "
    number_references: bool = True

    # provenance
    builtin: bool = True
    derived_from: str = ""   # e.g. "reference.docx" when learned from a sample
    # which conventions were actually read from the sample (the rest came from the
    # base style) — lets the UI show what was learned vs. inherited
    detected: list[str] = Field(default_factory=list)

    def heading_style(self, level: int) -> Style:
        return {1: self.heading1, 2: self.heading2, 3: self.heading3}.get(level, self.heading3)
