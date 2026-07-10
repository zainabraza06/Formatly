"""Document graph model.

The document is a tree of typed nodes. Each node carries content, style,
metadata and children. The graph maintains an id index for O(1) lookup and
provides typed traversal used by the execution engine to resolve action targets.

The model is a plain pydantic tree so it serialises straight to/from JSON for
storage (version snapshots) and transport (WebSocket / REST).
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Iterable, Iterator, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    DOCUMENT = "document"
    PARAGRAPH = "paragraph"
    HEADING = "heading"
    SUBHEADING = "subheading"
    BODY = "body"
    IMAGE = "image"
    FIGURE = "figure"
    CAPTION = "caption"
    TABLE = "table"
    TABLE_ROW = "table_row"
    TABLE_CELL = "table_cell"
    HORIZONTAL_RULE = "horizontal_rule"
    PAGE_BREAK = "page_break"
    HEADER = "header"
    FOOTER = "footer"
    REFERENCE = "reference"
    FOOTNOTE = "footnote"


# Which concrete node types a high-level action `target` resolves to.
# e.g. target "body" matches body paragraphs; "figure" matches figures & images.
TARGET_TO_TYPES: dict[str, tuple[NodeType, ...]] = {
    "heading": (NodeType.HEADING,),
    "subheading": (NodeType.SUBHEADING,),
    "paragraph": (NodeType.PARAGRAPH, NodeType.BODY),
    "body": (NodeType.BODY, NodeType.PARAGRAPH),
    "table": (NodeType.TABLE,),
    "table_cell": (NodeType.TABLE_CELL,),
    "figure": (NodeType.FIGURE, NodeType.IMAGE),
    "image": (NodeType.IMAGE,),
    "caption": (NodeType.CAPTION,),
    "reference": (NodeType.REFERENCE,),
    "horizontal_rule": (NodeType.HORIZONTAL_RULE,),
    "page_break": (NodeType.PAGE_BREAK,),
    "header": (NodeType.HEADER,),
    "footer": (NodeType.FOOTER,),
    "footnote": (NodeType.FOOTNOTE,),
}


class Style(BaseModel):
    """Presentation attributes. All optional; None means "inherit / unset"."""

    font_family: Optional[str] = None
    font_size: Optional[float] = None
    bold: Optional[bool] = None
    italic: Optional[bool] = None
    underline: Optional[bool] = None
    color: Optional[str] = None          # hex, e.g. "#003366"
    highlight: Optional[str] = None      # hex or named
    alignment: Optional[str] = None      # left | center | right | justify

    def merged(self, patch: "Style | dict[str, Any]") -> "Style":
        """Return a copy with non-None fields of `patch` overlaid."""
        data = self.model_dump()
        other = patch.model_dump() if isinstance(patch, Style) else dict(patch)
        for k, v in other.items():
            if v is not None and k in data:
                data[k] = v
        return Style(**data)


def _new_node_id() -> str:
    return f"n_{uuid4().hex[:12]}"


class Node(BaseModel):
    id: str = Field(default_factory=_new_node_id)
    type: NodeType
    content: str = ""
    style: Style = Field(default_factory=Style)
    metadata: dict[str, Any] = Field(default_factory=dict)
    children: list["Node"] = Field(default_factory=list)

    def walk(self) -> Iterator["Node"]:
        """Depth-first pre-order traversal including self."""
        yield self
        for child in self.children:
            yield from child.walk()


Node.model_rebuild()


class DocumentGraph(BaseModel):
    """Root container. `root` is always a DOCUMENT node."""

    root: Node = Field(default_factory=lambda: Node(type=NodeType.DOCUMENT))
    title: str = ""

    # ── indexing ────────────────────────────────────────────────────────────
    def index(self) -> dict[str, Node]:
        return {n.id: n for n in self.root.walk()}

    def get(self, node_id: str) -> Optional[Node]:
        for n in self.root.walk():
            if n.id == node_id:
                return n
        return None

    def parent_of(self, node_id: str) -> Optional[Node]:
        for n in self.root.walk():
            if any(c.id == node_id for c in n.children):
                return n
        return None

    def nodes(self) -> Iterator[Node]:
        """All nodes except the document root."""
        it = self.root.walk()
        next(it)  # skip root
        yield from it

    def find_by_types(self, types: Iterable[NodeType]) -> list[Node]:
        wanted = set(types)
        return [n for n in self.nodes() if n.type in wanted]

    def resolve_target(self, target: str) -> list[Node]:
        """Resolve a high-level action target to concrete nodes, in doc order."""
        types = TARGET_TO_TYPES.get(target)
        if not types:
            return []
        return self.find_by_types(types)

    # ── mutation helpers (used only by the execution engine) ────────────────
    def remove(self, node_id: str) -> bool:
        parent = self.parent_of(node_id)
        if parent is None:
            return False
        before = len(parent.children)
        parent.children = [c for c in parent.children if c.id != node_id]
        return len(parent.children) != before

    def insert_after(self, sibling_id: str, node: Node) -> bool:
        parent = self.parent_of(sibling_id)
        if parent is None:
            return False
        idx = next((i for i, c in enumerate(parent.children) if c.id == sibling_id), None)
        if idx is None:
            return False
        parent.children.insert(idx + 1, node)
        return True

    def move_to_end(self, node_id: str, new_parent_id: str) -> bool:
        node = self.get(node_id)
        new_parent = self.get(new_parent_id)
        if node is None or new_parent is None:
            return False
        if not self.remove(node_id):
            return False
        new_parent.children.append(node)
        return True

    def clone(self) -> "DocumentGraph":
        return DocumentGraph.model_validate(self.model_dump())

    # ── serialisation ───────────────────────────────────────────────────────
    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DocumentGraph":
        return cls.model_validate(data)
