"""IEEE paper generator: raw material → validated, fully-styled PaperSpec.

Uses the multi-provider router (Mistral → Groq → Gemini → OpenRouter → HuggingFace).
The model returns semantic JSON; we validate it against the schema and then stamp
explicit IEEE formatting onto every block via the stylesheet resolver.
"""
from __future__ import annotations

from typing import Any, Optional, Sequence

from pydantic import TypeAdapter, ValidationError

from app.paper.agentic import Progress, generate_sectioned
from app.paper.jsonx import extract_json
from app.paper.prompt import DEFAULT_DEPTH, build_user_message, system_prompt
from app.paper.schema import Author, Block, PaperSpec
from app.paper.styles import (
    DEFAULT_STYLE, StyleLike, is_builtin, lookup_style, resolve_style,
)
from app.paper.stylesheet import resolve

# Depths a single call cannot hold: measured, `detailed` overruns the ceiling and
# truncates its JSON, so it is always written in passes.
_MULTIPASS_DEPTHS = {"detailed"}


class PaperGenerationError(Exception):
    pass


_BLOCK = TypeAdapter(Block)

# Sent back to the model after a reply we could not parse. Naming the failure is
# what makes the second attempt different from the first.
_RETRY_NOTE = (
    "Your previous reply could not be parsed. Reply with the JSON object ONLY: "
    "no explanation, no markdown fence, nothing before or after it. Make sure it "
    "is complete and every brace is closed — if you are running short of room, "
    "write fewer blocks rather than stopping in the middle of one."
)


def _needs_multipass(depth: str, override: Optional[bool]) -> bool:
    return override if override is not None else depth in _MULTIPASS_DEPTHS


def generate_paper(
    *,
    raw_text: str,
    style: StyleLike = DEFAULT_STYLE,
    doc_kind: str = "document",
    depth: str = DEFAULT_DEPTH,          # brief | standard | detailed
    attachments: Optional[Sequence[dict[str, str]]] = None,
    reference_example: Optional[str] = None,
    instructions: Optional[str] = None,
    title_hint: Optional[str] = None,
    authors: Optional[list[dict[str, str]]] = None,
    owner_id: Optional[str] = None,
    router: Any = None,
    max_tokens: int = 8000,
    multipass: Optional[bool] = None,   # None = decide from depth
    on_progress: Optional[Progress] = None,
) -> tuple[PaperSpec, str]:
    """Turn raw material into a fully-styled PaperSpec.

    `attachments` is any number of freely-labelled extra material blocks
    ({"label": ..., "content": ...}) — data, transcripts, code, citations, notes;
    whatever the document happens to need.

    Returns (resolved_spec, provider_used). Raises PaperGenerationError on failure.
    """
    if not (raw_text or "").strip():
        raise PaperGenerationError("no source material supplied")

    # A name we don't implement (Chicago, Harvard, a journal house style) must not
    # be silently swallowed: we cannot reproduce its typography without a
    # stylesheet, but the writer can still follow its conventions, so the name is
    # carried through to the prompt and a neutral sheet supplies the layout.
    known = lookup_style(style, owner_id)
    style_note: Optional[str] = None
    if known is None and isinstance(style, str) and style.strip():
        style_note = style.strip()
    sheet = known or resolve_style(DEFAULT_STYLE, owner_id)

    # Steer the writer with the closest built-in convention; a custom style only
    # changes typography, not what good prose for that document kind looks like.
    guide_id = sheet.id if is_builtin(sheet.id) else DEFAULT_STYLE

    if router is None:
        from app.services.router import get_router
        router = get_router()

    if _needs_multipass(depth, multipass):
        # One call cannot hold a detailed document: it overruns the token ceiling
        # and the JSON truncates, losing everything. Plan first, then write each
        # section on its own.
        try:
            raw, provider = generate_sectioned(
                raw_text=raw_text, style_guide=guide_id, depth=depth, doc_kind=doc_kind,
                router=router, attachments=attachments, reference_example=reference_example,
                instructions=instructions, title_hint=title_hint, authors=authors,
                on_progress=on_progress, style_note=style_note,
            )
        except Exception as exc:
            raise PaperGenerationError(f"multi-pass generation failed: {exc}") from exc
    else:
        user_msg = build_user_message(
            raw_text=raw_text, style=guide_id, doc_kind=doc_kind, attachments=attachments,
            reference_example=reference_example, instructions=instructions,
            title_hint=title_hint, authors=authors,
        )
        base = [{"role": "system", "content": system_prompt(guide_id, depth, style_note)},
                {"role": "user", "content": user_msg}]

        # A model occasionally returns unparseable JSON; re-sampling usually
        # succeeds, and telling it *why* the last reply failed makes the second
        # and third attempts genuinely different from the first.
        raw = None
        provider = ""
        last_error = ""
        for attempt in range(3):
            messages = base if attempt == 0 else (
                base + [{"role": "user", "content": _RETRY_NOTE}])
            try:
                text, provider, _elapsed = router.chat(messages, max_tokens=max_tokens)
            except Exception as exc:
                raise PaperGenerationError(f"all AI providers failed: {exc}") from exc
            raw = extract_json(text)
            if raw is not None:
                break
            last_error = (text or "").strip()[:160]

        if raw is None:
            # No single reply survived. Rather than lose the document, write it
            # the way `detailed` is written: plan first, then one pass per
            # section, each small enough to finish inside the token ceiling.
            if on_progress:
                on_progress("retry", "writing the document in sections instead")
            try:
                raw, provider = generate_sectioned(
                    raw_text=raw_text, style_guide=guide_id, depth=depth, doc_kind=doc_kind,
                    router=router, attachments=attachments,
                    reference_example=reference_example, instructions=instructions,
                    title_hint=title_hint, authors=authors, on_progress=on_progress,
                    style_note=style_note,
                )
            except Exception as exc:
                raise PaperGenerationError(
                    "the model did not return usable JSON, and writing it in "
                    f"sections also failed ({exc})"
                    + (f" — the reply started with: {last_error!r}" if last_error else "")
                ) from exc

    if raw is None:
        raise PaperGenerationError("model did not return valid JSON")

    try:
        spec = PaperSpec.model_validate(raw)
    except ValidationError as exc:
        spec = _salvage_spec(raw)
        if spec is None:
            raise PaperGenerationError(
                f"model JSON did not match the paper schema: {exc}") from exc

    if not spec.blocks:
        raise PaperGenerationError("model returned a paper with no content blocks")

    # caller-supplied authors always win over anything the model invented
    if authors:
        spec.meta.authors = [Author(**a) for a in authors]
    if title_hint and not spec.meta.title.strip():
        spec.meta.title = title_hint

    return resolve(spec, sheet), provider


def _salvage_spec(raw: dict[str, Any]) -> Optional[PaperSpec]:
    """Build a spec from the parts of `raw` that do validate.

    A truncated or sloppy reply typically leaves one malformed block behind —
    a heading with no text, a figure with a mangled chart. That one block should
    not cost the reader the other thirty, so it is dropped and the rest kept.
    Falls back to shedding the metadata, then the references, before giving up.
    """
    if not isinstance(raw, dict):
        return None

    good: list[Any] = []
    for block in raw.get("blocks") or []:
        try:
            _BLOCK.validate_python(block)
        except ValidationError:
            continue
        good.append(block)
    if not good:
        return None

    candidate = {**raw, "blocks": good}
    for ladder in (candidate, {**candidate, "references": []},
                   {"meta": raw.get("meta") or {}, "blocks": good}, {"blocks": good}):
        try:
            return PaperSpec.model_validate(ladder)
        except ValidationError:
            continue
    return None
