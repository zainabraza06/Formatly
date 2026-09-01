"""AI Command Engine — natural language → validated action batch (or control op).

Pipeline:
  1. Detect control intents (undo / redo / rewind / restore / compare) via rules.
  2. Otherwise ask the provider router for a STRICT-JSON action batch.
  3. Validate against the action schema. If the model returns prose or an invalid
     batch, fall back to deterministic heuristics so common commands still work
     offline.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

from app.docos.actions import ActionBatch, ActionValidationError, validate_batch
from app.docos.command.prompt import (SYSTEM, build_short_message,
                                      build_user_message)
from app.docos.graph import DocumentGraph
from app.paper.jsonx import extract_json


@dataclass
class ControlOp:
    kind: str                       # undo | redo | rewind | restore | compare
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class CommandResult:
    kind: str                       # "actions" | "control"
    batch: Optional[ActionBatch] = None
    control: Optional[ControlOp] = None
    provider: str = ""              # which LLM answered (or "heuristic")
    source: str = ""                # llm | heuristic | rule
    # Why the planner was not used, when it was not. Empty on the happy path.
    fell_back_because: str = ""


# Verbs that ask for different words rather than a different appearance. A
# request built from these cannot be satisfied by any formatting action.
# Asking for a list, in the several ways people ask for one.
_WANTS_A_LIST = re.compile(
    r"\bbullet(?:s|ed|ted|-?point(?:s|ed)?)?\b"
    r"|\b(?:numbered|ordered|unordered|bulleted)\s+list\b"
    r"|\b(?:as|in|into)\s+(?:a\s+)?(?:numbered\s+|bulleted\s+)?list\b"
    r"|\blist(?:ed)?\s+(?:them|these|it|form|format)\b"
    r"|\bitemi[sz]e[ds]?\b|\bdot\s?points?\b|\bpoint\s+form\b"
    # "Number the recommendations" is a request for a list, with the list left
    # unsaid. "The number of parcels" is not, which is why the word has to be
    # doing the work of a verb here.
    r"|\bnumber\s+(?:the|these|those|all|each|every|them)\b",
    re.IGNORECASE)

_WANTS_NEW_WORDS = re.compile(
    r"\b(rewrite|reword|rephrase|paraphrase|convert|change|turn|translate|"
    r"simplify|clarify|shorten|tighten|condense|summari[sz]e|expand|"
    r"proofread|correct|fix|"
    # Case and wording changes are changes to the text, not to its style. A
    # request to capitalise something used to fall past every branch and be
    # answered with a selection.
    r"capitali[sz](?:e[sd]?|ing)|uppercase|lowercase|title\s?case|sentence\s?case|"
    r"abbreviate|spell\s+out|renumber|reorder|number)\b", re.IGNORECASE)


# How long to wait for a plan before answering from the rules instead. Long
# enough for a model to read a long paper's brief, short enough that a provider
# which has gone quiet does not hold up the request.
_PLANNER_SECONDS = 40


class CommandEngine:
    def __init__(self, router: Any = None):
        self._router = router  # injected; defaults to app.services.router.get_router()

    def parse(self, command: str, graph: DocumentGraph,
              reading: Optional[dict[str, str]] = None) -> CommandResult:
        """`reading` is what a pass over the document found each section to be
        about, so an instruction naming a part of the document can be placed."""
        control = self._detect_control(command)
        if control is not None:
            return CommandResult(kind="control", control=control, source="rule")

        # LLM path
        try:
            batch, provider = self._llm_actions(command, graph, reading)
            return CommandResult(kind="actions", batch=batch, provider=provider, source="llm")
        except Exception as exc:
            # Why the planner was not used travels with the result. Swallowing
            # it turned a mistake in this file — a name that did not exist —
            # into every command quietly dropping to the heuristic, which no
            # one could see from the outside.
            reason = f"{type(exc).__name__}: {exc}"

        # A second, cheaper attempt before giving up on understanding the
        # words. The first carries the whole document's brief — two thousand
        # tokens for a long paper — and that is what times out under load; the
        # instruction itself is twenty. Asking again with the instruction alone
        # is quick enough to succeed where the full request did not, and it
        # still reads English, which the rules below do not: they match words,
        # so "squash the gap between paragraphs" is a different request to them
        # than "reduce the space between paragraphs", and it should not be.
        try:
            batch, provider = self._llm_actions(command, graph, reading, briefly=True)
            return CommandResult(kind="actions", batch=batch, provider=provider,
                                 source="llm-brief", fell_back_because=reason)
        except Exception as exc:
            reason += f"; brief attempt: {type(exc).__name__}: {exc}"

        batch = self._heuristic_actions(command)
        return CommandResult(kind="actions", batch=batch, provider="heuristic",
                             source="heuristic", fell_back_because=reason)

    # ── control intents ───────────────────────────────────────────────────
    def _detect_control(self, command: str) -> Optional[ControlOp]:
        c = command.strip().lower()
        if re.fullmatch(r"undo\.?", c):
            return ControlOp("undo")
        if re.fullmatch(r"redo\.?", c):
            return ControlOp("redo")
        m = re.search(r"rewind (?:to )?version (\d+)", c)
        if m:
            return ControlOp("rewind", {"seq": int(m.group(1))})
        m = re.search(r"restore (?:to )?version (\d+)", c)
        if m:
            return ControlOp("restore", {"seq": int(m.group(1))})
        m = re.search(r"compare versions? (\d+) (?:and|to|with) (\d+)", c)
        if m:
            return ControlOp("compare", {"a": int(m.group(1)), "b": int(m.group(2))})
        return None

    # ── LLM path ──────────────────────────────────────────────────────────
    def _llm_actions(self, command: str, graph: DocumentGraph,
                     reading: Optional[dict[str, str]] = None,
                     briefly: bool = False) -> tuple[ActionBatch, str]:
        """The instruction as an action batch.

        `briefly` sends the instruction without the document's brief. It cannot
        place a request in a named section — nothing tells it what the sections
        are — but it can still tell a border from a bullet from a rewrite,
        which is the part the rules are worst at.
        """
        router = self._router
        if router is None:
            from app.services.router import get_router
            router = get_router()

        message = (build_short_message(command, graph) if briefly
                   else build_user_message(command, graph, reading))
        text, provider, _elapsed = router.chat(
            [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": message},
            ],
            max_tokens=900,
            # A plan is a few hundred bytes of JSON, but the document it is
            # planned against is not: a long paper's brief takes the model ten
            # or twenty seconds to read before it writes anything. Twenty
            # seconds was cutting off plans that were on their way, and a
            # request answered by the rules when the planner had understood it
            # is a worse outcome than a few more seconds of waiting.
            timeout=_PLANNER_SECONDS,
        )
        raw = _extract_json(text)
        if raw is None:
            raise ValueError("model did not return JSON")
        batch = validate_batch(raw)  # raises ActionValidationError if bad
        return batch, provider

    # ── deterministic heuristics ──────────────────────────────────────────
    def _heuristic_actions(self, command: str) -> ActionBatch:
        """What the request means, worked out from the words alone.

        This runs whenever the planner cannot be reached, which on a bad day is
        every request — so it is not a token fallback. It is expected to carry
        out ordinary instructions on its own: the appearance of a class of
        thing, of a named part, or of a phrase wherever it occurs.
        """
        c = command.lower()
        target = _guess_target(c)
        # A phrase the request quotes or names outright. It decides the scope
        # as much as the verb does: "bold Midlands wherever it appears" is not
        # about headings, and formatting a class of node instead formatted the
        # wrong things and missed the word where it actually was.
        phrase = _named_phrase(command)
        scoped = target if (target or not phrase) else "document"

        def a(**kw: Any) -> dict[str, Any]:
            return kw

        def formatting(style: dict[str, Any], default: str) -> dict[str, Any]:
            params = {"find": phrase} if phrase else {}
            return a(type="format", target=scoped or default,
                     style=style, params=params)

        actions: list[dict[str, Any]] = []
        reasoning = "heuristic interpretation"

        alignment = _alignment(c)
        color = _color(c)
        font = _font_family(command)
        size, relative, step = _size(c)

        if (case_kind := _case_wanted(c)):
            actions.append(a(type="case", target=target or "document",
                             params={"kind": case_kind}))
            reasoning = f"{case_kind} case"
        elif (spacing := _spacing_wanted(c)):
            # "Line spacing" says line, and "line" on its own means the rules
            # drawn across a page — which is not what a spacing request is about.
            where = target if target != "horizontal_rule" else None
            actions.append(a(type="spacing", target=where or "body", params=spacing))
            reasoning = f"spacing {spacing}"
        elif _ABOUT_BORDERS.search(c):
            sides, width = _borders_wanted(c)
            # Whatever noun was matched, a border request is about a table:
            # "lines" alone resolves to the document's horizontal rules.
            actions.append(a(type="border",
                             target=target if target in ("table", "table_cell",
                                                         "table_header") else "table",
                             params={"sides": sides, "width": width}))
            reasoning = ("borders off" if width == 0 else
                         f"{' and '.join(sides) or 'all'} borders")
        elif _WANTS_A_LIST.search(c):
            # Checked before "select", which claims the word "list" and so used
            # to answer "put these in bullets" by selecting something.
            kind = ("none" if _has(c, "remove", "delete", "un-bullet", "unbullet")
                    else "number" if _WANTS_NUMBERING.search(c) else "bullet")
            actions.append(a(type="list", target=target or "body",
                             params={"kind": kind}))
            reasoning = f"{kind} list"
        elif _has(c, "highlight"):
            if _has(c, "remove", "delete", "clear", "no highlight", "without"):
                # Taking it off is asked for as often as putting it on, and
                # highlighting in the same colour was answering the opposite.
                actions.append(formatting({"highlight": ""}, "document"))
                reasoning = "remove the highlighting"
                return validate_batch({"reasoning": reasoning, "actions": actions})
            actions.append(a(type="highlight", target=target or "document",
                             params={"color": _HIGHLIGHT, "find": phrase} if phrase
                             else {"color": _HIGHLIGHT}))
            reasoning = f"highlight {target or 'document'}"
        elif _has(c, "remove", "delete"):
            t = target or ("horizontal_rule" if _has(c, "line", "rule") else "figure")
            if not target and _ABOUT_CHARACTERS.search(c):
                # "Remove the double spaces" is about characters in the text.
                # Falling through to a node type deleted the figures.
                actions.append(a(type="rewrite", target="document",
                                 params={"instruction": command.strip()}))
                reasoning = "take out what the instruction names"
                return validate_batch({"reasoning": reasoning, "actions": actions})
            if phrase:
                # "Delete the phrase X" takes out the words, not the paragraph
                # they are in.
                actions.append(a(type="replace", target=scoped or "document",
                                 params={"find": phrase, "with": ""}))
                reasoning = f"remove {phrase!r}"
            elif t in ("paragraph", "body"):
                # "Delete the second paragraph" names one, and this cannot tell
                # which — and a delete of every paragraph is refused by the
                # schema, so emitting one crashed the request rather than
                # answering it. The rewriter is shown the text and can take out
                # what the instruction names.
                actions.append(a(type="rewrite", target=t,
                                 params={"instruction": command.strip()}))
                reasoning = "remove what the instruction names"
            else:
                actions.append(a(type="delete", target=t))
                reasoning = f"delete {t}"
        elif alignment:
            actions.append(a(type="align", target=target or "body",
                             params={"alignment": alignment}))
            reasoning = f"{alignment} {target or 'body'}"
        elif size is not None or relative or step:
            # "size 9" says which size; "by 2" says how much to add to whatever
            # each thing already is; "larger" says only which way, and the sizes
            # in the document decide the rest.
            if step:
                params, said = {"delta": step}, f"by {step:+g} pt"
            elif relative:
                params, said = {"scale": relative}, f"by {relative}"
            else:
                params, said = {"font_size": size}, f"to {size}"
            actions.append(a(type="resize", target=target or "body", params=params))
            reasoning = f"resize {target or 'body'} {said}"
        elif _style_asked(c, color, font):
            # Several at once is an ordinary request — "bold and italic", "red
            # and underlined" — and answering only the first of them was
            # answering half the question.
            style = _style_asked(c, color, font)
            actions.append(formatting(style, "heading"))
            reasoning = ", ".join(f"{k}={v}" for k, v in style.items())
        elif _has(c, "select", "find", "show", "list"):
            actions.append(a(type="select", target=target or "heading"))
            reasoning = f"select {target or 'heading'}"
        elif _WANTS_NEW_WORDS.search(c):
            # A request to change what the text says, which no amount of
            # formatting can do. The instruction is carried through as the user
            # wrote it and resolved against the real text later; selecting
            # something instead is how "convert the equations" came back Done
            # with every equation still in place.
            # A target is required by the schema; the service widens it to the
            # whole document anyway unless the request named a part of it.
            actions.append(a(type="rewrite", target=target or "body",
                             params={"instruction": command.strip()}))
            reasoning = "rewrite the text as asked"
        else:
            # An instruction this file has no rule for. It is still an
            # instruction: the user asked for something to change, and answering
            # with a selection changes nothing while looking like success. The
            # request goes to the rewriter instead, which is shown the real text
            # and told to leave alone whatever the instruction does not cover —
            # so an unrecognised request is attempted rather than dismissed.
            actions.append(a(type="rewrite", target=target or "body",
                             params={"instruction": command.strip()}))
            reasoning = "carry out the request against the text"

        return validate_batch({"reasoning": reasoning, "actions": actions})


# ── helpers ─────────────────────────────────────────────────────────────────

_TARGET_WORDS = {
    "heading": "heading", "headings": "heading",
    "subheading": "subheading", "subheadings": "subheading",
    "sub-heading": "subheading", "sub-headings": "subheading",
    "subsection": "subheading", "subsections": "subheading",
    "title": "title", "titles": "heading", "paragraph": "paragraph", "paragraphs": "paragraph",
    "body": "body", "table": "table", "tables": "table", "figure": "figure",
    "figures": "figure", "image": "image", "images": "image", "picture": "image",
    "caption": "caption", "captions": "caption", "reference": "reference",
    "references": "reference", "citation": "reference", "footnote": "footnote",
    "header": "header", "footer": "footer",
    "line": "horizontal_rule", "lines": "horizontal_rule", "rule": "horizontal_rule",
}

# Which noun wins when a request mentions more than one of them.
_TARGET_ORDER = (
    "caption", "reference", "footnote", "horizontal_rule", "page_break",
    "title",
    "header", "footer", "image", "figure", "subheading", "heading",
    "table", "body", "paragraph",
)


def _guess_target(text: str) -> Optional[str]:
    # "the headings in the table" is about the table, not about the document's
    # headings — which is what a plain word-by-word match returned, so the request
    # bolded every section title in the paper and no table at all.
    if (re.search(r"\b(headings?|headers?|titles?)\b", text)
            and re.search(r"\b(tables?)\b", text)):
        return "table_header"

    # Most specific first. "Centre the table 1 caption" mentions both a table
    # and a caption, and taking whichever came first in the map centred the
    # table — a request about a caption is about the caption, whatever it is a
    # caption of.
    for target in _TARGET_ORDER:
        for word, mapped in _TARGET_WORDS.items():
            if mapped == target and re.search(rf"\b{re.escape(word)}\b", text):
                return target
    return None


def _has(text: str, *words: str) -> bool:
    return any(w in text for w in words)


def _first_number(text: str) -> Optional[float]:
    m = re.search(r"\d+(?:\.\d+)?", text)
    return float(m.group(0)) if m else None


def _extract_json(text: str) -> Optional[dict[str, Any]]:
    """First JSON object in the model's reply, fences and truncation tolerated."""
    return extract_json(text)


# The words for each way of asking, kept beside the rule that reads them.

# Numbering rather than bullets. "1 2 3" is how people write it out.
_WANTS_NUMBERING = re.compile(
    r"\bnumber(ed|ing)?\b|\bordered\b|\benumerate\b|\b1[.,)]?\s*2[.,)]?\s*3\b",
    re.IGNORECASE)

_ALIGNMENTS = (
    ("justify", r"\bjustif(y|ied|ication)\b"),
    ("center", r"\b(cent(er|re)(ed|ing)?)\b"),
    ("right", r"\bright[- ]?align(ed|ment)?\b|\balign(ed)?\s+(to\s+the\s+)?right\b|\bflush\s+right\b"),
    ("left", r"\bleft[- ]?align(ed|ment)?\b|\balign(ed)?\s+(to\s+the\s+)?left\b|\bflush\s+left\b"),
)

# Colours by name, because a request says "green", not "#2e7d32". Word's own
# palette is close enough to these that a document keeps looking like itself.
_COLORS = {
    "black": "#000000", "white": "#ffffff", "grey": "#666666", "gray": "#666666",
    "red": "#c00000", "green": "#2e7d32", "blue": "#1f4e79", "navy": "#1f3864",
    "yellow": "#bf9000", "orange": "#c55a11", "purple": "#7030a0", "brown": "#833c00",
}

_HIGHLIGHT = "#fff59d"

# By how much "larger" and "smaller" change a size. A step people would call a
# step: enough to see, not enough to reflow the document.
_BIGGER = re.compile(r"\b(bigger|larger|large|increase|grow|enlarge|up)\b", re.IGNORECASE)
_SMALLER = re.compile(r"\b(smaller|small|reduce|decrease|shrink|down|tiny)\b", re.IGNORECASE)
_SIZE_WORDS = re.compile(r"\b(font\s*size|point\s*size|size|resize|pt\b)", re.IGNORECASE)

# A phrase the request names outright, rather than describing. The quotation
# marks, or the words "the word"/"every mention of", are the user saying
# "these exact characters".
_PHRASE_PATTERNS = (
    re.compile(r"[\"“']([^\"”']{1,80})[\"”']"),
    re.compile(r"\b(?:the\s+)?(?:word|phrase|term|name|acronym)s?\s+"
               r"[\"“']?([A-Za-z0-9][^\"”',.;:]{0,60}?)[\"”']?"
               r"(?=\s+(?:wherever|everywhere|where|in|throughout|across|"
               r"appears?|occurs?|is|are)\b|[,.;:]|$)", re.IGNORECASE),
    re.compile(r"\bevery\s+(?:mention|instance|occurrence|use)\s+of\s+"
               r"[\"“']?([^\"”',.;:]{1,60}?)[\"”']?(?=\s+in\b|[,.;:]|$)",
               re.IGNORECASE),
)


def _named_phrase(command: str) -> str:
    """The exact words a request quotes, if it quotes any."""
    for pattern in _PHRASE_PATTERNS:
        m = pattern.search(command)
        if m:
            phrase = m.group(1).strip()
            if phrase and len(phrase.split()) <= 8:
                return phrase
    return ""


def _style_asked(text: str, color: Optional[str],
                 font: Optional[str] = None) -> dict[str, Any]:
    """Everything about appearance the request asks for, in one patch."""
    style: dict[str, Any] = {}
    if _has(text, "bold"):
        style["bold"] = True
    if _has(text, "italic", "italicis", "italiciz", "slanted"):
        style["italic"] = True
    if _has(text, "underlin"):
        style["underline"] = True
    # Taking formatting off is asked for as often as putting it on.
    for attr, word in (("bold", "bold"), ("italic", "italic"), ("underline", "underlin")):
        if re.search(rf"\b(not|no longer|un|remove|without|drop|stop)\s*{word}", text):
            style[attr] = False
    if color:
        style["color"] = color
    if font:
        style["font_family"] = font
    return style


def _alignment(text: str) -> Optional[str]:
    for name, pattern in _ALIGNMENTS:
        if re.search(pattern, text, re.IGNORECASE):
            return name
    # "Align the captions to the left" puts words between the verb and the
    # side. Once a request says align, the side it names is the answer.
    if re.search(r"\balign(ed|ment|ing)?\b|\bflush\b|\branged\b", text, re.IGNORECASE):
        for side in ("right", "left"):
            if re.search(rf"\b{side}\b", text, re.IGNORECASE):
                return side
    return None


def _color(text: str) -> Optional[str]:
    if not re.search(r"\bcolou?r|\btext\s+colou?r|\bin\s+(?=\w+\b)", text, re.IGNORECASE):
        # A colour word on its own ("make the title blue") still counts; the
        # guard is only here so "the green transition" is not a colour request.
        if not re.search(r"\b(make|turn|set|paint)\b", text, re.IGNORECASE):
            return None
    for name, value in _COLORS.items():
        if re.search(rf"\b{name}\b", text, re.IGNORECASE):
            return value
    return None


def _size(text: str) -> tuple[Optional[float], Optional[float], Optional[float]]:
    """`(absolute size, relative factor, step in points)` — at most one of them.

    "Increase the headings by 2" names a step, not a size. Reading it as a size
    set every heading to 2 pt, which is unreadable and the opposite of what was
    asked, so the step is looked for first: a number a request is *adding* is
    never the size it wants.
    """
    step = _step(text)
    if step is not None:
        return None, None, step

    m = re.search(r"\b(?:size|pt|point)\D{0,12}?(\d{1,2}(?:\.\d)?)\b", text, re.IGNORECASE)
    if not m:
        m = re.search(r"\b(\d{1,2}(?:\.\d)?)\s*(?:pt|point)\b", text, re.IGNORECASE)
    if m:
        return float(m.group(1)), None, None
    if _BIGGER.search(text):
        return None, 1.25, None
    if _SMALLER.search(text):
        return None, 0.8, None
    if _SIZE_WORDS.search(text):
        return None, 1.25 if _BIGGER.search(text) else 0.8, None
    return None, None, None


# "by 2", "by 2 points", "2 units bigger", "+2" — a number being added to the
# size the text already has, whatever the document's sizes happen to be.
_BY_STEP = re.compile(
    r"\bby\s+(\d{1,2}(?:\.\d)?)\s*(?:pt|points?|units?|sizes?|steps?)?\b"
    r"|\b(\d{1,2}(?:\.\d)?)\s*(?:pt|points?|units?)\s+(?:bigger|larger|smaller|more|less)\b"
    r"|(?<![\w.])\+\s*(\d{1,2}(?:\.\d)?)\b",
    re.IGNORECASE)

_GOES_DOWN = re.compile(r"\b(smaller|reduce|decrease|shrink|down|less|lower)\b",
                        re.IGNORECASE)


def _step(text: str) -> Optional[float]:
    """How much bigger or smaller, in points, when a request says by how much."""
    if not re.search(r"\b(increase|decrease|raise|lower|reduce|grow|shrink|bigger|"
                     r"larger|smaller|bump|more|less|up|down|by)\b", text, re.IGNORECASE):
        return None
    m = _BY_STEP.search(text)
    if not m:
        return None
    value = float(next(g for g in m.groups() if g))
    return -value if _GOES_DOWN.search(text) else value


# The words that say a request is about a table. "Rules" and "lines" mean a
# table's edges only in their company — otherwise they are the rules drawn
# across a page, which is a different request.
_TABLE_CONTEXT = r"\b(?:tables?|header\s+rows?|cells?|columns?|grid)\b"

# A request about a table's rules rather than its text.
_ABOUT_BORDERS = re.compile(
    r"\bborders?\b|\bgridlines?\b"
    # "Lines" and "rules" mean a table's edges only when a table is being
    # talked about. Without that, "remove the horizontal lines" is about the
    # rules drawn across the page, which is a different request entirely.
    r"|\b(?:lines?|rules?)\b(?=.*" + _TABLE_CONTEXT + r")"
    r"|" + _TABLE_CONTEXT + r"(?=.*\b(?:lines?|rules?)\b)",
    re.IGNORECASE)

# Which edges, named the several ways people name them.
_SIDE_WORDS = (
    # The rule under the heading row, which a paper draws and Word has no
    # table-level word for. Checked before "top": "the header border" is the
    # line under the headings, and the line above them is the top.
    ("header", r"\bheader\s*(?:row|cells?|line|rule|border)?\b|\bunder\s+the\s+head"),
    ("top", r"\b(top|upper|above)\b"),
    ("bottom", r"\b(bottom|lower|below|last)\b"),
    ("left", r"\bleft\b"),
    ("right", r"\bright\b"),
    ("outside", r"\b(outer|outside|around|perimeter)\b"),
    ("inside", r"\b(inner|inside|internal|between)\b"),
    # "Rows", plural, is the lines between them; "the header row" is one row
    # and names no such line.
    ("inside_h", r"\b(horizontal|rows)\b"),
    ("inside_v", r"\b(vertical|columns?)\b"),
)

# How heavy a line "bold" or "thick" asks for, in points, against the ordinary
# half-point rule Word draws by default.
_HEAVY_LINE = 1.5
_THIN_LINE = 0.5


def _borders_wanted(text: str) -> tuple[list[str], float]:
    """`(the edges to draw, the width in points)`. No edges named means all.

    A request often says both halves at once — "keep only the top and bottom
    borders, removing the left and right" — and reading it as one list kept
    all four. The sentence is cut at the word that turns it: what is named
    before is kept, what is named after is taken away.
    """
    head, tail, removes = _split_at_removal(text)
    keep = _sides_in(head)
    drop = _sides_in(tail)

    heavy = re.search(r"\b(bold|thick|heavy|strong|double|dark)\b", text, re.IGNORECASE)
    width = _HEAVY_LINE if heavy else _THIN_LINE

    if keep:
        # What it asked to keep is the whole answer: naming some sides means
        # those and no others, so whatever it also asked to remove is gone.
        return _every_row(head, keep), width
    if drop:
        # Only a removal: everything else stays, at the width it would have.
        return _keep_others(drop), _THIN_LINE
    if removes:
        # "Remove the borders", naming no side at all.
        return [], 0.0
    # No side named and nothing removed: the request is about all of them.
    return [], width


def _every_row(text: str, keep: list[str]) -> list[str]:
    """Whether "top and bottom" means the table's or every row's.

    A table has one top and one bottom; a row has one each as well. "Keep the
    top and bottom borders" on a ten-row table drew two rules around the whole
    thing, and "all the top and bottom borders" means the line above and below
    each row — which is a ruled table, and a different request.
    """
    if "inside_h" in keep and re.search(r"\bhorizontal\b", text, re.IGNORECASE):
        # "Horizontal borders" is every horizontal line there is, the outermost
        # two included.
        return sorted(set(keep) | {"top", "bottom"})
    if {"top", "bottom"} <= set(keep) and re.search(
            r"\b(all|every|each)\b", text, re.IGNORECASE):
        return sorted(set(keep) | {"inside_h"})
    return keep


def _sides_in(text: str) -> list[str]:
    return [name for name, pattern in _SIDE_WORDS
            if re.search(pattern, text, re.IGNORECASE)]


# The word that turns a sentence from what to keep into what to take away.
_TURNS = re.compile(
    r"\b(?:remov\w*|delet\w*|drop\w*|hid\w*|without|except|but\s+not|minus|"
    r"no|none|clear\w*|off)\b",
    re.IGNORECASE)


def _split_at_removal(text: str) -> tuple[str, str, bool]:
    """`(what is kept, what is taken away, whether anything is)`."""
    m = _TURNS.search(text)
    if not m:
        return text, "", False
    return text[:m.start()], text[m.end():], True


_BORDER_ALL = ("top", "bottom", "left", "right", "inside_h", "inside_v")


def _expand(sides: list[str]) -> list[str]:
    out: list[str] = []
    for side in sides:
        if side == "outside":
            out += ["top", "bottom", "left", "right"]
        elif side == "inside":
            out += ["inside_h", "inside_v"]
        else:
            out.append(side)
    return out


def _keep_others(sides: list[str]) -> list[str]:
    """The edges left after the named ones are taken away."""
    gone = set(_expand(sides))
    return [s for s in _BORDER_ALL if s not in gone]


# Word calls this Change Case, and does it without asking anyone.
_CASE_WORDS = (
    ("upper", r"\b(upper[- ]?case|all[- ]?caps|capital letters|in caps|shout)\b"),
    ("lower", r"\b(lower[- ]?case|small letters|no caps)\b"),
    ("sentence", r"\bsentence[- ]?case\b"),
    ("title", r"\b(title[- ]?case|capitali[sz]e each word|capitali[sz]ed?|capitali[sz]ation)\b"),
)


def _case_wanted(text: str) -> Optional[str]:
    """Which case a request asks for, if it asks for one."""
    for kind, pattern in _CASE_WORDS:
        if re.search(pattern, text, re.IGNORECASE):
            return kind
    return None


# Line spacing, and the gaps above and below a paragraph. The document has
# carried all three since it was imported and nothing could ask for them.
_NAMED_SPACING = (
    (2.0, r"\bdouble[- ]?spac"),
    (1.5, r"\bone and a half\b|\b1\.5\s*(?:line\s*)?spac"),
    (1.0, r"\bsingle[- ]?spac"),
)


def _spacing_wanted(text: str) -> Optional[dict[str, float]]:
    # "Remove double spaces" is about two space characters in a row, not about
    # the distance between lines, and setting the document double-spaced is the
    # opposite of what it asks.
    if re.search(r"\b(remove|delete|strip|collapse)\b.{0,20}\bspaces\b", text, re.IGNORECASE):
        return None
    for value, pattern in _NAMED_SPACING:
        if re.search(pattern, text, re.IGNORECASE):
            return {"line": value}

    m = re.search(r"\bline\s*spacing\s*(?:of|to|=)?\s*(\d(?:\.\d+)?)\b", text, re.IGNORECASE)
    if m:
        return {"line": float(m.group(1))}

    # "More space between paragraphs" is about the gap, not the lines.
    if re.search(r"\bspac(?:e|ing)\b.*\bbetween\b|\bbetween\b.*\bparagraphs?\b", text, re.IGNORECASE):
        m = re.search(r"(\d{1,2}(?:\.\d)?)\s*(?:pt|points?)", text, re.IGNORECASE)
        points = float(m.group(1)) if m else 12.0
        if re.search(r"\b(less|reduce|decrease|tighten|remove|no)\b", text, re.IGNORECASE):
            points = 0.0
        return {"after_pt": points}
    return None


# A typeface the request names outright.
_FONT_NAMES = ("times new roman", "times", "arial", "calibri", "helvetica",
               "cambria", "georgia", "garamond", "verdana", "courier new",
               "courier", "palatino", "book antiqua", "computer modern")


def _font_family(text: str) -> Optional[str]:
    if not re.search(r"\b(font|typeface|typeset|set)\b", text, re.IGNORECASE):
        return None
    for name in _FONT_NAMES:
        if name in text.lower():
            return name.title()
    m = re.search(r"\bfont\s+(?:to|as|into)\s+([A-Za-z][A-Za-z ]{2,28})", text, re.IGNORECASE)
    return m.group(1).strip().title() if m else None


# Things a request can ask to remove that are characters rather than parts of
# the document. Without this "remove the double spaces" deleted the figures.
_ABOUT_CHARACTERS = re.compile(
    r"\bspaces?\b|\bwhitespace\b|\bblank\b|\btabs?\b|\bduplicate\b"
    r"|\bextra\b|\btypos?\b|\bcommas?\b|\bfull stops?\b|\bpunctuation\b",
    re.IGNORECASE)
