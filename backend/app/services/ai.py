from __future__ import annotations

import os
import re
from typing import Any, Optional

from app.schemas import Tone


def _fallback_title(prompt: str) -> str:
    p = (prompt or "").strip()
    if not p:
        return "Untitled Document"
    line = re.split(r"\r\n|\n|\.|\?", p, maxsplit=1)[0].strip()
    return (line[:80] + "…") if len(line) > 80 else line


def _fallback_outline(prompt: str, doc_type_hint: str | None = None) -> list[str]:
    base = [
        "Executive Summary",
        "Introduction",
        "Key Findings",
        "Discussion",
        "Recommendations",
        "Conclusion",
    ]
    if doc_type_hint == "resume":
        return [
            "Profile",
            "Experience",
            "Education",
            "Skills",
            "Projects",
            "Certifications",
        ]
    if "cv" in (prompt or "").lower() or "resume" in (prompt or "").lower():
        return [
            "Profile",
            "Experience",
            "Education",
            "Skills",
            "Projects",
            "Certifications",
        ]
    return base


def _apply_tone(text: str, tone: Tone) -> str:
    if tone == "technical":
        return text
    if tone == "simple":
        return re.sub(r"\b(utilize|facilitate|approximately)\b", lambda m: {"utilize": "use", "facilitate": "help", "approximately": "about"}[m.group(1)], text, flags=re.IGNORECASE)
    return text


def generate_structured_document(
    *,
    prompt: str,
    formatting_rules: dict[str, Any],
    style_preset: str,
    tone: Tone,
    template_style: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Returns: {title, outline, sections:[{heading, content}]}.

    Uses OpenAI if configured; falls back to deterministic generation otherwise.
    """

    api_key = os.environ.get("OPENAI_API_KEY")
    model = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")

    if api_key:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key)
            system = (
                "You are DocPilot AI, an expert document generation agent. "
                "Produce professional documents with clear structure. "
                "Return strict JSON with keys: title (string), outline (array of strings), sections (array of {heading, content})."
            )
            user_payload = {
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
            }
            resp = client.responses.create(
                model=model,
                input=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": "Generate the document JSON for: " + str(user_payload)},
                ],
            )
            text = resp.output_text
            # Best-effort JSON extraction
            m = re.search(r"\{.*\}", text, flags=re.DOTALL)
            if m:
                import json

                return json.loads(m.group(0))
        except Exception:
            pass

    title = _fallback_title(prompt)
    outline = _fallback_outline(prompt, doc_type_hint=style_preset if style_preset in {"resume"} else None)

    sections = []
    for heading in outline:
        body = (
            f"{heading} for: {prompt.strip() or 'the requested topic'}. "
            "This section is generated with professional structure and clear formatting. "
            "Add specific details or data to refine accuracy."
        )
        sections.append({"heading": heading, "content": _apply_tone(body, tone)})

    return {"title": title, "outline": outline, "sections": sections}


def rewrite_paragraph(*, text: str, tone: Tone) -> str:
    base = (text or "").strip()
    if not base:
        return ""
    if tone == "formal":
        return base
    if tone == "simple":
        return _apply_tone(base, tone)
    if tone == "technical":
        return base + "\n\n(Technical note: expand with metrics, assumptions, and references.)"
    return base
