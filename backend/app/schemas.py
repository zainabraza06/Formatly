from __future__ import annotations

from typing import Any, Literal, Optional

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


class GenerateRequest(BaseModel):
    prompt: str
    formatting_instructions: str = ""
    style_preset: StylePreset = "business"
    tone: Tone = "formal"
    include_toc: bool = True
    include_title_page: bool = True
    include_charts: bool = False
    charts: list[ChartSpec] = Field(default_factory=list)
    template_id: Optional[str] = None


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


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class ChatRequest(BaseModel):
    document_id: Optional[str] = None
    messages: list[ChatMessage]


class ChatResponse(BaseModel):
    message: str


class TemplateAnalyzeResponse(BaseModel):
    template_id: str
    filename: str
    kind: Literal["docx", "pdf", "image", "unknown"]
    summary: str
    extracted_style: dict[str, Any] = Field(default_factory=dict)
