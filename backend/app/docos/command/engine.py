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
from app.docos.command.prompt import SYSTEM, build_user_message
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
                     reading: Optional[dict[str, str]] = None) -> tuple[ActionBatch, str]:
        router = self._router
        if router is None:
            from app.services.router import get_router
            router = get_router()

        text, provider, _elapsed = router.chat(
            [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": build_user_message(command, graph, reading)},
            ],
            max_tokens=900,
            # A plan is a few hundred bytes of JSON. If it has not arrived in
            # twenty seconds it is not coming, and the heuristic — which answers
            # instantly and handles most requests — is a better use of the wait
            # than another half minute of a still screen.
            timeout=20,
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
        size, relative = _size(c)

        if _WANTS_A_LIST.search(c):
            # Checked before "select", which claims the word "list" and so used
            # to answer "put these in bullets" by selecting something.
            kind = ("none" if _has(c, "remove", "delete", "un-bullet", "unbullet")
                    else "number" if _WANTS_NUMBERING.search(c) else "bullet")
            actions.append(a(type="list", target=target or "body",
                             params={"kind": kind}))
            reasoning = f"{kind} list"
        elif _has(c, "highlight"):
            actions.append(a(type="highlight", target=target or "document",
                             params={"color": _HIGHLIGHT, "find": phrase} if phrase
                             else {"color": _HIGHLIGHT}))
            reasoning = f"highlight {target or 'document'}"
        elif _has(c, "remove", "delete"):
            t = target or ("horizontal_rule" if _has(c, "line", "rule") else "figure")
            actions.append(a(type="delete", target=t))
            reasoning = f"delete {t}"
        elif alignment:
            actions.append(a(type="align", target=target or "body",
                             params={"alignment": alignment}))
            reasoning = f"{alignment} {target or 'body'}"
        elif size is not None or relative:
            # "size 9" says which size; "larger" says which way, and the sizes
            # in the document decide the rest.
            params = {"scale": relative} if relative else {"font_size": size}
            actions.append(a(type="resize", target=target or "body", params=params))
            reasoning = (f"resize {target or 'body'} by {relative}" if relative
                         else f"resize {target or 'body'} to {size}")
        elif _style_asked(c, color):
            # Several at once is an ordinary request — "bold and italic", "red
            # and underlined" — and answering only the first of them was
            # answering half the question.
            style = _style_asked(c, color)
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


def _style_asked(text: str, color: Optional[str]) -> dict[str, Any]:
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


def _size(text: str) -> tuple[Optional[float], Optional[float]]:
    """`(absolute size, relative factor)` — at most one of them."""
    m = re.search(r"\b(?:size|pt|point)\D{0,12}?(\d{1,2}(?:\.\d)?)\b", text, re.IGNORECASE)
    if not m:
        m = re.search(r"\b(\d{1,2}(?:\.\d)?)\s*(?:pt|point)\b", text, re.IGNORECASE)
    if m:
        return float(m.group(1)), None
    if _BIGGER.search(text):
        return None, 1.25
    if _SMALLER.search(text):
        return None, 0.8
    if _SIZE_WORDS.search(text):
        return None, 1.25 if _BIGGER.search(text) else 0.8
    return None, None
