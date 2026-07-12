"""Tests for the paper/report pipeline: schema → style resolver → DOCX renderer.

Runs fully offline (no LLM contacted); the generator is tested with a stub router.
"""
from __future__ import annotations

import json

import pytest
from docx import Document
from docx.oxml.ns import qn

from app.paper.generator import PaperGenerationError, generate_paper
from app.paper.renderer import render_paper
from app.paper.schema import PaperSpec
from app.paper.styles import get_stylesheet, list_styles
from app.paper.stylesheet import alpha, resolve, roman

SPEC = {
    "meta": {
        "title": "An Evaluation of Models",
        "authors": [{"name": "A. Researcher", "affiliation": "Test Lab", "email": "a@lab.org"}],
        "abstract": "This paper evaluates several models.",
        "keywords": ["testing", "models"],
    },
    "blocks": [
        {"type": "heading", "level": 1, "text": "Introduction"},
        {"type": "paragraph", "text": "Background prose goes here."},
        {"type": "heading", "level": 2, "text": "Dataset"},
        {"type": "list", "ordered": False, "items": ["First point", "Second point"]},
        {"type": "equation", "text": "E = mc^2", "numbered": True},
        {"type": "heading", "level": 1, "text": "Results"},
        {"type": "table", "caption": "Model performance",
         "columns": ["Model", "Accuracy"], "rows": [["CNN", "0.94"], ["SVM", "0.85"]]},
        {"type": "figure", "caption": "Accuracy by model",
         "chart": {"kind": "bar", "title": "Accuracy", "labels": ["CNN", "SVM"],
                   "values": [0.94, 0.85], "rationale": "compares one metric across models"}},
    ],
    "references": ["A. Author, \"A title,\" Journal, 2023."],
    "visualization_plan": [
        {"data": "accuracy per model", "kind": "bar", "rationale": "categorical comparison"}
    ],
}


# ── numbering helpers ───────────────────────────────────────────────────────

def test_roman_and_alpha():
    assert roman(1) == "I" and roman(4) == "IV" and roman(9) == "IX" and roman(14) == "XIV"
    assert alpha(1) == "A" and alpha(2) == "B" and alpha(27) == "AA"


# ── resolver ────────────────────────────────────────────────────────────────

def test_resolver_stamps_explicit_formatting():
    spec = resolve(PaperSpec.model_validate(SPEC), "ieee")
    assert spec.resolved is True
    assert spec.meta.style == "ieee"
    assert spec.meta.page.columns == 2

    heading = spec.blocks[0]
    assert heading.style.font == "Times New Roman"
    assert heading.style.small_caps is True

    body = spec.blocks[1]
    assert body.style.alignment == "justify"
    assert body.style.size_pt == 10

    table = next(b for b in spec.blocks if b.type == "table")
    assert table.header_style.bold is True
    assert table.cell_style.size_pt == 8


def test_resolver_keeps_author_overrides():
    data = json.loads(json.dumps(SPEC))
    data["blocks"][1]["style"] = {"italic": True, "size_pt": 14}
    spec = resolve(PaperSpec.model_validate(data), "ieee")
    body = spec.blocks[1]
    assert body.style.italic is True      # override survived
    assert body.style.size_pt == 14
    assert body.style.font == "Times New Roman"  # base still applied


def test_style_registry_and_aliases():
    ids = {s["id"] for s in list_styles()}
    assert {"ieee", "apa", "acm", "report"} <= ids
    assert get_stylesheet("IEEE").id == "ieee"
    assert get_stylesheet("apa 7").id == "apa"
    assert get_stylesheet("something unknown").id == "report"  # safe default


# ── renderer ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("style,cols,font", [
    ("ieee", "2", "Times New Roman"),
    ("apa", "1", "Times New Roman"),
    ("acm", "2", "Times New Roman"),
    ("report", "1", "Calibri"),
])
def test_render_each_style(tmp_path, style, cols, font):
    out = tmp_path / f"{style}.docx"
    render_paper(PaperSpec.model_validate(SPEC), out, style=style)
    assert out.exists()

    doc = Document(str(out))
    # last section carries the body column count
    last = doc.sections[-1]._sectPr.find(qn("w:cols"))
    assert last.get(qn("w:num")) == cols

    paras = [p for p in doc.paragraphs if p.text.strip()]
    assert paras[0].text == "An Evaluation of Models"
    assert paras[0].runs[0].font.name == font

    assert len(doc.tables) == 1
    assert len(doc.inline_shapes) == 1          # the bar chart rendered
    assert any("References" in p.text for p in paras)


def test_ieee_numbering_and_captions(tmp_path):
    out = tmp_path / "ieee.docx"
    render_paper(PaperSpec.model_validate(SPEC), out, style="ieee")
    texts = [p.text for p in Document(str(out)).paragraphs]

    assert any(t.startswith("I. Introduction") for t in texts)
    assert any(t.startswith("A. Dataset") for t in texts)
    assert any(t.startswith("II. Results") for t in texts)
    assert any(t.startswith("TABLE I") for t in texts)
    # IEEE figure captions run inline: "Fig. 1. Accuracy by model"
    assert any(t.startswith("Fig. 1.") and "Accuracy by model" in t and "\n" not in t
               for t in texts)


def test_decimal_numbering_for_report(tmp_path):
    out = tmp_path / "report.docx"
    render_paper(PaperSpec.model_validate(SPEC), out, style="report")
    texts = [p.text for p in Document(str(out)).paragraphs]
    assert any(t.startswith("1. Introduction") for t in texts)
    assert any(t.startswith("1.1 Dataset") for t in texts)
    assert any(t.startswith("2. Results") for t in texts)
    assert any(t.startswith("Table 1.") for t in texts)


def test_apa_caption_has_separator(tmp_path):
    out = tmp_path / "apa.docx"
    render_paper(PaperSpec.model_validate(SPEC), out, style="apa")
    texts = [p.text for p in Document(str(out)).paragraphs]
    cap = next(t for t in texts if t.startswith("Table 1"))
    assert cap == "Table 1\nModel performance"   # label and title on separate lines


# ── generator (stubbed LLM) ─────────────────────────────────────────────────

class _StubRouter:
    def __init__(self, reply: str):
        self.reply = reply

    def chat(self, messages, **kwargs):
        return self.reply, "stub", 0.01


def test_generator_validates_and_resolves():
    spec, provider = generate_paper(
        raw_text="some material",
        style="ieee",
        router=_StubRouter(json.dumps(SPEC)),
    )
    assert provider == "stub"
    assert spec.resolved is True
    assert spec.meta.style == "ieee"
    assert spec.blocks[0].style.small_caps is True


def test_generator_tolerates_fenced_json():
    fenced = "```json\n" + json.dumps(SPEC) + "\n```"
    spec, _ = generate_paper(raw_text="x", router=_StubRouter(fenced))
    assert spec.meta.title == "An Evaluation of Models"


def test_generator_rejects_non_json():
    with pytest.raises(PaperGenerationError):
        generate_paper(raw_text="x", router=_StubRouter("I cannot help with that."))


def test_generator_requires_material():
    with pytest.raises(PaperGenerationError):
        generate_paper(raw_text="   ", router=_StubRouter("{}"))


def test_generator_keeps_visualization_plan():
    spec, _ = generate_paper(raw_text="x", router=_StubRouter(json.dumps(SPEC)))
    assert spec.visualization_plan[0].kind == "bar"
    assert "accuracy" in spec.visualization_plan[0].data
