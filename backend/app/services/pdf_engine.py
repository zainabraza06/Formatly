"""
PDF generation engine using fpdf2.
Produces professionally formatted PDFs with:
  - Centered title page with subtitle and date
  - Table of contents with dotted leaders
  - Justified body text
  - Proper heading hierarchy with spacing
  - Embedded chart images with captions
"""
from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any, Optional

from fpdf import FPDF

from app.schemas import ChartSpec, DocumentSection
from app.services.presets import get_preset


# fpdf2 core fonts only support latin-1 characters
_FONT_MAP = {
    "Times New Roman": "Times",
    "Garamond": "Times",
    "Georgia": "Times",
    "Calibri": "Helvetica",
    "Arial": "Helvetica",
    "Helvetica": "Helvetica",
}


def _pdf_font(font_name: str) -> str:
    return _FONT_MAP.get(str(font_name), "Helvetica")


def _safe(text: str) -> str:
    """Sanitize Unicode to latin-1 safe representation."""
    if not text:
        return ""
    replacements = {
        "•": "-", "‣": "-",
        "–": "-", "—": "-", "−": "-",
        "“": '"', "”": '"', "„": '"',
        "‘": "'", "’": "'",
        "…": "...", " ": " ",
        "─": "-", "━": "-",
        "→": "->", "←": "<-",
        "●": "*", "►": ">",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text.encode("latin-1", errors="replace").decode("latin-1")


class _Doc(FPDF):
    """FPDF subclass that tracks the current font for convenience helpers."""

    def __init__(self, font: str, margin_mm: float) -> None:
        super().__init__(orientation="P", unit="mm", format="A4")
        self._font = font
        self._margin = margin_mm
        self.set_auto_page_break(auto=True, margin=margin_mm)
        self.set_margins(left=margin_mm, top=margin_mm, right=margin_mm)

    # usable width in mm
    @property
    def _w(self) -> float:
        return 210 - 2 * self._margin

    def h1(self, text: str, size: int = 16) -> None:
        self.set_font(self._font, style="B", size=size)
        self.ln(4)
        self.multi_cell(self._w, 8, _safe(text), align="L")
        self.ln(2)

    def h2(self, text: str, size: int = 13) -> None:
        self.set_font(self._font, style="B", size=size)
        self.ln(2)
        self.multi_cell(self._w, 7, _safe(text), align="L")
        self.ln(1)

    def body(self, text: str, size: int = 11) -> None:
        self.set_font(self._font, size=size)
        self.multi_cell(self._w, 5.5, _safe(text), align="J")
        self.ln(1)

    def center_text(self, text: str, size: int = 11, style: str = "") -> None:
        self.set_font(self._font, style=style, size=size)
        self.multi_cell(self._w, 7, _safe(text), align="C")

    def rule(self, width_frac: float = 0.5) -> None:
        """Draw a thin horizontal rule centered on the page."""
        rule_w = self._w * width_frac
        x = self._margin + (self._w - rule_w) / 2
        y = self.get_y() + 2
        self.set_draw_color(180, 180, 190)
        self.set_line_width(0.3)
        self.line(x, y, x + rule_w, y)
        self.set_line_width(0.2)
        self.set_draw_color(0, 0, 0)
        self.ln(4)


def _add_title_page(pdf: _Doc, title: str, subtitle: str = "") -> None:
    pdf.add_page()

    # vertical centering: push ~80 mm down
    pdf.ln(55)

    # decorative rule above
    pdf.rule(0.45)

    # main title
    pdf.center_text(title, size=26, style="B")
    pdf.ln(4)

    # decorative rule below title
    pdf.rule(0.45)

    pdf.ln(6)

    if subtitle:
        pdf.center_text(subtitle, size=13, style="I")
        pdf.ln(4)

    # date
    pdf.center_text(datetime.date.today().strftime("%B %Y"), size=10)
    pdf.ln(2)


def _add_toc(pdf: _Doc, outline: list[str]) -> None:
    pdf.add_page()
    pdf.h1("Table of Contents")
    pdf.ln(2)

    for i, item in enumerate(outline, 1):
        pdf.set_font(pdf._font, size=11)
        # calculate dots to fill line
        dots = "." * max(0, 58 - len(f"{i}. {item}"))
        line = _safe(f"{i}.  {item}  {dots}  {i + 1}")
        pdf.cell(pdf._w, 7, line, ln=True)


def build_pdf(
    *,
    out_path: Path,
    title: str,
    outline: list[str],
    sections: list[DocumentSection],
    style_preset: str,
    extracted_rules: dict[str, Any],
    template_style: Optional[dict[str, Any]] = None,
    chart_specs: Optional[list[ChartSpec]] = None,
    chart_pngs: Optional[list[Path]] = None,
    include_title_page: bool = True,
    include_toc: bool = True,
) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    ts     = template_style or {}
    preset = get_preset(style_preset)  # type: ignore[arg-type]

    font_name   = ts.get("font_name") or extracted_rules.get("font_name") or preset.font_name
    font        = _pdf_font(str(font_name))
    margin_in   = float(ts.get("margin_in") or extracted_rules.get("margin_in") or preset.margin_in)
    margin_mm   = margin_in * 25.4
    heading1_pt = int(ts.get("heading1_pt") or extracted_rules.get("heading_size_pt") or preset.heading1_pt)
    heading2_pt = max(heading1_pt - 2, 10)
    body_pt     = preset.body_pt

    pdf = _Doc(font=font, margin_mm=margin_mm)

    if include_title_page:
        _add_title_page(pdf, title, subtitle=style_preset.replace("_", " ").title())

    if include_toc and outline:
        _add_toc(pdf, outline)

    # ── Body sections ──────────────────────────────────────────────────────────
    pdf.add_page()
    for sec in sections:
        pdf.h1(sec.heading, size=heading1_pt)
        for para in (sec.content or "").split("\n"):
            para = para.strip()
            if not para:
                continue
            pdf.body(para, size=body_pt)
        pdf.ln(3)

    # ── Charts ─────────────────────────────────────────────────────────────────
    if chart_pngs:
        pdf.add_page()
        pdf.h1("Charts & Visualizations", size=heading1_pt)
        pdf.ln(2)

        for idx, png in enumerate(chart_pngs):
            if not Path(png).exists():
                continue
            try:
                pdf.image(str(png), w=min(pdf._w, 170))
            except Exception:
                pdf.body(f"[Chart {idx + 1}: image unavailable]", size=body_pt)

            caption = ""
            if chart_specs and idx < len(chart_specs):
                caption = f"Figure {idx + 1}: {chart_specs[idx].title}"
            if caption:
                pdf.set_font(font, style="I", size=9)
                pdf.multi_cell(pdf._w, 5, _safe(caption), align="C")
            pdf.ln(5)

    pdf.output(str(out_path))
    return out_path
