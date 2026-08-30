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
    r"|\bitemi[sz]e[ds]?\b|\bdot\s?points?\b|\bpoint\s+form\b",
    re.IGNORECASE)

_WANTS_NEW_WORDS = re.compile(
    r"\b(rewrite|reword|rephrase|paraphrase|convert|change|turn|translate|"
    r"simplify|clarify|shorten|tighten|condense|summari[sz]e|expand|"
    r"proofread|correct|fix)\b", re.IGNORECASE)


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
        c = command.lower()
        target = _guess_target(c)

        def a(**kw: Any) -> dict[str, Any]:
            return kw

        actions: list[dict[str, Any]] = []
        reasoning = "heuristic interpretation"

        if _WANTS_A_LIST.search(c):
            # Checked before "select", which claims the word "list" and so used
            # to answer "put these in bullets" by selecting something.
            numbered = bool(re.search(r"\bnumber(ed)?\b|\bordered\b|\b1[.)]\s", c))
            kind = ("none" if _has(c, "remove", "delete", "un-bullet", "unbullet")
                    else "number" if numbered else "bullet")
            actions.append(a(type="list", target=target or "body",
                             params={"kind": kind}))
            reasoning = f"{kind} list"
        elif _has(c, "select", "find", "show", "list"):
            actions.append(a(type="select", target=target or "heading"))
            reasoning = f"select {target or 'heading'}"
        elif _has(c, "highlight"):
            actions.append(a(type="highlight", target=target or "figure",
                             params={"color": "#fff59d"}))
            reasoning = f"highlight {target or 'figure'}"
        elif _has(c, "remove", "delete"):
            t = target or ("horizontal_rule" if _has(c, "line", "rule") else "figure")
            actions.append(a(type="delete", target=t))
            reasoning = f"delete {t}"
        elif _has(c, "justify"):
            actions.append(a(type="justify", target=target or "body"))
            reasoning = "justify body"
        elif _has(c, "center", "centre"):
            actions.append(a(type="align", target=target or "image",
                             params={"alignment": "center"}))
            reasoning = f"center {target or 'image'}"
        elif _has(c, "font size", "resize", "size"):
            size = _first_number(c) or 10
            actions.append(a(type="resize", target=target or "reference",
                             params={"font_size": size}))
            reasoning = f"resize {target or 'reference'} to {size}"
        elif _has(c, "bold"):
            actions.append(a(type="format", target=target or "heading",
                             style={"bold": True}))
            reasoning = "bold"
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
            # last resort: select whatever target we can infer
            actions.append(a(type="select", target=target or "heading"))
            reasoning = "select (fallback)"

        return validate_batch({"reasoning": reasoning, "actions": actions})


# ── helpers ─────────────────────────────────────────────────────────────────

_TARGET_WORDS = {
    "heading": "heading", "headings": "heading", "subheading": "subheading",
    "title": "heading", "paragraph": "paragraph", "paragraphs": "paragraph",
    "body": "body", "table": "table", "tables": "table", "figure": "figure",
    "figures": "figure", "image": "image", "images": "image", "picture": "image",
    "caption": "caption", "captions": "caption", "reference": "reference",
    "references": "reference", "citation": "reference", "footnote": "footnote",
    "header": "header", "footer": "footer",
    "line": "horizontal_rule", "lines": "horizontal_rule", "rule": "horizontal_rule",
}


def _guess_target(text: str) -> Optional[str]:
    # "the headings in the table" is about the table, not about the document's
    # headings — which is what a plain word-by-word match returned, so the request
    # bolded every section title in the paper and no table at all.
    if (re.search(r"\b(headings?|headers?|titles?)\b", text)
            and re.search(r"\b(tables?)\b", text)):
        return "table_header"

    for word, target in _TARGET_WORDS.items():
        if re.search(rf"\b{re.escape(word)}\b", text):
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
