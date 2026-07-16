"""Prompt construction for document generation.

The model writes the *content* and identifies visualisation opportunities. It does
NOT need to get typography right — the stylesheet resolver stamps explicit
formatting onto every block afterwards. This keeps the model focused on prose
quality and understanding the material, where it is actually useful.

Nothing here assumes a domain. The user supplies a body of material plus any
number of freely-labelled attachments (data, transcripts, code, citations,
survey responses — whatever the job needs), and the model adapts.
"""
from __future__ import annotations

import json
from typing import Any, Optional, Sequence

# Structure + citation conventions per style. The renderer enforces typography;
# this only steers what the model writes. Section lists are typical shapes, not
# mandates — the model is told to adapt them to the actual material.
_STYLE_GUIDE: dict[str, str] = {
    "ieee": (
        "Style: IEEE.\n"
        "Use IEEE sectioning conventions, adapted to the material. For empirical work that is "
        "typically Introduction, Related Work, Methodology, Experimental Setup, Results and "
        "Discussion, Conclusion. For other kinds of work, choose the sections the subject "
        "actually calls for.\n"
        "References in IEEE format: A. Author, \"Title,\" Journal, vol. x, no. y, pp. 1-10, Year."
    ),
    "acm": (
        "Style: ACM.\n"
        "Use ACM sectioning conventions, adapted to the material — commonly Introduction, "
        "Background and Related Work, Approach, Evaluation, Results, Conclusion.\n"
        "References in ACM reference format."
    ),
    "apa": (
        "Style: APA 7th edition.\n"
        "Use APA conventions, adapted to the material. For a study that is typically "
        "Introduction, Method, Results, Discussion, Conclusion; for a review or theoretical "
        "piece, use thematic sections instead.\n"
        "References in APA format: Author, A. A. (Year). Title of work. Publisher/Journal, "
        "vol(issue), pages.\n"
        "Use APA in-text citation style (Author, Year) in the prose where a source is referenced."
    ),
    "report": (
        "Style: professional report.\n"
        "Choose the sections the subject calls for. A common shape is Executive Summary, "
        "Introduction, Background, Findings, Discussion, Recommendations, Conclusion — adapt, "
        "rename or drop these freely to suit the material.\n"
        "Write for a mixed specialist and non-specialist audience: precise, but no unexplained jargon."
    ),
}

_BASE = """You are a document generation engine. You produce complete, publication-quality documents
of any kind — research papers, reports, reviews, proposals, case studies, memos, technical
documentation — on any subject.

Return ONLY strict JSON. No markdown fences, no commentary, no prose outside the JSON.

Write in FORMAL English appropriate to the requested style and document kind. Do not use
casual language.

CRITICAL — do not invent facts. Never fabricate citations, statistics, quantities, dates or
results that are not present in the supplied material. If a value is not given, describe the
matter qualitatively instead of inventing a number. You may write the surrounding analysis,
explanation and framing freely; you may not manufacture evidence.

Let the material decide the shape of the document. Use only the sections, tables, equations
and figures the material actually supports. A document with no numbers should contain no
tables or charts; a document with no formal method needs no methodology section.

JSON shape:
{
  "meta": {
    "title": "<concise, specific title>",
    "authors": [{"name": "...", "affiliation": "...", "email": "..."}],
    "abstract": "<150-250 word summary: context, purpose, approach, key points, conclusion>",
    "keywords": ["<4-6 terms>"]
  },
  "blocks": [
    {"type":"heading","level":1,"text":"Introduction"},
    {"type":"paragraph","text":"..."},
    {"type":"heading","level":2,"text":"A subsection"},
    {"type":"list","ordered":false,"items":["...","..."]},
    {"type":"equation","text":"y = mx + c","numbered":true},
    {"type":"table","caption":"Summary of reported values",
     "columns":["Category","Value"],
     "rows":[["Group A","12.4"],["Group B","9.8"]]},
    {"type":"figure","caption":"Values by category",
     "chart":{"kind":"bar","title":"Values by category","x_label":"Category","y_label":"Value",
              "labels":["Group A","Group B"],"values":[12.4,9.8],
              "source":"the values given in the supplied material",
              "rationale":"a bar chart compares one quantity across discrete categories"}},
    {"type":"code","language":"python","text":"..."}
  ],
  "references": ["<formatted per the requested style>"],
  "visualization_plan": [
    {"data":"<which values in the input>","kind":"bar","rationale":"<why this chart suits them>"}
  ]
}

Do NOT emit an "Abstract" or "References" heading block — use meta.abstract and references.
Headings are numbered automatically by the renderer; do not put numbers in heading text.
Use "code" blocks only if the material actually contains or requires code.

VISUALISATION RULES — important:
- Scan ALL supplied material for anything chartable, whatever the domain. Look for:
  comparable quantities across categories (products, regions, groups, methods, treatments);
  values along an ordered axis (time, dates, stages, doses, iterations); composition or share
  of a whole; the relationship between two variables; before-and-after comparisons.
- For EVERY such opportunity, add an entry to "visualization_plan" stating explicitly what the
  data is, which chart kind to generate, and why that kind suits it.
- Also emit a matching "figure" block whose "chart" carries the ACTUAL values from the input,
  so the chart can be rendered. Never invent data points.
- Chart kinds: "bar" (compare a quantity across categories), "line" (trend along an ordered
  axis), "pie" (composition of a whole), "scatter" (relationship between two variables),
  "grouped_bar" (several quantities across the same categories — supply
  "series": [{"name":"Q1","values":[...]}, ...]).
- If the material contains no chartable values, return an empty "visualization_plan" and no
  figure blocks. Do not fabricate data to justify a chart.

TABLES — use them for quantitative or comparative content where they help the reader.
EQUATIONS — include any formulae the material relies on, if any.
"""


def system_prompt(style: str) -> str:
    guide = _STYLE_GUIDE.get(style, _STYLE_GUIDE["report"])
    return f"{_BASE}\n{guide}\n"


def build_user_message(
    *,
    raw_text: str,
    style: str = "report",
    doc_kind: str = "document",
    attachments: Optional[Sequence[dict[str, str]]] = None,
    reference_example: Optional[str] = None,
    instructions: Optional[str] = None,
    title_hint: Optional[str] = None,
    authors: Optional[list[dict[str, str]]] = None,
) -> str:
    payload: dict[str, Any] = {
        "task": f"Write a complete {doc_kind} in {style.upper()} style from the material below.",
        "source_material": raw_text,
    }

    # Arbitrary user-labelled material: data, results, code, transcripts, notes,
    # citations — whatever this particular job involves.
    extras = [
        {"label": (a.get("label") or "additional material").strip(),
         "content": a.get("content", "")}
        for a in (attachments or [])
        if (a.get("content") or "").strip()
    ]
    if extras:
        payload["additional_material"] = extras

    if reference_example:
        payload["reference_example_to_follow"] = reference_example
    if instructions:
        payload["extra_instructions"] = instructions
    if title_hint:
        payload["title_hint"] = title_hint
    if authors:
        payload["authors"] = authors

    return ("Produce the document JSON for the following material.\n"
            + json.dumps(payload, indent=2, ensure_ascii=False))
