"""Stylesheet registry.

Built-in styles are declared as modules here. User-defined styles live in the
database and resolve through the same entry point, so nothing downstream knows
or cares whether a style shipped with the app or was authored by a user.
"""
from __future__ import annotations

from typing import Optional, Union

from app.paper.styles.acm import ACM
from app.paper.styles.apa import APA
from app.paper.styles.base import StyleSheet
from app.paper.styles.ieee import IEEE
from app.paper.styles.report import REPORT

_REGISTRY: dict[str, StyleSheet] = {s.id: s for s in (IEEE, APA, ACM, REPORT)}

# common things users type, mapped onto a built-in style
_ALIASES = {
    "ieee": "ieee", "ieee conference": "ieee", "ieeetran": "ieee",
    "apa": "apa", "apa7": "apa", "apa 7": "apa", "apa 7th": "apa",
    "acm": "acm", "sigconf": "acm",
    "report": "report", "technical report": "report", "business report": "report",
    "default": "report", "": "report",
}

DEFAULT_STYLE = "report"

StyleLike = Union[str, StyleSheet, None]


def get_stylesheet(name: str | None) -> StyleSheet:
    """Built-in lookup. Unknown names fall back to the default style."""
    key = (name or "").strip().lower()
    resolved = _ALIASES.get(key, key)
    return _REGISTRY.get(resolved, _REGISTRY[DEFAULT_STYLE])


def is_builtin(name: str | None) -> bool:
    key = (name or "").strip().lower()
    return _ALIASES.get(key, key) in _REGISTRY


def resolve_style(style: StyleLike, owner_id: Optional[str] = None) -> StyleSheet:
    """Resolve a style from an object, a built-in id/alias, or a user's custom style.

    Order: explicit StyleSheet → built-in → user's custom (by id, then by name)
    → default.
    """
    if isinstance(style, StyleSheet):
        return style

    key = (style or "").strip()
    if not key:
        return _REGISTRY[DEFAULT_STYLE]
    if is_builtin(key):
        return get_stylesheet(key)

    if owner_id:
        from app.paper.styles.store import get_style_store
        store = get_style_store()
        found = store.get(key, owner_id) or store.get_by_name(key, owner_id)
        if found:
            return found

    return _REGISTRY[DEFAULT_STYLE]


def list_styles(owner_id: Optional[str] = None) -> list[dict[str, str]]:
    """Built-in styles, plus the user's custom styles when an owner is given."""
    out = [{"id": s.id, "name": s.name, "columns": str(s.page.columns),
            "builtin": "true", "derived_from": s.derived_from}
           for s in _REGISTRY.values()]
    if owner_id:
        from app.paper.styles.store import get_style_store
        out += [{"id": s.id, "name": s.name, "columns": str(s.page.columns),
                 "builtin": "false", "derived_from": s.derived_from}
                for s in get_style_store().list(owner_id)]
    return out


__all__ = [
    "StyleSheet", "StyleLike", "get_stylesheet", "resolve_style", "list_styles",
    "is_builtin", "DEFAULT_STYLE",
]
