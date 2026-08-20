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
        "Submitted coursework is not a research paper. Leave meta.abstract EMPTY and "
        "meta.keywords empty unless the brief explicitly asks for an abstract or keywords, "
        "and return an empty `references` list unless the brief asks for references or the "
        "work genuinely cites sources. Do not add either merely to look scholarly.\n"
        "If references are called for, number them in order of first mention and write the "
        "entry only — the [1] numbering is added for you, so never start an entry with it."
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
    {"type":"figure","caption":"Relationship between the two measures",
     "chart":{"kind":"scatter","x_label":"Measure A","y_label":"Measure B",
              "x_values":[0.2,0.7],"values":[0.9,0.3],
              "series":[{"name":"group two","x_values":[0.3,0.8],"values":[0.5,0.4]}],
              "source":"...","rationale":"..."}},
    {"type":"code","language":"python","filename":"solver.py",
     "caption":"what this listing does","text":"line one\\nline two"}
  ],
  "references": ["<formatted per the requested style; the entry only — the [1] numbering is added for you>"],
  "visualization_plan": [
    {"data":"<which values in the input>","kind":"bar","rationale":"<why this chart suits them>"}
  ]
}

Do NOT emit an "Abstract" or "References" heading block — use meta.abstract and references.
Headings are numbered automatically by the renderer; do not put numbers in heading text.

WHEN THE MATERIAL IS A BRIEF — a task, assignment, problem set, specification or
set of questions rather than a body of findings to write up:
- First read out every requirement it states: numbered tasks, sub-parts, "you must" or
  "your submission should" sentences, deliverables, and any marking criteria. Treat that list
  as the contract for the document.
- Answer EVERY one of them. Do not silently drop a part because it is harder or because the
  supplied material is thin — address it explicitly, and say plainly where an assumption was
  needed. A document that covers eight of ten requirements has failed.
- HONOUR THE COUNTS. Where the brief names a number — five screenshots, three test cases,
  two examples — produce that many, not "several". Where it asks for something *per task*,
  *per feature* or *for each part*, produce one for each: a brief listing four tasks and
  asking for a screenshot of each needs four screenshots, one sitting in each task's own
  section. Before finishing, count what you emitted against what was asked.
- Structure the document so a marker can find each requirement: follow the brief's own order
  and its own names for the parts, and give each substantial requirement its own section or
  subsection.
- Do the work, do not describe the work. Derive the mathematics step by step rather than
  naming the method; write the code rather than explaining what the code would do; work the
  numbers rather than saying they could be worked. Then explain the reasoning in prose so the
  answer can be followed and marked.

CODE — when the task calls for an implementation, or the user asks for snippets:
- Emit real, complete, runnable code in "code" blocks. Give "language", and give "caption"
  saying what the listing does; add "filename" when the code belongs in a named file.
- Split a long program into several listings — one per function or per step — with the prose
  explaining each in between. One unbroken wall of code is not an explanation.
- Honour whatever environment the user names (a plain script, a VS Code project, a Colab or
  Jupyter notebook, a specific language, framework or version): match its conventions, its
  cell or file structure, and any imports and setup that environment needs.
- Set "render":"image" on a listing ONLY when the brief asks to *see* the code in an editor —
  "attach a screenshot of your VS Code", "show the notebook cell". That draws the listing as
  an editor window with syntax highlighting and line numbers ("theme":"dark" or "light").
  Otherwise leave it as text, which stays selectable and copyable.
- If no code is called for, emit no "code" blocks.
- A "code" block MUST carry its actual code in "text". Never emit a listing with empty or
  placeholder text: an empty listing is dropped, leaving your caption promising something
  that is not there.

SCREENSHOTS — a brief often asks for several. Two kinds can be drawn, both from text you
write yourself, and both go in a "code" block with "render":"image":
- Source code, as an editor window: "window":"editor" with the real "language" and a
  "filename". Syntax colours and line numbers are added for you.
- A program's output, as a console window: "window":"terminal", "language":"text", and the
  session written out exactly as it would appear — prompts, the user's typed input, the
  program's replies. Put the window's title in "filename" (e.g. "Command Prompt") if it
  matters.
Nothing is executed while this document is written, so write the session you know the
program produces, and keep it faithful to the code you wrote: the same wording, the same
prompts, plausible inputs. Do NOT claim it is a capture of a real run.
You CANNOT picture anything else — no installer, website, GUI, IDE debugger or file
explorer. NEVER write a heading, caption or sentence announcing a screenshot you are not
emitting: a section reading "Screenshot 2 — Program Starting" with nothing under it is worse
than no section, because it tells the reader something is missing.

MATHEMATICS — when the task involves derivations, formulae or worked numbers:
- Put each formula in an "equation" block, written as TeX math markup: \\frac{a}{b},
  \\sqrt{x}, x^{2}, x_{i}, \\sum_{i=1}^{n}, \\int, \\alpha, \\bar{x}, \\pm, \\leq.
  It is typeset properly — no LaTeX installation is involved, and you do not need to avoid
  fractions, radicals, subscripts or limits.
- Do not write markup in "paragraph" text; prose is set as plain text and the markup would
  show through literally. Formulae belong in "equation" blocks.
- Show the working: state the formula, substitute the actual values, then give the result.
  A derivation that jumps from the formula to the answer cannot be marked.

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
- A "scatter" needs BOTH coordinates: put the y values in "values" and the matching x values
  in "x_values". To colour points by group, give one entry in "series" per group, each with
  its own "x_values" and "values". A scatter with no values is dropped, not drawn.
- If the material contains no chartable values, return an empty "visualization_plan" and no
  figure blocks. Do not fabricate data to justify a chart.

EXTRA INSTRUCTIONS — these are the user's own words and they OVERRIDE the defaults
above. If `extra_instructions` is present in the payload, follow every part of it. It is
not a hint or a preference: a request to bold key terms, keep sections short, use a
particular voice, include or omit something, is binding. Where it conflicts with a default
in this prompt, the user wins. Re-read it before you finish and check you did each thing
it asked.

EMPHASIS — inside any "text" field you may mark emphasis with **bold** and *italic*, and
the renderer turns those into real bold and italic runs. Use them where the user asks for
emphasis, and where a key term genuinely earns it. ("No markdown fences" above is about
the JSON envelope — never wrap the JSON itself in ``` — not about the prose inside it.)

LAYOUT AND FORMATTING — the stylesheet sets sensible typography, but the user may ask for
something specific, and you have the means to give it to them. Do not answer a formatting
instruction with prose about it; express it.
- EVERY block accepts an optional "style" object that overrides the stylesheet for that block
  alone. Any subset of:
  {"font":"Arial","size_pt":12,"bold":true,"italic":true,"underline":true,"small_caps":true,
   "all_caps":true,"color":"#000000","alignment":"left|center|right|justify",
   "first_line_indent_in":0.5,"left_indent_in":0.5,"hanging_indent_in":0.25,
   "space_before_pt":12,"space_after_pt":6,"line_spacing":2.0,"keep_with_next":true}
  So "double-space it" is "line_spacing":2.0; "centre the headings" is
  "alignment":"center"; "indent the quotation" is "left_indent_in". Use it only where asked
  or where the content plainly needs it — do not restyle a document nobody asked you to.
- {"type":"page_break"} starts what follows on a new page. Use it when the user asks for a
  section to begin on its own page.
- A COVER SHEET, when and only when the brief or the user asks for one: set
  "title_page": true in meta, and put every extra line they name — course code and title,
  student id, registration number, submission date, supervisor, department — in
  "title_page_lines" as separate strings, in the order asked for. The cover sheet then holds
  the title, the authors, and exactly those lines, and the document starts on the next page.
  If they say it should contain only certain things, put only those things there.
  Without "title_page": true there is no separate cover sheet, which is right for a paper.
- A RUNNING HEADER, when asked for one: put the line in meta.page_header (e.g. an institution
  and campus, "NUST, H-12, Islamabad, Pakistan"). It repeats at the top of every page, and is
  kept off the cover sheet automatically. Leave it empty and pages carry no header.

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


# Coursework is not a research paper, whatever stylesheet it is set in. Someone
# choosing IEEE for an assignment wants IEEE *typography*, not an abstract and a
# reference list nobody asked for — so this follows the document kind, and
# applies independently of the style.
_COURSEWORK_KINDS = (
    "assignment", "homework", "coursework", "lab report", "lab", "practical",
    "problem set", "problem sheet", "exercise", "submission", "worksheet",
    "project report", "semester project",
)

_COURSEWORK_GUIDE = (
    "THIS IS SUBMITTED COURSEWORK, NOT A RESEARCH PAPER — this overrides the style guide "
    "above wherever they disagree.\n"
    "Leave meta.abstract EMPTY (\"\") and meta.keywords empty unless the brief explicitly "
    "asks for an abstract or keywords. Return an EMPTY `references` list unless the brief "
    "asks for references or the work genuinely cites sources. Do not add either merely to "
    "look scholarly: a marker reading an assignment does not expect them, and an abstract "
    "nobody asked for reads as padding.\n"
    "Answer the brief in the brief's own order, using its own names for the parts."
)


def doc_kind_guide(doc_kind: str) -> str:
    """Extra instruction implied by what the document *is*, not how it is set."""
    kind = (doc_kind or "").strip().lower()
    if any(k in kind for k in _COURSEWORK_KINDS):
        return _COURSEWORK_GUIDE
    return ""


def system_prompt(style: str, depth: str = DEFAULT_DEPTH,
                  style_note: Optional[str] = None, doc_kind: str = "document") -> str:
    guide = named_style_guide(style_note) if style_note else _STYLE_GUIDE.get(
        style, _STYLE_GUIDE["report"])
    depth_guide = _DEPTH_GUIDE.get(depth, _DEPTH_GUIDE[DEFAULT_DEPTH])
    return f"{_BASE}\n{guide}\n{depth_guide}\n{doc_kind_guide(doc_kind)}\n"


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
  "references": ["<formatted per the requested style; the entry only — the [1] numbering is added for you>"],
  "visualization_plan": [
    {"data":"<which values in the input>","kind":"bar","rationale":"<why this chart suits them>"}
  ]
}

Rules:
- Choose the sections the material actually supports; do not pad with empty sections.
- Do NOT include an "Abstract" or "References" section in the outline — they are handled
  separately via meta.abstract and references.
- Do NOT plan a section for a screenshot of a program running, a terminal, a website or a
  GUI. Nothing is executed while this document is written, so that section would come out
  empty. Code can be shown as an editor window, and output as a sample-output listing; plan
  those instead, inside the section they belong to.
- Assign each chartable set of values in the material to "visualization_plan", stating what
  the data is, the chart kind, and why. If there are no chartable values, return an empty list.
- Never invent facts, citations or numbers that are absent from the material.
EXTRA INSTRUCTIONS — these are the user's own words and they OVERRIDE the defaults
above. If `extra_instructions` is present in the payload, follow every part of it. It is
not a hint or a preference: a request to bold key terms, keep sections short, use a
particular voice, include or omit something, is binding. Where it conflicts with a default
in this prompt, the user wins. Re-read it before you finish and check you did each thing
it asked.

EMPHASIS — inside any "text" field you may mark emphasis with **bold** and *italic*, and
the renderer turns those into real bold and italic runs. Use them where the user asks for
emphasis, and where a key term genuinely earns it. ("No markdown fences" above is about
the JSON envelope — never wrap the JSON itself in ``` — not about the prose inside it.)
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
- If this section answers part of a brief, answer it in full: derive the mathematics, write
  the code, work the numbers — do not describe what would be done. Real code goes in
  {"type":"code","language":"...","filename":"...","caption":"...","text":"..."} blocks,
  split one listing per function or step with the explanation in between.
- Formulae go in {"type":"equation","text":"..."} as TeX math markup (\\frac, \\sqrt, ^, _,
  \\sum); they are typeset for you. Substitute the real values and show the result.
- Headings are numbered automatically; do not put numbers in heading text.
- Include a table or figure ONLY if this section is the one that should carry it according to
  the visualisation plan you are given, and only using values present in the material.
- Never invent facts, citations or numbers that are absent from the material.
EXTRA INSTRUCTIONS — these are the user's own words and they OVERRIDE the defaults
above. If `extra_instructions` is present in the payload, follow every part of it. It is
not a hint or a preference: a request to bold key terms, keep sections short, use a
particular voice, include or omit something, is binding. Where it conflicts with a default
in this prompt, the user wins. Re-read it before you finish and check you did each thing
it asked.

EMPHASIS — inside any "text" field you may mark emphasis with **bold** and *italic*, and
the renderer turns those into real bold and italic runs. Use them where the user asks for
emphasis, and where a key term genuinely earns it. ("No markdown fences" above is about
the JSON envelope — never wrap the JSON itself in ``` — not about the prose inside it.)
"""


def plan_system_prompt(style: str, depth: str = DEFAULT_DEPTH,
                       style_note: Optional[str] = None, doc_kind: str = "document") -> str:
    guide = named_style_guide(style_note) if style_note else _STYLE_GUIDE.get(
        style, _STYLE_GUIDE["report"])
    depth_guide = _DEPTH_GUIDE.get(depth, _DEPTH_GUIDE[DEFAULT_DEPTH])
    return f"{PLAN_SYSTEM}\n{guide}\n{depth_guide}\n{doc_kind_guide(doc_kind)}\n"


def section_system_prompt(style: str, depth: str = DEFAULT_DEPTH,
                          style_note: Optional[str] = None,
                          doc_kind: str = "document") -> str:
    guide = named_style_guide(style_note) if style_note else _STYLE_GUIDE.get(
        style, _STYLE_GUIDE["report"])
    depth_guide = _DEPTH_GUIDE.get(depth, _DEPTH_GUIDE[DEFAULT_DEPTH])
    return f"{SECTION_SYSTEM}\n{guide}\n{depth_guide}\n{doc_kind_guide(doc_kind)}\n"


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
    }
    # The user's own instructions go FIRST. Buried under the outline and a few
    # thousand words of source material they read as an afterthought, and every
    # section of a multi-pass document inherits the same neglect.
    if instructions:
        payload["extra_instructions"] = instructions
    payload.update({
        "document_title": title,
        "this_section": section,
        "full_outline": [s.get("heading", "") for s in outline],
        "sections_already_written": list(written_so_far),
        "visualization_plan": list(visualization_plan),
        "source_material": raw_text,
    })
    extras = _clean_attachments(attachments)
    if extras:
        payload["additional_material"] = extras
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
    }
    # The user's own instructions go FIRST. Buried under a few thousand words of
    # source material they read as an afterthought and get treated as one.
    if instructions:
        payload["extra_instructions"] = instructions
    payload["source_material"] = raw_text

    # Arbitrary user-labelled material: data, results, code, transcripts, notes,
    # citations — whatever this particular job involves.
    extras = _clean_attachments(attachments)
    if extras:
        payload["additional_material"] = extras

    if reference_example:
        payload["reference_example_to_follow"] = reference_example
    if title_hint:
        payload["title_hint"] = title_hint
    if authors:
        payload["authors"] = authors

    return f"{lead}\n" + json.dumps(payload, indent=2, ensure_ascii=False)


# ── instruction refinement ──────────────────────────────────────────────────
#
# Special instructions are the part users get least help with. They write
# "make it look professional", the writer has nothing actionable to do with
# that, and the result disappoints without anybody being able to say why. This
# pass turns intent into instructions the writer can act on, and — importantly —
# asks rather than guesses when the intent is genuinely unclear.

IMPROVE_SYSTEM = """You refine a person's instructions for a document that is about to be
written. You do NOT write the document.

Return ONLY strict JSON. No markdown fences, no commentary.

{
  "improved": "<the rewritten instructions, ready to hand to the writer>",
  "changes": ["<what you made explicit, one short line each>"],
  "questions": ["<anything you could not settle without them; empty if none>"]
}

Rules:
- Preserve their intent exactly. You are making it precise, not making it yours. Never add a
  requirement they did not ask for, drop one they did, or change what they asked for because
  you would have done it differently.
- Turn a vague wish into something checkable. "Make it look professional" becomes the
  specific things they plausibly mean for this document; "add screenshots" becomes which
  screenshots, of what, and how many.
- Where the brief or material already names a number — five screenshots, three test cases,
  under four pages — carry that number into the instructions rather than leaving "several".
- Keep it in their voice, in plain imperative sentences, one instruction per line. No
  headings, no numbering, no preamble.
- Do not restate the whole task. These are the EXTRA instructions that sit alongside the
  material, not a rewrite of the brief.
- If something is genuinely ambiguous and the answer would change the document, put it in
  "questions" instead of choosing for them. Ask at most three, and only about things that
  matter.
- If their instructions are already clear and specific, say so: return them nearly unchanged
  with an empty or near-empty "changes".
"""


def build_improve_message(
    *,
    instructions: str,
    raw_text: str = "",
    doc_kind: str = "document",
    style: str = "report",
    feedback: Optional[str] = None,
    previous: Optional[str] = None,
) -> str:
    """The refinement request, including any earlier attempt and what the user
    said was wrong with it — which is what makes a second round better than a
    re-roll of the first."""
    payload: dict[str, Any] = {
        "task": "Refine the extra instructions for the document described below.",
        "their_instructions": instructions,
        "document_kind": doc_kind,
        "style": style,
    }
    if previous:
        payload["your_previous_attempt"] = previous
    if feedback:
        payload["their_feedback_on_it"] = feedback
    if raw_text.strip():
        # Trimmed: the refiner needs to know what the document is about, not to
        # re-read every word of it.
        payload["material_excerpt"] = raw_text.strip()[:4000]
    return "Refine these instructions.\n" + json.dumps(payload, indent=2, ensure_ascii=False)
