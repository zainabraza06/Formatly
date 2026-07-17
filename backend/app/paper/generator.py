"""IEEE paper generator: raw material → validated, fully-styled PaperSpec.

Uses the multi-provider router (Mistral → Groq → Gemini → OpenRouter → HuggingFace).
The model returns semantic JSON; we validate it against the schema and then stamp
explicit IEEE formatting onto every block via the stylesheet resolver.
"""
from __future__ import annotations

import json
import re
from typing import Any, Optional, Sequence

from pydantic import ValidationError

from app.paper.agentic import Progress, generate_sectioned
from app.paper.prompt import DEFAULT_DEPTH, build_user_message, system_prompt
from app.paper.schema import Author, PaperSpec
from app.paper.styles import DEFAULT_STYLE, StyleLike, is_builtin, resolve_style
from app.paper.stylesheet import resolve

# Depths a single call cannot hold: measured, `detailed` overruns the ceiling and
# truncates its JSON, so it is always written in passes.
_MULTIPASS_DEPTHS = {"detailed"}


class PaperGenerationError(Exception):
    pass


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
    max_tokens: int = 4000,
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

    sheet = resolve_style(style, owner_id)
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
                on_progress=on_progress,
            )
        except Exception as exc:
            raise PaperGenerationError(f"multi-pass generation failed: {exc}") from exc
    else:
        user_msg = build_user_message(
            raw_text=raw_text, style=guide_id, doc_kind=doc_kind, attachments=attachments,
            reference_example=reference_example, instructions=instructions,
            title_hint=title_hint, authors=authors,
        )
        try:
            text, provider, _elapsed = router.chat(
                [{"role": "system", "content": system_prompt(guide_id, depth)},
                 {"role": "user", "content": user_msg}],
                max_tokens=max_tokens,
            )
        except Exception as exc:
            raise PaperGenerationError(f"all AI providers failed: {exc}") from exc

        raw = _extract_json(text)

    if raw is None:
        raise PaperGenerationError("model did not return valid JSON")

    try:
        spec = PaperSpec.model_validate(raw)
    except ValidationError as exc:
        raise PaperGenerationError(f"model JSON did not match the paper schema: {exc}") from exc

    if not spec.blocks:
        raise PaperGenerationError("model returned a paper with no content blocks")

    # caller-supplied authors always win over anything the model invented
    if authors:
        spec.meta.authors = [Author(**a) for a in authors]
    if title_hint and not spec.meta.title.strip():
        spec.meta.title = title_hint

    return resolve(spec, sheet), provider


def _extract_json(text: str) -> Optional[dict[str, Any]]:
    """Pull the first JSON object out of the model's reply, tolerating fences."""
    if not text:
        return None
    cleaned = re.sub(r"^\s*```(?:json)?|```\s*$", "", text.strip(), flags=re.MULTILINE)
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
