"""Prompt construction for the AI Command Engine.

The model's ONLY job is to translate intent into an action batch. It must return
strict JSON — no prose, no markdown — matching the action schema. The Execution
Engine is the sole mutator, so a hallucinated action can do no harm: it is
validated and rejected before it ever touches the graph.
"""
from __future__ import annotations

import json

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
    "- Prefer targeting by `target` (a node class) over node_ids unless the user names specific nodes.\n"
    "- For 'center images' use align with params.alignment='center'.\n"
    "- For 'justify body' use justify on target 'body'.\n"
    "- For 'change references to font size 10' use resize on target 'reference' with params.font_size=10.\n"
    "- For 'highlight figures' use highlight on target 'figure'.\n"
    "- For 'remove horizontal lines' use delete on target 'horizontal_rule'.\n"
    "- replace requires params.find and params.with.\n"
    "- Only emit fields you need; omit unknown fields.\n"
)


def build_user_message(command: str, graph: DocumentGraph) -> str:
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
    context = {
        "instruction": command,
        "document_node_counts": counts,
        "headings": outline,
        "text_sample": sample,
    }
    return "Produce the JSON action batch for:\n" + json.dumps(context, indent=2)
