"""Paper specification — the JSON contract between the LLM and the DOCX renderer.

The LLM emits *semantic* blocks (plus optional style overrides). The style resolver
then fills in complete, explicit formatting for every block (font, size, bold,
italic, small-caps, alignment, indents, table rules), so the final JSON fully
describes the document and the renderer is a dumb, deterministic executor.
"""
from __future__ import annotations

from typing import Annotated, Any, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator


# ── formatting ──────────────────────────────────────────────────────────────

class Style(BaseModel):
    font: Optional[str] = None
    size_pt: Optional[float] = None
    bold: Optional[bool] = None
    italic: Optional[bool] = None
    underline: Optional[bool] = None
    small_caps: Optional[bool] = None
    all_caps: Optional[bool] = None
    color: Optional[str] = None                     # hex, e.g. "#000000"
    alignment: Optional[Literal["left", "center", "right", "justify"]] = None
    first_line_indent_in: Optional[float] = None
    left_indent_in: Optional[float] = None
    hanging_indent_in: Optional[float] = None
    space_before_pt: Optional[float] = None
    space_after_pt: Optional[float] = None
    line_spacing: Optional[float] = None            # 1.0 = single
    keep_with_next: Optional[bool] = None

    def merged(self, override: Optional["Style"]) -> "Style":
        """Overlay non-None fields of `override` on a copy of self."""
        if override is None:
            return self.model_copy()
        data = self.model_dump()
        for k, v in override.model_dump().items():
            if v is not None:
                data[k] = v
        return Style(**data)


# ── charts / visualisations ─────────────────────────────────────────────────

class Series(BaseModel):
    name: str = ""
    values: list[float] = Field(default_factory=list)
    # scatter only: this series' own x coordinates, when it does not share the
    # chart's x axis (e.g. one point cloud per group)
    x_values: list[float] = Field(default_factory=list)


ChartKind = Literal["bar", "line", "pie", "scatter", "grouped_bar"]


def normalize_chart_kind(value: Any) -> Any:
    """Coerce the loose phrasings a model actually emits ("pie chart",
    "line graph", "stacked bar") to the enum. Models rarely return the bare
    token, so validating strictly would throw away otherwise-good documents."""
    if not isinstance(value, str):
        return value
    v = value.strip().lower()
    if v in {"bar", "line", "pie", "scatter", "grouped_bar"}:
        return v
    if "pie" in v or "donut" in v or "doughnut" in v:
        return "pie"
    if "scatter" in v:
        return "scatter"
    if "line" in v or "trend" in v:
        return "line"
    if "group" in v or "cluster" in v or "stack" in v or "multi" in v:
        return "grouped_bar"
    if "bar" in v or "column" in v or "histogram" in v:
        return "bar"
    return "bar"  # last resort — a chart the reader can still read


class ChartSpec(BaseModel):
    """A visualisation the model derived from the supplied data."""
    kind: ChartKind = "bar"
    title: str = ""
    x_label: str = ""
    y_label: str = ""
    labels: list[str] = Field(default_factory=list)      # x categories / pie slices
    values: list[float] = Field(default_factory=list)    # single-series data
    x_values: list[float] = Field(default_factory=list)  # scatter: numeric x for `values`
    series: list[Series] = Field(default_factory=list)   # multi-series data
    source: str = ""      # which part of the user's data this came from
    rationale: str = ""   # why this chart type suits the data

    @field_validator("kind", mode="before")
    @classmethod
    def _coerce_kind(cls, v: Any) -> Any:
        return normalize_chart_kind(v)

    @property
    def has_data(self) -> bool:
        """Is there anything to plot? A chart without values renders as empty
        axes — a blank box under a caption — so callers skip it instead."""
        return bool(self.values) or any(s.values for s in self.series)


# ── blocks ──────────────────────────────────────────────────────────────────

class BlockBase(BaseModel):
    style: Optional[Style] = None   # explicit override; resolver fills the rest


class Heading(BlockBase):
    type: Literal["heading"] = "heading"
    level: int = 1                  # 1 = "I. INTRODUCTION", 2 = "A. Subsection", 3 = "1) point"
    text: str


class Paragraph(BlockBase):
    type: Literal["paragraph"] = "paragraph"
    text: str


class ListBlock(BlockBase):
    type: Literal["list"] = "list"
    ordered: bool = False
    items: list[str] = Field(default_factory=list)


class Equation(BlockBase):
    type: Literal["equation"] = "equation"
    text: str
    numbered: bool = True


class Table(BlockBase):
    type: Literal["table"] = "table"
    caption: str = ""
    columns: list[str] = Field(default_factory=list)
    rows: list[list[str]] = Field(default_factory=list)
    span: Literal["column", "page"] = "column"
    header_style: Optional[Style] = None
    cell_style: Optional[Style] = None
    caption_style: Optional[Style] = None


class Figure(BlockBase):
    type: Literal["figure"] = "figure"
    caption: str = ""
    chart: Optional[ChartSpec] = None
    image_path: Optional[str] = None
    span: Literal["column", "page"] = "column"
    caption_style: Optional[Style] = None


class Code(BlockBase):
    type: Literal["code"] = "code"
    language: str = ""
    text: str = ""
    caption: str = ""          # what the listing does; rendered as "Listing n."
    filename: str = ""         # e.g. "regime_scalars.py", shown with the caption
    caption_style: Optional[Style] = None


Block = Annotated[
    Union[Heading, Paragraph, ListBlock, Equation, Table, Figure, Code],
    Field(discriminator="type"),
]


# ── document ────────────────────────────────────────────────────────────────

class Author(BaseModel):
    name: str
    affiliation: str = ""
    email: str = ""


class PageSetup(BaseModel):
    width_in: float = 8.5
    height_in: float = 11.0
    margin_top_in: float = 0.75
    margin_bottom_in: float = 1.0
    margin_left_in: float = 0.625
    margin_right_in: float = 0.625
    columns: int = 2
    column_spacing_in: float = 0.25


class PaperMeta(BaseModel):
    title: str = "Untitled"
    authors: list[Author] = Field(default_factory=list)
    abstract: str = ""
    keywords: list[str] = Field(default_factory=list)
    # any registered stylesheet id: "ieee" | "apa" | "acm" | "report" | …
    style: str = "report"
    page: PageSetup = Field(default_factory=PageSetup)


class VisualizationNote(BaseModel):
    """Explicit statement of a chart opportunity found in the user's data."""
    data: str = ""     # what data it is
    kind: ChartKind = "bar"    # what visualisation to generate
    rationale: str = ""  # why

    @field_validator("kind", mode="before")
    @classmethod
    def _coerce_kind(cls, v: Any) -> Any:
        return normalize_chart_kind(v)


class PaperSpec(BaseModel):
    meta: PaperMeta = Field(default_factory=PaperMeta)
    blocks: list[Block] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)
    visualization_plan: list[VisualizationNote] = Field(default_factory=list)

    # set by the resolver so consumers know formatting is fully explicit
    resolved: bool = False

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=False)
