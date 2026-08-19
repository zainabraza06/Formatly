"""Reference-entry normalisation.

Two jobs, both aimed at the reference list rendering as readable, single-line
entries:

* Models asked for "citations" sometimes hand back the raw BibTeX they were
  given instead of a formatted entry. `@article{key, title = {...}, ...}` in a
  reference list is not a reference — it is source code. We format it.
* Any entry that still carries newlines is flattened. A justified paragraph
  whose lines end in manual breaks gets each of those lines stretched to the
  column width, and a line holding a single unbreakable token (`@article{key,`)
  has no inter-word gaps to absorb the slack, so the whole token is pushed
  flush right. Single-line entries cannot hit that.
"""
from __future__ import annotations

import re

_BIBTEX_HEAD = re.compile(r"^\s*@(\w+)\s*\{\s*([^,\s]*)\s*,", re.IGNORECASE)
_FIELD = re.compile(r"(\w+)\s*=\s*", re.IGNORECASE)


def _strip_braces(value: str) -> str:
    value = value.strip().strip(",").strip()
    while len(value) >= 2 and value[0] in "{\"" and value[-1] in "}\"":
        value = value[1:-1].strip()
    return re.sub(r"\s+", " ", value.replace("{", "").replace("}", "")).strip()


def _split_fields(body: str) -> dict[str, str]:
    """Split a BibTeX entry body into fields, tracking brace depth so that
    commas inside `{...}` (author lists, titles) do not split a value."""
    fields: dict[str, str] = {}
    depth = quote = 0
    start = 0
    parts: list[str] = []
    for i, ch in enumerate(body):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        elif ch == '"' and depth == 0:
            quote ^= 1
        elif ch == "," and depth <= 0 and not quote:
            parts.append(body[start:i])
            start = i + 1
    parts.append(body[start:])

    for part in parts:
        m = _FIELD.match(part.strip())
        if m:
            fields[m.group(1).lower()] = _strip_braces(part.strip()[m.end():])
    return fields


def _initials(name: str) -> str:
    """"Vavoulas, George" -> "G. Vavoulas"; "George Vavoulas" -> "G. Vavoulas"."""
    name = name.strip()
    if not name:
        return ""
    if "," in name:
        last, _, first = name.partition(",")
    else:
        words = name.split()
        last, first = words[-1], " ".join(words[:-1])
    given = " ".join(f"{w[0]}." for w in first.split() if w)
    last = last.strip()
    return f"{given} {last}".strip() if given else last


def _authors(raw: str) -> str:
    people = [_initials(p) for p in re.split(r"\s+and\s+", raw) if p.strip()]
    people = [p for p in people if p]
    if len(people) > 2:
        return ", ".join(people[:-1]) + ", and " + people[-1]
    return " and ".join(people)


def _format_bibtex(entry_type: str, fields: dict[str, str]) -> str:
    """Render BibTeX fields as one flat citation line. `*text*` becomes real
    italics downstream — the renderer turns markdown emphasis into runs."""
    parts: list[str] = []

    if authors := _authors(fields.get("author") or fields.get("editor", "")):
        parts.append(authors)
    if title := fields.get("title"):
        parts.append(f'"{title},"' if fields.get("journal") or fields.get("booktitle")
                     else f"*{title}*")

    if container := fields.get("journal") or fields.get("booktitle"):
        parts.append(f"*{container}*")

    if vol := fields.get("volume"):
        parts.append(f"vol. {vol}")
    if num := fields.get("number"):
        parts.append(f"no. {num}")
    if pages := fields.get("pages"):
        pages = pages.replace("--", "–")
        parts.append(f"pp. {pages}" if "–" in pages or "-" in pages else f"p. {pages}")

    if publisher := fields.get("publisher") or fields.get("school") or fields.get("institution"):
        parts.append(publisher)
    if entry_type.lower() == "phdthesis":
        parts.append("Ph.D. dissertation")
    if year := fields.get("year"):
        parts.append(year)
    if (url := fields.get("url")) and not fields.get("journal"):
        parts.append(url)
    elif doi := fields.get("doi"):
        parts.append(f"doi: {doi}")

    text = _join(parts)
    return f"{text}." if text and not text.endswith(".") else text


def _join(parts: list[str]) -> str:
    """Comma-join, except after a part that already ends in its own comma —
    a quoted title reads `"Title," *Journal*`, not `"Title,", *Journal*`."""
    out = ""
    for part in (p for p in parts if p):
        if not out:
            out = part
        elif out.rstrip('"').endswith(","):
            out += f" {part}"
        else:
            out += f", {part}"
    return out


def format_reference(raw: str) -> str:
    """Normalise one reference entry to a single formatted line."""
    if not raw:
        return ""
    text = raw.strip()

    m = _BIBTEX_HEAD.match(text)
    if m:
        body = text[m.end():]
        body = body[:body.rfind("}")] if "}" in body else body
        formatted = _format_bibtex(m.group(1), _split_fields(body))
        if formatted:
            return formatted

    # not BibTeX (or unparseable) — at minimum, never leave manual line breaks
    return re.sub(r"\s+", " ", text).strip()
