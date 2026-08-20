from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


StylePreset = Literal[
    "academic",
    "business",
    "research",
    "technical",
    "resume",
    "presentation",
]

Tone = Literal["formal", "simple", "technical"]


class ChartSpec(BaseModel):
    kind: Literal["bar", "line", "pie"]
    title: str = ""
    labels: list[str] = Field(default_factory=list)
    values: list[float] = Field(default_factory=list)
    x_label: str = ""
    y_label: str = ""
    explanation: str = ""


class GenerateRequest(BaseModel):
    prompt: str
    formatting_instructions: str = ""
    style_preset: StylePreset = "business"
    tone: Tone = "formal"
    include_toc: bool = True
    include_title_page: bool = True
    include_charts: bool = False
    charts: list[ChartSpec] = Field(default_factory=list)


class DocumentSection(BaseModel):
    id: str
    heading: str
    content: str


class PipelineStep(BaseModel):
    name: str
    status: Literal["pending", "running", "done", "error"] = "pending"
    detail: str = ""


class GenerateResponse(BaseModel):
    document_id: str
    title: str
    outline: list[str]
    sections: list[DocumentSection]
    extracted_rules: dict[str, Any]
    pipeline: list[PipelineStep]
    suggested_charts: list[ChartSpec] = Field(default_factory=list)


