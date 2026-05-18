from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ExtractedRules:
    font_name: str | None = None
    heading_size_pt: int | None = None
    heading_bold: bool | None = None
    line_spacing: float | None = None
    margin_in: float | None = None
    include_charts: bool | None = None


def _find_float(pattern: str, text: str) -> float | None:
    m = re.search(pattern, text, flags=re.IGNORECASE)
    if not m:
        return None
    try:
        return float(m.group(1))
    except Exception:
        return None


def _find_int(pattern: str, text: str) -> int | None:
    m = re.search(pattern, text, flags=re.IGNORECASE)
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None


def extract_rules(formatting_instructions: str) -> dict[str, Any]:
    text = formatting_instructions or ""

    font_name = None
    for candidate in [
        "Times New Roman",
        "Calibri",
        "Arial",
        "Garamond",
        "Georgia",
    ]:
        if re.search(rf"\b{re.escape(candidate)}\b", text, flags=re.IGNORECASE):
            font_name = candidate
            break

    heading_size_pt = _find_int(r"heading\s*(?:size)?\s*(\d{1,2})", text)
    heading_bold = True if re.search(r"heading.*\bbold\b|\bbold\b.*heading", text, flags=re.IGNORECASE) else None

    line_spacing = _find_float(r"(\d+(?:\.\d+)?)\s*(?:line\s*)?spacing", text)

    margin_in = None
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:in|inch|inches)\s*margins?", text, flags=re.IGNORECASE)
    if m:
        try:
            margin_in = float(m.group(1))
        except Exception:
            margin_in = None

    include_charts = True if re.search(r"\binclude\s+charts?\b|\bcharts?\b", text, flags=re.IGNORECASE) else None

    rules = ExtractedRules(
        font_name=font_name,
        heading_size_pt=heading_size_pt,
        heading_bold=heading_bold,
        line_spacing=line_spacing,
        margin_in=margin_in,
        include_charts=include_charts,
    )

    return {k: v for k, v in rules.__dict__.items() if v is not None}
