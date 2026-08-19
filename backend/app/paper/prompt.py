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
    "assignment": (
        "Style: formal assignment / official document.\n"
        "Structure the document the way submitted work is structured, adapted to the task: "
        "commonly Introduction or Problem Statement, Approach or Method, Implementation, "
        "Results, Discussion, Conclusion. Where the brief names its own sections or "
        "deliverables, use the brief's names and order instead of inventing your own.\n"
        "Write formally and in full sentences. Explain the reasoning, not just the outcome — "
        "a marker has to follow how the answer was reached.\n"
        "References numbered in order of first mention: [1] A. Author, \"Title,\" Publisher, Year."
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


# How much the model should write. Left to itself a model is markedly concise —
# it stops well short of any token ceiling — so depth has to be asked for
# explicitly rather than bought with a bigger max_tokens.
DEPTHS = ("brief", "standard")
DEFAULT_DEPTH = "standard"

_DEPTH_GUIDE: dict[str, str] = {
    "brief": (
        "LENGTH — brief: keep the document tight. One or two short paragraphs per section, "
        "no subsections unless the material genuinely needs them. Favour clarity over coverage."
    ),
    "standard": (
        "LENGTH — standard: give each section two to three developed paragraphs. Use level-2 "
        "subsections where a section has distinct parts."
    ),
    "detailed": (
        "LENGTH — detailed: write an in-depth, thorough document. Give every major section at "
        "least four substantial paragraphs, and break each one into level-2 subsections that "
        "are themselves developed rather than one-liners. Draw out implications, discuss "
        "limitations and alternatives, and explain reasoning fully. Do not summarise where you "
        "could analyse. Still never invent facts that are absent from the material — depth must "
        "come from analysis of what is given, not from fabricated detail."
    ),
}


def named_style_guide(name: str) -> str:
    """Guidance for an established style we do not implement a stylesheet for
    (Chicago, Harvard, MLA, Vancouver, a journal's house style…).

    We cannot reproduce such a style's typography without a stylesheet, but the
    model knows its *conventions*, and those are what a reader recognises: how
    sources are cited, how the reference list is ordered and formatted, how
    sections are conventionally arranged. So the request is honoured where it
    can be, rather than silently discarded.
    """
    return (
        f"Requested style: {name}.\n"
        f"Follow the conventions of {name} as they are commonly published: use its "
        f"in-text citation form, format every entry in `references` exactly as {name} "
        f"prescribes, and arrange the sections the way documents in {name} normally are. "
        f"If {name} has a conventional structure for this kind of document, use it. "
        f"Where {name} says nothing about a detail, choose what a careful editor would."
    )


def system_prompt(style: str, depth: str = DEFAULT_DEPTH,
                  style_note: Optional[str] = None) -> str:
    guide = named_style_guide(style_note) if style_note else _STYLE_GUIDE.get(
        style, _STYLE_GUIDE["report"])
    depth_guide = _DEPTH_GUIDE.get(depth, _DEPTH_GUIDE[DEFAULT_DEPTH])
    return f"{_BASE}\n{guide}\n{depth_guide}\n"


# ── multi-pass (agentic) prompts ────────────────────────────────────────────
#
# A single call cannot produce a genuinely detailed document: asked for depth, the
# model runs past any token ceiling and the JSON truncates, losing the whole
# document rather than part of it. So depth is produced in passes — plan once,
# then write each section on its own — and every call returns small, complete,
# validatable JSON.

PLAN_SYSTEM = """You are planning a document before it is written.

Return ONLY strict JSON. No markdown fences, no commentary.

Produce the front matter and a section plan — NOT the prose itself.

{
  "meta": {
    "title": "<concise, specific title>",
    "authors": [{"name": "...", "affiliation": "...", "email": "..."}],
    "abstract": "<150-250 word summary of the finished document>",
    "keywords": ["<4-6 terms>"]
  },
  "outline": [
    {"heading": "Introduction",
     "brief": "<what this section must cover, and which of the supplied material it draws on>",
     "subsections": ["<level-2 heading>", "..."]}
  ],
  "references": ["<formatted per the requested style>"],
  "visualization_plan": [
    {"data":"<which values in the input>","kind":"bar","rationale":"<why this chart suits them>"}
  ]
}

Rules:
- Choose the sections the material actually supports; do not pad with empty sections.
- Do NOT include an "Abstract" or "References" section in the outline — they are handled
  separately via meta.abstract and references.
- Assign each chartable set of values in the material to "visualization_plan", stating what
  the data is, the chart kind, and why. If there are no chartable values, return an empty list.
- Never invent facts, citations or numbers that are absent from the material.
"""

SECTION_SYSTEM = """You are writing ONE section of a document that is already planned.

Return ONLY strict JSON. No markdown fences, no commentary.

{"blocks": [ {"type":"heading","level":1,"text":"<this section's heading>"},
             {"type":"paragraph","text":"..."},
             {"type":"heading","level":2,"text":"<a subsection>"},
             {"type":"paragraph","text":"..."},
             {"type":"list","ordered":false,"items":["..."]},
             {"type":"table","caption":"...","columns":["..."],"rows":[["..."]]},
             {"type":"figure","caption":"...",
              "chart":{"kind":"bar","title":"...","x_label":"...","y_label":"...",
                       "labels":["..."],"values":[1.0],
                       "source":"...","rationale":"..."}},
             {"type":"equation","text":"...","numbered":true} ] }

Rules:
- Write ONLY the section you are given. Start with its level-1 heading. Do not write any
  other section, and do not restate what other sections cover.
- Headings are numbered automatically; do not put numbers in heading text.
- Include a table or figure ONLY if this section is the one that should carry it according to
  the visualisation plan you are given, and only using values present in the material.
- Never invent facts, citations or numbers that are absent from the material.
"""


def plan_system_prompt(style: str, depth: str = DEFAULT_DEPTH,
                       style_note: Optional[str] = None) -> str:
    guide = named_style_guide(style_note) if style_note else _STYLE_GUIDE.get(
        style, _STYLE_GUIDE["report"])
    depth_guide = _DEPTH_GUIDE.get(depth, _DEPTH_GUIDE[DEFAULT_DEPTH])
    return f"{PLAN_SYSTEM}\n{guide}\n{depth_guide}\n"


def section_system_prompt(style: str, depth: str = DEFAULT_DEPTH,
                          style_note: Optional[str] = None) -> str:
    guide = named_style_guide(style_note) if style_note else _STYLE_GUIDE.get(
        style, _STYLE_GUIDE["report"])
    depth_guide = _DEPTH_GUIDE.get(depth, _DEPTH_GUIDE[DEFAULT_DEPTH])
    return f"{SECTION_SYSTEM}\n{guide}\n{depth_guide}\n"


def build_plan_message(**kwargs: Any) -> str:
    """Same material payload as a single-pass run, framed as a planning task."""
    return _material_message(
        lead="Plan the document for the following material.", **kwargs
    )


def build_section_message(
    *,
    section: dict[str, Any],
    outline: Sequence[dict[str, Any]],
    title: str,
    visualization_plan: Sequence[dict[str, Any]],
    written_so_far: Sequence[str],
    raw_text: str,
    attachments: Optional[Sequence[dict[str, str]]] = None,
    instructions: Optional[str] = None,
) -> str:
    payload: dict[str, Any] = {
        "task": f"Write the section '{section.get('heading', '')}' of the document.",
        "document_title": title,
        "this_section": section,
        "full_outline": [s.get("heading", "") for s in outline],
        "sections_already_written": list(written_so_far),
        "visualization_plan": list(visualization_plan),
        "source_material": raw_text,
    }
    extras = _clean_attachments(attachments)
    if extras:
        payload["additional_material"] = extras
    if instructions:
        payload["extra_instructions"] = instructions
    return ("Produce the JSON for this section only.\n"
            + json.dumps(payload, indent=2, ensure_ascii=False))


def _clean_attachments(attachments: Optional[Sequence[dict[str, str]]]) -> list[dict[str, str]]:
    return [
        {"label": (a.get("label") or "additional material").strip(),
         "content": a.get("content", "")}
        for a in (attachments or [])
        if (a.get("content") or "").strip()
    ]


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
    return _material_message(
        lead="Produce the document JSON for the following material.",
        raw_text=raw_text, style=style, doc_kind=doc_kind, attachments=attachments,
        reference_example=reference_example, instructions=instructions,
        title_hint=title_hint, authors=authors,
    )


def _material_message(
    *,
    lead: str,
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
    extras = _clean_attachments(attachments)
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

    return f"{lead}\n" + json.dumps(payload, indent=2, ensure_ascii=False)
