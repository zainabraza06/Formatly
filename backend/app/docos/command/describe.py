"""Saying what was done, in the document's terms.

The panel used to show the planner's `reasoning`, which is a note the planner
writes to itself: "Target the Abstract section's node_ids and apply bold
formatting to the word 'results'". Node ids are an implementation detail of
this program, and a person reading their own document has no use for them —
worse, the sentence describes an intention, so it reads the same whether the
words were bolded or nothing happened at all.

This describes the outcome instead, from the actions that ran and what they
touched, so the line under Done is a fact about the document.
"""
from __future__ import annotations

from typing import Any, Optional

from app.docos.actions import ActionBatch, ActionType

# What each target is called out loud, singular and plural.
_THINGS = {
    "heading": ("heading", "headings"),
    "subheading": ("subheading", "subheadings"),
    "title": ("title", "titles"),
    "body": ("paragraph", "paragraphs"),
    "paragraph": ("paragraph", "paragraphs"),
    "caption": ("caption", "captions"),
    "reference": ("reference", "references"),
    "footnote": ("footnote", "footnotes"),
    "table": ("table", "tables"),
    "table_cell": ("cell", "cells"),
    "table_header": ("table header cell", "table header cells"),
    "figure": ("figure", "figures"),
    "image": ("image", "images"),
    "header": ("page header", "page headers"),
    "footer": ("page footer", "page footers"),
    "horizontal_rule": ("line", "lines"),
    "document": ("place", "places"),
}

# What a node is called out loud, by what it is rather than by what the plan
# aimed at.
_TYPE_NAMES = {
    "heading": ("heading", "headings"),
    "subheading": ("subheading", "subheadings"),
    "body": ("paragraph", "paragraphs"),
    "paragraph": ("paragraph", "paragraphs"),
    "caption": ("caption", "captions"),
    "reference": ("reference", "references"),
    "footnote": ("footnote", "footnotes"),
    "table": ("table", "tables"),
    "table_cell": ("cell", "cells"),
    "table_row": ("row", "rows"),
    "figure": ("figure", "figures"),
    "image": ("image", "images"),
    "header": ("page header", "page headers"),
    "footer": ("page footer", "page footers"),
    "horizontal_rule": ("line", "lines"),
}

_ALIGNMENT_VERBS = {
    "center": "Centred", "left": "Left-aligned",
    "right": "Right-aligned", "justify": "Justified",
}


def describe_outcome(batch: ActionBatch, changed: list[Any],
                     section: Optional[str] = None) -> str:
    """One plain sentence about what changed, or "" if there is nothing to say.

    `changed` is the nodes that actually changed, so the sentence names what
    they are — "4 paragraphs", "12 cells" — rather than the target the plan
    happened to carry, which said "12 tables" for the cells inside one.
    """
    parts = [_one(action, changed) for action in batch.actions]
    said = [p for p in parts if p]
    if not said:
        return ""

    sentence = _join(said)
    # "Set 3 references to 9 pt in References" says it twice. The section is
    # worth naming only when the sentence does not already name that place.
    if section and section.lower() not in sentence.lower():
        sentence += f" in {section}"
    return sentence[0].upper() + sentence[1:] + "."


def _one(action: Any, changed: list[Any]) -> str:
    kind = action.type
    params = action.params or {}
    what = _what(action, changed)

    if kind is ActionType.FORMAT:
        style = action.style.model_dump(exclude_none=True) if action.style else {}
        style.update({k: v for k, v in params.items()
                      if k in ("bold", "italic", "underline", "color")})
        return f"{_style_verb(style)} {what}" if style else f"formatted {what}"
    if kind is ActionType.HIGHLIGHT:
        return f"highlighted {what}"
    if kind is ActionType.ALIGN:
        return f"{_ALIGNMENT_VERBS.get(params.get('alignment', ''), 'aligned')} {what}".lower()
    if kind is ActionType.JUSTIFY:
        return f"justified {what}"
    if kind is ActionType.RESIZE:
        if params.get("delta"):
            step = float(params["delta"])
            return (f"made {what} {_number(abs(step))} pt "
                    f"{'larger' if step > 0 else 'smaller'}")
        if params.get("font_size"):
            return f"set {what} to {_number(params['font_size'])} pt"
        scale = float(params.get("scale") or 1.0)
        return f"made {what} {'larger' if scale > 1 else 'smaller'}"
    if kind is ActionType.LIST:
        wanted = str(params.get("kind") or "bullet").lower()
        if wanted in ("none", "off", "remove", "plain", "paragraph"):
            return f"took the bullets off {what}"
        return f"{'numbered' if wanted.startswith('num') else 'bulleted'} {what}"
    if kind is ActionType.BORDER:
        sides = [str(s).replace("inside_h", "inner horizontal")
                 .replace("inside_v", "inner vertical").replace("_", " ")
                 for s in params.get("sides") or []]
        width = float(params.get("width") or 0)
        if not width:
            return f"took the borders off {what}"
        heavy = "heavy" if width >= 1.0 else "thin"
        if sides:
            return f"drew {heavy} {_join(sides)} borders on {what}, and no others"
        return f"drew {heavy} borders on {what}"
    if kind is ActionType.DELETE:
        return f"deleted {what}"
    if kind is ActionType.REPLACE:
        return f"replaced {params.get('find', 'the text')!r} in {what}"
    if kind is ActionType.REWRITE:
        return f"rewrote {what}"
    if kind is ActionType.RENDER_MATHS:
        return ("drew the equations as mathematics" if params.get("on", True)
                else "put the equations back as they were typed")
    if kind is ActionType.INSERT:
        return "added a paragraph"
    if kind is ActionType.SELECT:
        return f"selected {what}"
    return ""


def _what(action: Any, changed: list[Any]) -> str:
    """The things an action touched, counted and named."""
    spans = [s for s in (action.params or {}).get("spans") or [] if isinstance(s, dict)]
    find = str((action.params or {}).get("find") or "").strip()

    if spans:
        quoted = [f"“{s['text']}”" for s in spans[:3] if s.get("text")]
        more = len(spans) - len(quoted)
        # With a tail to mention, the quotations are separated by commas
        # only — "a, b and c and 3 more" has one "and" too many.
        if more > 0:
            return ", ".join(quoted) + f" and {more} more"
        return _join(quoted)
    if find:
        return f"“{find}”"

    if changed:
        # Named after what they are. Mixed kinds — a heading and the paragraphs
        # under it — are called by the commonest of them.
        kinds: dict[str, int] = {}
        for node in changed:
            kinds[node.type.value] = kinds.get(node.type.value, 0) + 1
        kind = max(kinds, key=lambda k: kinds[k])
        singular, plural = _TYPE_NAMES.get(kind, ("node", "nodes"))
        count = len(changed)
    else:
        singular, plural = _THINGS.get(action.target or "", ("node", "nodes"))
        count = len(action.node_ids)

    if count == 1:
        return f"1 {singular}"
    return f"{count} {plural}" if count else plural


def _style_verb(style: dict[str, Any]) -> str:
    words = []
    if style.get("bold"):
        words.append("bolded")
    if style.get("italic"):
        words.append("italicised")
    if style.get("underline"):
        words.append("underlined")
    if style.get("color"):
        words.append("coloured")
    for attr, undone in (("bold", "unbolded"), ("italic", "un-italicised"),
                         ("underline", "removed the underline from")):
        if style.get(attr) is False:
            words.append(undone)
    return _join(words) or "formatted"


def _join(items: list[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]


def _number(value: Any) -> str:
    number = float(value)
    return str(int(number)) if number == int(number) else str(number)
