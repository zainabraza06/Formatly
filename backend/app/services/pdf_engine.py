from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from fpdf import FPDF

from app.schemas import DocumentSection
from app.services.presets import get_preset


_FONT_MAP = {
    "Times New Roman": "Times",
    "Garamond": "Times",
    "Georgia": "Times",
    "Calibri": "Helvetica",
    "Arial": "Helvetica",
}


def _pdf_font(font_name: str) -> str:
    return _FONT_MAP.get(font_name, "Helvetica")


def _pdf_safe_text(text: str) -> str:
    # fpdf2 core fonts only support latin-1. We sanitize typical Unicode
    # punctuation that can appear in AI output and fall back to '?' replacement.
    if not text:
        return ""
    replacements = {
        "•": "-",
        "‣": "-",
        "–": "-",
        "—": "-",
        "−": "-",
        "“": '"',
        "”": '"',
        "„": '"',
        "’": "'",
        "‘": "'",
        "…": "...",
        "\u00a0": " ",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text.encode("latin-1", errors="replace").decode("latin-1")


def build_pdf(
    *,
    out_path: Path,
    title: str,
    outline: list[str],
    sections: list[DocumentSection],
    style_preset: str,
    extracted_rules: dict[str, Any],
    template_style: Optional[dict[str, Any]] = None,
    chart_pngs: Optional[list[Path]] = None,
    include_title_page: bool = True,
    include_toc: bool = True,
) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    preset = get_preset(style_preset)  # type: ignore[arg-type]

    font_name = (template_style or {}).get("font_name") or extracted_rules.get("font_name") or preset.font_name
    font = _pdf_font(str(font_name))
    margin_in = float((template_style or {}).get("margin_in") or extracted_rules.get("margin_in") or preset.margin_in)
    margin_mm = margin_in * 25.4

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=margin_mm)
    pdf.set_margins(left=margin_mm, top=margin_mm, right=margin_mm)

    def h1(text: str):
        pdf.set_font(font, style="B", size=max(14, preset.heading1_pt))
        pdf.ln(2)
        pdf.multi_cell(0, 7, _pdf_safe_text(text))
        pdf.ln(1)

    def body(text: str):
        pdf.set_font(font, size=max(10, preset.body_pt))
        pdf.multi_cell(0, 5, _pdf_safe_text(text))
        pdf.ln(1)

    if include_title_page:
        pdf.add_page()
        pdf.set_font(font, style="B", size=22)
        pdf.ln(40)
        pdf.multi_cell(0, 10, _pdf_safe_text(title), align="C")

    if include_toc:
        pdf.add_page()
        h1("Table of Contents")
        for item in outline:
            body(f"- {item}")

    pdf.add_page()
    for sec in sections:
        h1(sec.heading)
        for para in (sec.content or "").split("\n"):
            para = para.strip()
            if not para:
                continue
            body(para)

    if chart_pngs:
        pdf.add_page()
        h1("Charts")
        for p in chart_pngs:
            try:
                # 180mm wide fits within typical margins
                pdf.image(str(p), w=180)
                pdf.ln(4)
            except Exception:
                continue

    pdf.output(str(out_path))
    return out_path
