"""Prompt construction for the AI Command Engine.

The model's ONLY job is to translate intent into an action batch. It must return
strict JSON — no prose, no markdown — matching the action schema. The Execution
Engine is the sole mutator, so a hallucinated action can do no harm: it is
validated and rejected before it ever touches the graph.
"""
from __future__ import annotations

import json
from typing import Optional

from app.docos.actions import ActionType, TARGETS
from app.docos.graph import DocumentGraph

SYSTEM = (
    "You are the Command Engine of a visual document editor. "
    "Translate the user's natural-language instruction into a STRICT JSON action batch. "
    "Return ONLY JSON. No markdown fences, no explanations, no prose.\n\n"
    "Schema:\n"
    '{ "reasoning": "<one short sentence>", "actions": [ {'
    '"type": <op>, "target": <target|null>, "node_ids": [<ids>], '
    '"style": {"font_size": <num>, "bold": <bool>, "italic": <bool>, "underline": <bool>, '
    '"color": "<hex>", "highlight": "<hex>", "alignment": "left|center|right|justify", '
    '"font_family": "<name>"}, "params": { ... } } ] }\n\n'
    f"Valid ops: {', '.join(sorted(a.value for a in ActionType))}.\n"
    f"Valid targets: {', '.join(sorted(TARGETS))}.\n"
    "Rules:\n"
    "- Prefer targeting by `target` (a node class) when the request is about a class "
    "of thing ('the headings', 'every caption').\n"
    "- When the request is about a PART of the document — a named section, or one "
    "described by what it says ('the part about the evaluation protocol', 'the section "
    "reporting accuracy') — find it in `document.sections`, where each entry carries "
    "`heading`, `about` and the `node_ids` it covers, and use those node_ids. Do not "
    "fall back to a target that merely shares a word with the request.\n"
    "- For 'center images' use align with params.alignment='center'.\n"
    "- For 'justify body' use justify on target 'body'.\n"
    "- For 'change references to font size 10' use resize on target 'reference' with params.font_size=10.\n"
    "- For 'highlight figures' use highlight on target 'figure'.\n"
    "- To format WORDS rather than whole paragraphs — 'bold the word results', "
    "'italicise every mention of MobiAct' — use format with params.find set to "
    "those words. Without params.find the whole paragraph is formatted, which is "
    "not what a request about a phrase means.\n"
    "- If the request DESCRIBES the words rather than quoting them — 'bold the "
    "results', 'italicise the dataset names' — use format with params.describe "
    "set to that description. params.find is for text the user named outright: "
    "'the word results' is find; 'the results' is describe.\n"
    "- 'the headings in the table' means target 'table_header' (the cells of the "
    "table's header row), NOT target 'heading', which is the document's own "
    "section headings.\n"
    "- 'the part about the results' is NOT target 'figure': find the section in "
    "`document.sections` whose `about` or `heading` matches the request and use its "
    "node_ids. A word shared with a target name is not a reason to use that target.\n"
    "- For 'put the contributions in bullets', 'make these a numbered list', use "
    "list with params.kind='bullet' or 'number' on the node_ids concerned. A "
    "bullet is a property of the paragraph, so do NOT rewrite the text to add "
    "dashes or numbers. params.kind='none' takes paragraphs back out of a list.\n"
    "- For 'remove horizontal lines' use delete on target 'horizontal_rule'.\n"
    "- replace requires params.find and params.with.\n"
    "- Only emit fields you need; omit unknown fields.\n"
)


def build_user_message(command: str, graph: DocumentGraph,
                       reading: Optional[dict[str, str]] = None) -> str:
    from app.docos.command.reading import brief_with_reading

    counts: dict[str, int] = {}
    for n in graph.nodes():
        counts[n.type.value] = counts.get(n.type.value, 0) + 1
    outline = [
        {"id": n.id, "type": n.type.value, "text": n.content[:60]}
        for n in graph.nodes()
        if n.type.value in {"heading", "subheading"}
    ][:40]
    # A short sample of the document's own words. The planner does not rewrite
    # anything, but without seeing any prose it cannot tell an instruction about
    # the text from one about the layout.
    sample = [
        n.content[:200]
        for n in graph.nodes()
        if n.type.value in {"body", "paragraph"} and n.content.strip()
    ][:6]
    # What the document is, read from the document itself: what kind of thing it
    # is, how it is divided, what each part holds, and where its maths and
    # citations live. Planning from counts alone is guessing — it could not tell
    # that the equations an instruction names sit in table cells, or which
    # section a request is about.
    context = {
        "instruction": command,
        "document": _for_prompt(brief_with_reading(graph, reading or {})),
        "document_node_counts": counts,
        "headings": outline,
        "text_sample": sample,
    }
    # Compact rather than indented: the indentation of a fifty-section brief
    # is a thousand tokens of whitespace.
    return ("Produce the JSON action batch for:\n"
            + json.dumps(context, separators=(",", ":")))


# How much of a document's structure is worth sending. A long report has fifty
# sections, and listing them all — each with the ids of everything inside it —
# put thirty thousand characters in front of the planner, which is slow, costly,
# and the difference between an answer and a timeout.
_MAX_SECTIONS_IN_PROMPT = 25


def _for_prompt(brief: dict) -> dict:
    """The brief trimmed to what the planner can actually use.

    Node ids are dropped. The planner is no longer what places an instruction
    in a section — `locate.py` does that afterwards, deterministically — so the
    ids were thousands of tokens spent telling it something it is not asked to
    decide.
    """
    sections = brief.get("sections") or []
    trimmed = [{k: v for k, v in section.items() if k != "node_ids"}
               for section in sections[:_MAX_SECTIONS_IN_PROMPT]]

    out = {**brief, "sections": trimmed}
    if len(sections) > len(trimmed):
        out["sections_omitted"] = len(sections) - len(trimmed)
    return out
