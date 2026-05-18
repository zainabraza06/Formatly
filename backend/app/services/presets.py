from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from docx.shared import Inches, Pt

from app.schemas import StylePreset


@dataclass(frozen=True)
class StyleConfig:
    font_name: str
    body_pt: int
    heading1_pt: int
    heading2_pt: int
    line_spacing: float
    margin_in: float


_PRESETS: dict[StylePreset, StyleConfig] = {
    "academic": StyleConfig(
        font_name="Times New Roman",
        body_pt=12,
        heading1_pt=16,
        heading2_pt=14,
        line_spacing=1.5,
        margin_in=1.0,
    ),
    "business": StyleConfig(
        font_name="Calibri",
        body_pt=11,
        heading1_pt=16,
        heading2_pt=13,
        line_spacing=1.15,
        margin_in=1.0,
    ),
    "research": StyleConfig(
        font_name="Times New Roman",
        body_pt=12,
        heading1_pt=16,
        heading2_pt=14,
        line_spacing=1.5,
        margin_in=1.0,
    ),
    "technical": StyleConfig(
        font_name="Calibri",
        body_pt=11,
        heading1_pt=15,
        heading2_pt=13,
        line_spacing=1.15,
        margin_in=1.0,
    ),
    "resume": StyleConfig(
        font_name="Calibri",
        body_pt=10,
        heading1_pt=14,
        heading2_pt=12,
        line_spacing=1.0,
        margin_in=0.7,
    ),
    "presentation": StyleConfig(
        font_name="Calibri",
        body_pt=12,
        heading1_pt=18,
        heading2_pt=14,
        line_spacing=1.15,
        margin_in=1.0,
    ),
}


def get_preset(style: StylePreset) -> StyleConfig:
    return _PRESETS.get(style, _PRESETS["business"])


def inches(value: float):
    return Inches(value)


def pt(value: int):
    return Pt(value)
