"""Refining a person's special instructions before the document is written.

Instructions are where a document most often goes wrong, and where the user gets
least feedback: "make it look professional" is a wish, not something a writer can
act on, and the disappointment only shows up in the finished file.

This runs a single short pass that rewrites the instruction into something
checkable, says what it made explicit, and asks about anything genuinely
ambiguous rather than deciding for the user. It is iterative on purpose — the
caller can send the previous attempt back with what was wrong about it, which is
what makes a second round better than a re-roll of the first.
"""
from __future__ import annotations

import threading
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.paper.jsonx import extract_json
from app.paper.prompt import IMPROVE_SYSTEM, build_improve_message

# Short by construction: this rewrites a few lines, it does not write a document.
_MAX_TOKENS = 1200

# Beyond a handful the list stops being a question and becomes an interrogation.
_MAX_QUESTIONS = 3


class RefinedInstructions(BaseModel):
    improved: str = ""
    changes: list[str] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)


class InstructionRefinementError(Exception):
    pass


def refine_instructions(
    *,
    instructions: str,
    raw_text: str = "",
    doc_kind: str = "document",
    style: str = "report",
    feedback: Optional[str] = None,
    previous: Optional[str] = None,
    router: Any = None,
    cancel: Optional[threading.Event] = None,
) -> tuple[RefinedInstructions, str]:
    """Return (refined, provider_used).

    Raises InstructionRefinementError when there is nothing to refine or the
    model gives back something unusable.
    """
    if not (instructions or "").strip():
        raise InstructionRefinementError("no instructions to refine")

    if router is None:
        from app.services.router import get_router
        router = get_router()

    messages = [
        {"role": "system", "content": IMPROVE_SYSTEM},
        {"role": "user", "content": build_improve_message(
            instructions=instructions, raw_text=raw_text, doc_kind=doc_kind,
            style=style, feedback=feedback, previous=previous)},
    ]

    try:
        text, provider, _elapsed = router.chat(messages, max_tokens=_MAX_TOKENS,
                                               cancel=cancel)
    except Exception as exc:
        raise InstructionRefinementError(str(exc)) from exc

    raw = extract_json(text)
    if not raw:
        raise InstructionRefinementError("the model did not return usable JSON")

    refined = RefinedInstructions(
        improved=str(raw.get("improved") or "").strip(),
        changes=_lines(raw.get("changes")),
        questions=_lines(raw.get("questions"))[:_MAX_QUESTIONS],
    )
    if not refined.improved:
        # Nothing usable came back; the caller's own text is still the best copy
        # they have, so say so rather than handing back an empty box.
        raise InstructionRefinementError("the model returned no improved instructions")
    return refined, provider


def _lines(value: Any) -> list[str]:
    """Models return this as a list, sometimes as one newline-joined string."""
    if isinstance(value, str):
        value = value.splitlines()
    if not isinstance(value, list):
        return []
    return [s.strip(" -•\t") for s in (str(v) for v in value) if s.strip(" -•\t")]
