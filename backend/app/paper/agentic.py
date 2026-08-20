"""Multi-pass ("agentic") document generation.

A single call cannot write a genuinely detailed document. Measured against
mistral-large: asked for depth, it runs past an 8000-token ceiling, finishes with
`finish_reason=length`, and the JSON truncates mid-structure — so the *whole*
document is lost, not merely its tail.

Naively continuing the raw token stream does not fix that: a cut lands inside the
JSON, and asking a model to resume mid-structure is unreliable — it re-opens
braces, restarts, or drifts. There is nothing valid to parse until the end.

So depth is produced in passes over *document structure* rather than tokens:

    plan  ──▶ meta + section outline + references + visualisation plan   (1 call)
    write ──▶ each section on its own, given the plan for coherence      (N calls)
    assemble ─▶ one PaperSpec

Every call returns small, complete, validatable JSON, the document can be
arbitrarily long, and a single failed section degrades that section instead of
destroying the document.
"""
from __future__ import annotations

import threading
from typing import Any, Callable, Optional, Sequence

from app.paper.jsonx import extract_json
from app.paper.prompt import (
    build_plan_message, build_section_message, plan_system_prompt, section_system_prompt,
)
from app.paper.schema import Block, PaperSpec
from app.services.router import GenerationCancelled

# Budgets per pass. Each is generous for its job yet far below any ceiling,
# which is the entire point of splitting the work up.
_PLAN_TOKENS = 2000
_SECTION_TOKENS = 3000

# A progress callback so callers (API, CLI) can report which pass is running.
Progress = Callable[[str, int, int], None]


class SectionFailure(Exception):
    """A single section could not be written. The document survives without it."""


def generate_sectioned(
    *,
    raw_text: str,
    style_guide: str,
    depth: str,
    doc_kind: str,
    router: Any,
    attachments: Optional[Sequence[dict[str, str]]] = None,
    reference_example: Optional[str] = None,
    instructions: Optional[str] = None,
    title_hint: Optional[str] = None,
    authors: Optional[list[dict[str, str]]] = None,
    on_progress: Optional[Progress] = None,
    style_note: Optional[str] = None,
    cancel: Optional[threading.Event] = None,
) -> tuple[dict[str, Any], str]:
    """Returns (raw_spec_dict, provider_used). Raises if the plan pass fails."""
    plan, provider = _plan(
        raw_text=raw_text, style_guide=style_guide, depth=depth, doc_kind=doc_kind,
        router=router, attachments=attachments, reference_example=reference_example,
        instructions=instructions, title_hint=title_hint, authors=authors,
        style_note=style_note, cancel=cancel,
    )

    outline: list[dict[str, Any]] = [s for s in plan.get("outline", []) if s.get("heading")]
    if not outline:
        raise ValueError("planning pass produced no outline")

    meta = plan.get("meta", {}) or {}
    viz = plan.get("visualization_plan", []) or []

    blocks: list[dict[str, Any]] = []
    written: list[str] = []
    total = len(outline)

    for i, section in enumerate(outline, start=1):
        # Checked between passes as well as inside them: a multi-pass document
        # is many calls, and the cheapest one to cancel is the one not yet made.
        if cancel is not None and cancel.is_set():
            raise GenerationCancelled()
        heading = section.get("heading", "")
        if on_progress:
            on_progress(heading, i, total)
        try:
            section_blocks = _write_section(
                section=section, outline=outline, title=meta.get("title", ""),
                viz=viz, written=written, raw_text=raw_text, style_guide=style_guide,
                depth=depth, router=router, attachments=attachments,
                instructions=instructions, style_note=style_note, cancel=cancel,
            )
        except GenerationCancelled:
            raise
        except SectionFailure:
            # Keep the section present with its heading rather than silently
            # dropping it — a visible gap beats a document that quietly lies
            # about its own structure.
            section_blocks = [{"type": "heading", "level": 1, "text": heading}]
        blocks.extend(section_blocks)
        written.append(heading)

    return (
        {
            "meta": meta,
            "blocks": blocks,
            "references": plan.get("references", []) or [],
            "visualization_plan": viz,
        },
        provider,
    )


# ── passes ──────────────────────────────────────────────────────────────────

def _plan(*, raw_text: str, style_guide: str, depth: str, doc_kind: str, router: Any,
          attachments, reference_example, instructions, title_hint, authors,
          style_note: Optional[str] = None,
          cancel: Optional[threading.Event] = None) -> tuple[dict[str, Any], str]:
    msg = build_plan_message(
        raw_text=raw_text, style=style_guide, doc_kind=doc_kind, attachments=attachments,
        reference_example=reference_example, instructions=instructions,
        title_hint=title_hint, authors=authors,
    )
    text, provider, _elapsed = router.chat(
        [{"role": "system", "content": plan_system_prompt(style_guide, depth, style_note)},
         {"role": "user", "content": msg}],
        max_tokens=_PLAN_TOKENS,
        cancel=cancel,
    )
    plan = extract_json(text)
    if plan is None:
        raise ValueError("planning pass did not return JSON")
    return plan, provider


def _write_section(*, section: dict[str, Any], outline: list[dict[str, Any]], title: str,
                   viz: list[dict[str, Any]], written: list[str], raw_text: str,
                   style_guide: str, depth: str, router: Any, attachments, instructions,
                   style_note: Optional[str] = None,
                   cancel: Optional[threading.Event] = None) -> list[dict[str, Any]]:
    msg = build_section_message(
        section=section, outline=outline, title=title, visualization_plan=viz,
        written_so_far=written, raw_text=raw_text, attachments=attachments,
        instructions=instructions,
    )
    try:
        text, _provider, _elapsed = router.chat(
            [{"role": "system", "content": section_system_prompt(style_guide, depth, style_note)},
             {"role": "user", "content": msg}],
            max_tokens=_SECTION_TOKENS,
            cancel=cancel,
        )
    except GenerationCancelled:
        raise    # must unwind; a cancelled run is not a failed section
    except Exception as exc:
        raise SectionFailure(str(exc)) from exc

    data = extract_json(text)
    if not data or not isinstance(data.get("blocks"), list) or not data["blocks"]:
        raise SectionFailure("section pass returned no usable blocks")

    blocks = [b for b in data["blocks"] if isinstance(b, dict) and b.get("type")]
    if not blocks:
        raise SectionFailure("section pass returned no valid blocks")

    # The section owns exactly one level-1 heading: its own, first.
    heading = section.get("heading", "")
    if not (blocks[0].get("type") == "heading" and blocks[0].get("level") == 1):
        blocks.insert(0, {"type": "heading", "level": 1, "text": heading})
    else:
        blocks[0]["text"] = heading  # keep the outline's wording authoritative

    # Demote any further level-1 headings: a section must not invent siblings.
    for b in blocks[1:]:
        if b.get("type") == "heading" and b.get("level", 1) <= 1:
            b["level"] = 2

    return blocks


