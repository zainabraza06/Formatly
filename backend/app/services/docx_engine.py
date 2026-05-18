from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.shared import OxmlElement, qn
from docx.shared import Inches

from app.schemas import DocumentSection
from app.services.presets import StyleConfig, get_preset, pt


def _set_margins(doc: Document, margin_in: float) -> None:
    for section in doc.sections:
        section.top_margin = Inches(margin_in)
        section.bottom_margin = Inches(margin_in)
        section.left_margin = Inches(margin_in)
        section.right_margin = Inches(margin_in)


def _set_normal_style(doc: Document, *, font_name: str, body_pt: int, line_spacing: float) -> None:
    normal = doc.styles["Normal"]
    normal.font.name = font_name
    normal.font.size = pt(body_pt)
    try:
        normal.paragraph_format.line_spacing = line_spacing
    except Exception:
        pass


def _set_heading_styles(
    doc: Document,
    *,
    font_name: str,
    heading1_pt: int,
    heading2_pt: int,
    heading_bold: bool = True,
) -> None:
    for name, size in [("Heading 1", heading1_pt), ("Heading 2", heading2_pt)]:
        try:
            style = doc.styles[name]
            style.font.name = font_name
            style.font.size = pt(size)
            style.font.bold = heading_bold
        except Exception:
            continue


def _add_title_page(doc: Document, title: str) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(title)
    run.bold = True
    run.font.size = pt(22)
    doc.add_page_break()


def _add_toc_placeholder(doc: Document, outline: list[str]) -> None:
    doc.add_paragraph("Table of Contents").style = "Heading 1"
    for item in outline:
        doc.add_paragraph(f"• {item}")
    doc.add_page_break()


def _add_chart_image(doc: Document, png_path: Path) -> None:
    doc.add_paragraph()
    doc.add_picture(str(png_path), width=Inches(6.0))


def build_docx(
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

    preset: StyleConfig = get_preset(style_preset)  # type: ignore[arg-type]

    font_name = (template_style or {}).get("font_name") or extracted_rules.get("font_name") or preset.font_name
    line_spacing = float((template_style or {}).get("line_spacing") or extracted_rules.get("line_spacing") or preset.line_spacing)
    margin_in = float((template_style or {}).get("margin_in") or extracted_rules.get("margin_in") or preset.margin_in)

    heading1_pt = int((template_style or {}).get("heading1_pt") or extracted_rules.get("heading_size_pt") or preset.heading1_pt)
    heading2_pt = int((template_style or {}).get("heading2_pt") or max(heading1_pt - 2, 10) or preset.heading2_pt)
    heading_bold = bool((template_style or {}).get("heading_bold") if (template_style or {}).get("heading_bold") is not None else extracted_rules.get("heading_bold", True))

    doc = Document()
    _set_margins(doc, margin_in)
    _set_normal_style(doc, font_name=font_name, body_pt=preset.body_pt, line_spacing=line_spacing)
    _set_heading_styles(doc, font_name=font_name, heading1_pt=heading1_pt, heading2_pt=heading2_pt, heading_bold=heading_bold)

    if include_title_page:
        _add_title_page(doc, title)
    if include_toc:
        _add_toc_placeholder(doc, outline)

    for sec in sections:
        doc.add_paragraph(sec.heading).style = "Heading 1"
        for para in (sec.content or "").split("\n"):
            para = para.strip()
            if not para:
                continue
            doc.add_paragraph(para)

    if chart_pngs:
        doc.add_page_break()
        doc.add_paragraph("Charts").style = "Heading 1"
        for p in chart_pngs:
            _add_chart_image(doc, p)

    doc.save(str(out_path))
    return out_path


def add_docx_toc_field(doc: Document) -> None:
    """Optional: add a Word TOC field. Not all viewers render it.

    Kept unused by default; placeholder TOC is more predictable.
    """

    p = doc.add_paragraph()
    run = p.add_run()
    fld_char_begin = OxmlElement("w:fldChar")
    fld_char_begin.set(qn("w:fldCharType"), "begin")

    instr_text = OxmlElement("w:instrText")
    instr_text.set(qn("xml:space"), "preserve")
    instr_text.text = "TOC \\o '1-3' \\h \\z \\u"

    fld_char_sep = OxmlElement("w:fldChar")
    fld_char_sep.set(qn("w:fldCharType"), "separate")

    fld_char_end = OxmlElement("w:fldChar")
    fld_char_end.set(qn("w:fldCharType"), "end")

    run._r.append(fld_char_begin)
    run._r.append(instr_text)
    run._r.append(fld_char_sep)
    run._r.append(fld_char_end)
