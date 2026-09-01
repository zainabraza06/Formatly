"""Action language: the structured contract the AI emits and the engine executes.

The AI never mutates the document — it only produces an `ActionBatch`. Every batch
is validated (type + target + params) before execution; anything invalid or
dangerous is rejected and the graph is left untouched.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, ValidationError

from app.docos.graph import Style
from app.docos.graph.model import TARGET_TO_TYPES


class ActionType(str, Enum):
    SELECT = "select"
    FORMAT = "format"
    DELETE = "delete"
    INSERT = "insert"
    REPLACE = "replace"
    HIGHLIGHT = "highlight"
    JUSTIFY = "justify"
    ALIGN = "align"
    RESIZE = "resize"
    MOVE = "move"
    COPY = "copy"
    PASTE = "paste"
    MERGE = "merge"
    SPLIT = "split"
    NORMALIZE = "normalize"
    # Rewrite the text of the nodes in scope. Unlike replace, which needs a
    # literal find/with, this carries an instruction and is resolved by a
    # model that is shown the actual text.
    REWRITE = "rewrite"
    # Draw the document's LaTeX as mathematics. A display change: it asks no
    # model, rewrites no words, and turning it off gives back exactly the text
    # the author typed. Converting the words instead is lossy and irreversible.
    RENDER_MATHS = "render_maths"
    # Turn the paragraphs in scope into list items, or take them back out of a
    # list. Bullets are a property of the paragraph in Word, not punctuation
    # typed into it, so this sets that property rather than editing the text.
    LIST = "list"
    # Which edges a table draws, and how heavily. A request about a table's
    # rules — "only the top and bottom borders" — is about the table, not
    # about the text in it, so no style patch can express it.
    BORDER = "border"
    # UPPERCASE, lowercase, Title Case, Sentence case. A change to the letters
    # and not to their formatting, but a mechanical one — asking a model to
    # retype a heading in capitals is slow, costly, and occasionally creative.
    CASE = "case"
    # Line spacing and the gaps around a paragraph. The document already
    # carries all three; nothing could ask for them.
    SPACING = "spacing"


# Targets that name a role rather than a node type, resolved by the graph.
ROLE_TARGETS: frozenset[str] = frozenset({"table_header", "title"})

TARGETS: frozenset[str] = frozenset(TARGET_TO_TYPES.keys()) | ROLE_TARGETS

# Operations that must name a target or explicit node ids to run.
_NEEDS_SCOPE = {
    ActionType.SELECT, ActionType.FORMAT, ActionType.DELETE, ActionType.HIGHLIGHT,
    ActionType.JUSTIFY, ActionType.ALIGN, ActionType.RESIZE, ActionType.MOVE,
    ActionType.COPY, ActionType.REPLACE, ActionType.MERGE, ActionType.SPLIT,
    ActionType.NORMALIZE, ActionType.REWRITE,
}


class Action(BaseModel):
    type: ActionType
    target: Optional[str] = None                 # high-level target, e.g. "heading"
    node_ids: list[str] = Field(default_factory=list)  # explicit scope (overrides target)
    style: Optional[Style] = None                # for format/highlight
    params: dict[str, Any] = Field(default_factory=dict)  # op-specific extras

    def scope_ok(self) -> bool:
        if self.type in _NEEDS_SCOPE:
            return bool(self.node_ids) or bool(self.target)
        return True


class ActionBatch(BaseModel):
    actions: list[Action] = Field(default_factory=list)
    reasoning: str = ""          # short human-readable summary (for the AI panel)


class ActionValidationError(Exception):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def validate_batch(raw: dict[str, Any]) -> ActionBatch:
    """Parse + validate an untrusted action batch. Raises on any problem."""
    try:
        batch = ActionBatch.model_validate(raw)
    except ValidationError as exc:
        raise ActionValidationError([_fmt(e) for e in exc.errors()]) from exc

    errors: list[str] = []
    if not batch.actions:
        errors.append("batch contains no actions")

    for i, a in enumerate(batch.actions):
        if a.target is not None and a.target not in TARGETS:
            errors.append(f"action[{i}]: unknown target '{a.target}'")
        if not a.scope_ok():
            errors.append(f"action[{i}]: '{a.type.value}' requires a target or node_ids")
        _validate_params(i, a, errors)

    _reject_dangerous(batch, errors)

    if errors:
        raise ActionValidationError(errors)
    return batch


def _validate_params(i: int, a: Action, errors: list[str]) -> None:
    if a.type == ActionType.ALIGN:
        val = a.params.get("alignment") or (a.style.alignment if a.style else None)
        if val not in {"left", "center", "right", "justify"}:
            errors.append(f"action[{i}]: align needs params.alignment in left|center|right|justify")
    if a.type == ActionType.RESIZE:
        # A size to set, a step to add to the sizes that are there, or a factor
        # to multiply them by: "12 pt", "by 2", and "larger" are three different
        # requests, and only the first of them names a size.
        if ("font_size" not in a.params and "scale" not in a.params
                and "delta" not in a.params
                and not (a.style and a.style.font_size)):
            errors.append(f"action[{i}]: resize needs a font_size, a delta or a scale")
    if a.type == ActionType.CASE:
        if str(a.params.get("kind") or "") not in ("upper", "lower", "title", "sentence"):
            errors.append(f"action[{i}]: case needs params.kind in upper|lower|title|sentence")
    if a.type == ActionType.SPACING:
        if not any(k in a.params for k in ("line", "before_pt", "after_pt")):
            errors.append(f"action[{i}]: spacing needs params.line, before_pt or after_pt")
    if a.type == ActionType.BORDER:
        sides = a.params.get("sides")
        if sides is not None and not isinstance(sides, list):
            errors.append(f"action[{i}]: border needs params.sides as a list")
    if a.type == ActionType.REPLACE:
        if "find" not in a.params and "with" not in a.params:
            errors.append(f"action[{i}]: replace needs params.find and params.with")
    if a.type in (ActionType.FORMAT, ActionType.HIGHLIGHT) and a.style is None and not a.params:
        errors.append(f"action[{i}]: {a.type.value} needs a style")


def _reject_dangerous(batch: ActionBatch, errors: list[str]) -> None:
    # A delete that targets the whole document body with no id scope is refused.
    for i, a in enumerate(batch.actions):
        if a.type == ActionType.DELETE and a.target in {"paragraph", "body"} and not a.node_ids:
            if a.params.get("confirm") is not True:
                errors.append(
                    f"action[{i}]: refusing to delete every '{a.target}' without confirm=true or node_ids"
                )


def _fmt(err: dict[str, Any]) -> str:
    loc = ".".join(str(x) for x in err.get("loc", ()))
    return f"{loc}: {err.get('msg', 'invalid')}"
