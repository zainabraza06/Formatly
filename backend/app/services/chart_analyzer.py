"""
Chart analyzer: reads document sections with the LLM and returns
a list of ChartSpec objects with populated titles, labels, values,
and axis labels — ready for rendering by charts.py.

Falls back gracefully when the LLM is unavailable or returns
malformed JSON.
"""
from __future__ import annotations

from typing import Any

from app.paper.jsonx import extract_json_array
from app.schemas import ChartSpec, DocumentSection
from app.services.router import AllProvidersFailed, get_router


_SYSTEM = (
    "You are a data analyst assistant. Given document sections, you identify data "
    "that can be meaningfully visualised as bar, line, or pie charts. "
    "Respond ONLY with a valid JSON array — no prose, no markdown fences."
)

_USER_TMPL = """\
Analyse the following document sections and suggest up to 5 charts that would \
meaningfully visualise quantitative or comparative data found in the text.

For each chart return an object with these keys:
  kind        : "bar" | "line" | "pie"
  title       : descriptive chart title (string)
  labels      : list of category/x-axis label strings
  values      : list of numeric floats matching labels
  x_label     : x-axis label (empty string if not applicable)
  y_label     : y-axis label (units, e.g. "USD billions", "percentage", "count")
  explanation : one sentence explaining why this chart was chosen

If no quantitative data exists, return an empty array [].

DOCUMENT SECTIONS:
{content}
"""


def _extract_json(text: str) -> list[dict[str, Any]]:
    """The chart list from the model's reply, fences and truncation tolerated."""
    items = extract_json_array(text) or []
    return [x for x in items if isinstance(x, dict)]


def _validate_spec(raw: dict[str, Any]) -> ChartSpec | None:
    """Convert a raw dict from the LLM into a validated ChartSpec, or None."""
    try:
        kind = raw.get("kind", "bar")
        if kind not in ("bar", "line", "pie"):
            kind = "bar"

        labels = [str(l) for l in (raw.get("labels") or [])]
        raw_vals = raw.get("values") or []
        values = [float(v) for v in raw_vals if v is not None]

        if not values or len(values) < 2:
            return None

        # align labels and values length
        n = min(len(labels), len(values))
        if n == 0:
            n = len(values)
            labels = [f"Item {i+1}" for i in range(n)]
        else:
            labels = labels[:n]
            values = values[:n]

        return ChartSpec(
            kind=kind,
            title=str(raw.get("title") or "Chart"),
            labels=labels,
            values=values,
            x_label=str(raw.get("x_label") or ""),
            y_label=str(raw.get("y_label") or "Value"),
            explanation=str(raw.get("explanation") or ""),
        )
    except Exception:
        return None


def analyze_charts(sections: list[DocumentSection]) -> list[ChartSpec]:
    """
    Ask the LLM to identify suitable charts for the given document sections.
    Returns a list of validated ChartSpec objects (empty list on failure).
    """
    # Build a compact text dump of all section content
    content_parts: list[str] = []
    for sec in sections:
        content_parts.append(f"## {sec.heading}\n{sec.content or ''}")
    combined = "\n\n".join(content_parts)

    # Truncate to ~4000 chars to stay within token limits
    if len(combined) > 4000:
        combined = combined[:4000] + "\n[truncated]"

    messages = [
        {"role": "system", "content": _SYSTEM},
        {"role": "user",   "content": _USER_TMPL.format(content=combined)},
    ]

    try:
        text, _provider, _elapsed = get_router().chat(
            messages, max_tokens=1200
        )
    except AllProvidersFailed:
        return []
    except Exception:
        return []

    raw_list = _extract_json(text)
    specs: list[ChartSpec] = []
    for raw in raw_list:
        spec = _validate_spec(raw)
        if spec:
            specs.append(spec)

    return specs[:5]  # cap at 5 charts
