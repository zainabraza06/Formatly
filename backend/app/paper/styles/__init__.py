"""Stylesheet registry.

Built-in styles are declared as modules here. User-defined styles live in the
database and resolve through the same entry point, so nothing downstream knows
or cares whether a style shipped with the app or was authored by a user.
"""
from __future__ import annotations

from typing import Optional, Union

from app.paper.styles.assignment import ASSIGNMENT
from app.paper.styles.base import StyleSheet
from app.paper.styles.ieee import IEEE, IEEE_1COL

_REGISTRY: dict[str, StyleSheet] = {s.id: s for s in (IEEE, IEEE_1COL, ASSIGNMENT)}

# common things users type, mapped onto a built-in style
_ALIASES = {
    "ieee": "ieee", "ieee conference": "ieee", "ieeetran": "ieee",
    "ieee_1col": "ieee_1col", "ieee 1 column": "ieee_1col",
    # Coursework, lab reports and anything with code do not belong in a
    # conference two-column layout, so they resolve to the formal style.
    "assignment": "assignment", "assignments": "assignment",
    "homework": "assignment", "coursework": "assignment",
    "lab report": "assignment", "lab": "assignment",
    "report": "assignment", "formal": "assignment", "official": "assignment",
    "submission": "assignment", "document": "assignment",
    "default": "ieee", "": "ieee",
}

DEFAULT_STYLE = "ieee"

StyleLike = Union[str, StyleSheet, None]


def get_stylesheet(name: str | None) -> StyleSheet:
    """Built-in lookup. Unknown names fall back to the default style."""
    key = (name or "").strip().lower()
    resolved = _ALIASES.get(key, key)
    return _REGISTRY.get(resolved, _REGISTRY[DEFAULT_STYLE])


def is_builtin(name: str | None) -> bool:
    """Does this name reach a built-in sheet, by id or by alias?"""
    key = (name or "").strip().lower()
    return _ALIASES.get(key, key) in _REGISTRY


def _is_builtin_id(name: str | None) -> bool:
    """A built-in sheet's own id, as opposed to one of the loose names that
    merely point at it. The distinction decides who wins against a user's custom
    style: an id does, an alias does not."""
    return (name or "").strip().lower() in _REGISTRY


def _custom(key: str, owner_id: Optional[str]) -> Optional[StyleSheet]:
    if not owner_id:
        return None
    from app.paper.styles.store import get_style_store
    store = get_style_store()
    return store.get(key, owner_id) or store.get_by_name(key, owner_id)


def lookup_style(style: StyleLike, owner_id: Optional[str] = None) -> Optional[StyleSheet]:
    """Find a stylesheet, or None if the name is not one we implement.

    Distinct from `resolve_style`, which always returns something. Callers that
    need to know a name was *unrecognised* — so they can still honour it, e.g. by
    asking the writer to follow Chicago conventions — must use this.
    """
    if isinstance(style, StyleSheet):
        return style

    key = (style or "").strip()
    if not key:
        return None
    if _is_builtin_id(key):
        return get_stylesheet(key)

    # A user who named their own style "Report" means their own style, so the
    # custom store is consulted before the alias table — but after the built-in
    # ids, which are ours and cannot be claimed.
    return _custom(key, owner_id) or (get_stylesheet(key) if is_builtin(key) else None)


def resolve_style(style: StyleLike, owner_id: Optional[str] = None) -> StyleSheet:
    """Resolve a style from an object, a built-in id/alias, or a user's custom style.

    Order: explicit StyleSheet → built-in id → user's custom (by id, then by
    name) → built-in alias → default.
    """
    if isinstance(style, StyleSheet):
        return style

    key = (style or "").strip()
    if not key:
        return _REGISTRY[DEFAULT_STYLE]
    if _is_builtin_id(key):
        return get_stylesheet(key)

    found = _custom(key, owner_id)
    if found:
        return found
    if is_builtin(key):
        return get_stylesheet(key)

    return _REGISTRY[DEFAULT_STYLE]


def _summary(sheet: StyleSheet, builtin: bool) -> dict[str, str]:
    return {
        "id": sheet.id,
        "name": sheet.name,
        "columns": str(sheet.page.columns),
        "builtin": "true" if builtin else "false",
        "derived_from": sheet.derived_from,
        # what was read from a reference sample rather than inherited from a base
        "detected": ",".join(sheet.detected),
        "heading_scheme": sheet.heading_scheme,
        "table_borders": sheet.table_borders,
    }


def list_styles(owner_id: Optional[str] = None) -> list[dict[str, str]]:
    """Built-in styles, plus the user's custom styles when an owner is given."""
    out = [_summary(s, True) for s in _REGISTRY.values()]
    if owner_id:
        from app.paper.styles.store import get_style_store
        out += [_summary(s, False) for s in get_style_store().list(owner_id)]
    return out


__all__ = [
    "StyleSheet", "StyleLike", "get_stylesheet", "resolve_style", "lookup_style",
    "list_styles", "is_builtin", "DEFAULT_STYLE",
]
