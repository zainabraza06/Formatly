"""Stylesheet registry. Add a module here to support a new style."""
from __future__ import annotations

from app.paper.styles.acm import ACM
from app.paper.styles.apa import APA
from app.paper.styles.base import StyleSheet
from app.paper.styles.ieee import IEEE
from app.paper.styles.report import REPORT

_REGISTRY: dict[str, StyleSheet] = {s.id: s for s in (IEEE, APA, ACM, REPORT)}

# common things users type, mapped onto a registered style
_ALIASES = {
    "ieee": "ieee", "ieee conference": "ieee", "ieeetran": "ieee",
    "apa": "apa", "apa7": "apa", "apa 7": "apa",
    "acm": "acm", "sigconf": "acm",
    "report": "report", "technical report": "report", "business report": "report",
    "default": "report", "": "report",
}

DEFAULT_STYLE = "report"


def get_stylesheet(name: str | None) -> StyleSheet:
    key = (name or "").strip().lower()
    resolved = _ALIASES.get(key, key)
    return _REGISTRY.get(resolved, _REGISTRY[DEFAULT_STYLE])


def list_styles() -> list[dict[str, str]]:
    return [{"id": s.id, "name": s.name, "columns": str(s.page.columns)}
            for s in _REGISTRY.values()]


def is_known(name: str | None) -> bool:
    key = (name or "").strip().lower()
    return _ALIASES.get(key, key) in _REGISTRY


__all__ = ["StyleSheet", "get_stylesheet", "list_styles", "is_known", "DEFAULT_STYLE"]
