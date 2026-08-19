from __future__ import annotations

import json
import re
from typing import Any, Optional

from app.paper.jsonx import extract_json
from app.schemas import Tone

_SYSTEM_DOC = (
    "You are Formatly, an expert document generation agent. "
    "Produce professional documents with clear structure. "
    "Return ONLY strict JSON with keys: "
    "title (string), outline (array of strings), "
    "sections (array of objects each with 'heading' and 'content' string fields). "
    "No markdown fences, no extra keys, no commentary outside the JSON."
)

_SYSTEM_REWRITE = (
    "You are a professional editor. Rewrite the supplied text in the requested tone. "
    "Return only the rewritten text — no labels, no explanations."
)


# ── deterministic fallback helpers ───────────────────────────────────────────

def _fallback_title(prompt: str) -> str:
    p = (prompt or "").strip()
    if not p:
        return "Untitled Document"
    line = re.split(r"\r\n|\n|\.|\?", p, maxsplit=1)[0].strip()
    return (line[:80] + "...") if len(line) > 80 else line


def _fallback_outline(prompt: str, doc_type_hint: str | None = None) -> list[str]:
    if doc_type_hint == "resume" or "cv" in (prompt or "").lower() or "resume" in (prompt or "").lower():
        return ["Profile", "Experience", "Education", "Skills", "Projects", "Certifications"]
    return ["Executive Summary", "Introduction", "Key Findings", "Discussion", "Recommendations", "Conclusion"]


def _apply_tone(text: str, tone: Tone) -> str:
    if tone == "simple":
        return re.sub(
            r"\b(utilize|facilitate|approximately)\b",
            lambda m: {"utilize": "use", "facilitate": "help", "approximately": "about"}[m.group(1)],
            text,
            flags=re.IGNORECASE,
        )
    return text


def _extract_json(text: str) -> dict[str, Any] | None:
    """First JSON object in the model's reply, fences and truncation tolerated."""
    return extract_json(text)


# ── public API ────────────────────────────────────────────────────────────────

def generate_structured_document(
    *,
    prompt: str,
    formatting_rules: dict[str, Any],
    style_preset: str,
    tone: Tone,
    template_style: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    Returns {title, outline, sections:[{heading, content}]}.

    Tries the multi-provider router (Groq -> Gemini -> OpenRouter -> HuggingFace).
    Falls back to deterministic generation when all providers are unavailable.
    """
    user_content = (
        "Generate the document JSON for the following request:\n"
        + json.dumps(
            {
                "prompt": prompt,
                "style_preset": style_preset,
                "tone": tone,
                "formatting_rules": formatting_rules,
                "template_style": template_style or {},
                "requirements": {
                    "include_title_page": True,
                    "include_toc": True,
                    "include_summary": True,
                    "include_conclusion": True,
                },
            },
            indent=2,
        )
    )

    try:
        from app.services.router import get_router, AllProvidersFailed

        text, _provider, _elapsed = get_router().chat(
            [
                {"role": "system", "content": _SYSTEM_DOC},
                {"role": "user",   "content": user_content},
            ],
            max_tokens=1500,
        )
        result = _extract_json(text)
        if result and result.get("sections"):
            return result
    except Exception:
        pass

    # ── deterministic fallback ────────────────────────────────────────────────
    title   = _fallback_title(prompt)
    outline = _fallback_outline(prompt, doc_type_hint=style_preset if style_preset == "resume" else None)
    sections = [
        {
            "heading": h,
            "content": _apply_tone(
                f"{h} for: {prompt.strip() or 'the requested topic'}. "
                "This section is generated with professional structure and clear formatting. "
                "Add specific details or data to refine accuracy.",
                tone,
            ),
        }
        for h in outline
    ]
    return {"title": title, "outline": outline, "sections": sections}


def rewrite_paragraph(*, text: str, tone: Tone) -> str:
    base = (text or "").strip()
    if not base:
        return ""

    try:
        from app.services.router import get_router, AllProvidersFailed

        result, _provider, _elapsed = get_router().chat(
            [
                {"role": "system", "content": _SYSTEM_REWRITE},
                {"role": "user",   "content": f"Tone: {tone}\n\nText:\n{base}"},
            ],
            max_tokens=600,
        )
        return result.strip() or base
    except Exception:
        pass

    # ── deterministic fallback ────────────────────────────────────────────────
    if tone == "simple":
        return _apply_tone(base, tone)
    if tone == "technical":
        return base + "\n\n(Technical note: expand with metrics, assumptions, and references.)"
    return base
