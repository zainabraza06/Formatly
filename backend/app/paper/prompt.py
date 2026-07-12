"""Prompt construction for document generation in any requested style.

The model writes the *content* and identifies visualisation opportunities. It does
NOT need to get typography right — the stylesheet resolver stamps explicit
formatting onto every block afterwards. This keeps the model focused on prose
quality and data understanding, where it is actually useful.
"""
from __future__ import annotations

import json
from typing import Any, Optional

# Structure + citation conventions per style. The renderer enforces typography;
# this only steers what the model writes.
_STYLE_GUIDE: dict[str, str] = {
    "ieee": (
        "Style: IEEE conference paper.\n"
        "Sections (level-1 headings, in this order, omitting any the material cannot support):\n"
        "  Introduction, Related Work, Methodology, Experimental Setup, Results and Discussion, Conclusion\n"
        "References must be in IEEE format: A. Author, \"Title,\" Journal, vol. x, no. y, pp. 1-10, Year."
    ),
    "acm": (
        "Style: ACM conference paper.\n"
        "Sections: Introduction, Background and Related Work, Approach, Evaluation, Results, Conclusion.\n"
        "References in ACM reference format."
    ),
    "apa": (
        "Style: APA 7th edition research paper.\n"
        "Sections: Introduction, Method, Results, Discussion, Conclusion.\n"
        "References in APA format: Author, A. A. (Year). Title of work. Publisher/Journal, vol(issue), pages.\n"
        "Use APA in-text citation style (Author, Year) inside the prose where a source is referenced."
    ),
    "report": (
        "Style: professional technical/business report.\n"
        "Sections: Executive Summary, Introduction, Approach/Methodology, Findings, "
        "Discussion, Recommendations, Conclusion.\n"
        "Write for a mixed technical and managerial audience: precise, but no unexplained jargon."
    ),
}

_BASE = """You are a document generation engine. You produce complete, publication-quality documents.

Return ONLY strict JSON. No markdown fences, no commentary, no prose outside the JSON.

Write in FORMAL English appropriate to the requested style. Do not use casual language.
CRITICAL: do not invent citations, statistics, or numeric results that are not supported by
the supplied material. If a value is not given, describe it qualitatively instead of
fabricating it. You may write the surrounding analysis and explanation freely.

JSON shape:
{
  "meta": {
    "title": "<concise, specific title>",
    "authors": [{"name": "...", "affiliation": "...", "email": "..."}],
    "abstract": "<150-250 words: context, problem, approach, key results, conclusion>",
    "keywords": ["<4-6 terms>"]
  },
  "blocks": [
    {"type":"heading","level":1,"text":"Introduction"},
    {"type":"paragraph","text":"..."},
    {"type":"heading","level":2,"text":"Dataset"},
    {"type":"list","ordered":false,"items":["...","..."]},
    {"type":"equation","text":"F1 = 2 * (P * R) / (P + R)","numbered":true},
    {"type":"table","caption":"Model performance",
     "columns":["Model","Accuracy","F1"],
     "rows":[["CNN","0.91","0.90"],["SVM","0.85","0.84"]]},
    {"type":"figure","caption":"Accuracy across models",
     "chart":{"kind":"bar","title":"Model accuracy","x_label":"Model","y_label":"Accuracy",
              "labels":["CNN","SVM"],"values":[0.91,0.85],
              "source":"accuracy values in the supplied results",
              "rationale":"a bar chart best compares one metric across discrete models"}},
    {"type":"code","language":"python","text":"..."}
  ],
  "references": ["<formatted per the requested style>"],
  "visualization_plan": [
    {"data":"<which numbers in the input>","kind":"bar","rationale":"<why this chart>"}
  ]
}

Do NOT emit an "Abstract" or "References" heading block — use meta.abstract and references.
Headings are numbered automatically by the renderer; do not put numbers in heading text.

VISUALISATION RULES — important:
- Scan the supplied data/results for anything chartable: metrics per model/category,
  values per epoch or over time, class or category distributions, timing comparisons,
  ablation results, before/after comparisons.
- For EVERY such opportunity, add an entry to "visualization_plan" stating explicitly what
  the data is, which chart kind to generate, and why that kind fits the data.
- Also emit a matching "figure" block whose "chart" carries the ACTUAL numbers from the
  input so the chart can be rendered. Never invent data points.
- Chart kinds: "bar" (compare a metric across categories), "line" (trend over an ordered
  axis such as epochs/time), "pie" (composition of a whole), "scatter" (relationship
  between two variables), "grouped_bar" (several metrics across the same categories —
  supply "series": [{"name":"Precision","values":[...]}, ...]).
- If the input contains no chartable numbers, return an empty "visualization_plan" and no
  figure blocks. Do not fabricate data to justify a chart.

TABLES — put quantitative comparisons in tables as well as charts where it helps the reader.
EQUATIONS — include the key formulae the method relies on, if any.
"""


def system_prompt(style: str) -> str:
    guide = _STYLE_GUIDE.get(style, _STYLE_GUIDE["report"])
    return f"{_BASE}\n{guide}\n"


def build_user_message(
    *,
    raw_text: str,
    style: str = "report",
    doc_kind: str = "paper",
    code: Optional[str] = None,
    results: Optional[str] = None,
    reference_example: Optional[str] = None,
    instructions: Optional[str] = None,
    title_hint: Optional[str] = None,
    authors: Optional[list[dict[str, str]]] = None,
) -> str:
    payload: dict[str, Any] = {
        "task": f"Write a complete {doc_kind} in {style.upper()} style from the material below.",
        "source_material": raw_text,
    }
    if code:
        payload["source_code"] = code
    if results:
        payload["model_results"] = results
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
