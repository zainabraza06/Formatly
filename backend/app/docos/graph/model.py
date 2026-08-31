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
    # Everywhere words are. "Bold Midlands wherever it appears" is not about a
    # class of node, and answering it with one — headings, say — formatted the
    # wrong things and missed the word in the table.
    "document": (NodeType.HEADING, NodeType.SUBHEADING, NodeType.BODY,
                 NodeType.PARAGRAPH, NodeType.CAPTION, NodeType.TABLE_CELL,
                 NodeType.REFERENCE, NodeType.FOOTNOTE,
                 NodeType.HEADER, NodeType.FOOTER),
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
    # Inline only: a citation marker or a chemical formula raises or lowers a
    # few characters without disturbing the line they sit on.
    vertical_align: Optional[str] = None  # superscript | subscript

    def merged(self, patch: "Style | dict[str, Any]") -> "Style":
        """Return a copy with non-None fields of `patch` overlaid."""
        data = self.model_dump()
        other = patch.model_dump() if isinstance(patch, Style) else dict(patch)
        for k, v in other.items():
            if v is not None and k in data:
                data[k] = v
        return Style(**data)


class Run(BaseModel):
    """A stretch of text inside a paragraph that is formatted as one piece.

    Word stores a paragraph as a sequence of these, and a paragraph whose words
    are not all formatted alike cannot be described without them: a bold phrase
    mid-sentence, an italic term, a superscript citation. `style` holds only what
    the run itself states — None still means "inherit", here from the paragraph.
    """

    text: str = ""
    style: Style = Field(default_factory=Style)

    def same_formatting_as(self, other: "Run") -> bool:
        return self.style.model_dump() == other.style.model_dump()


def merge_runs(runs: Iterable[Run]) -> list[Run]:
    """Join neighbours that are formatted alike, and drop empty ones.

    Word splits runs wherever it likes — a spell-check boundary, a saved
    revision — so the same sentence can arrive as a dozen identically formatted
    pieces. Merging keeps the model describing the document rather than the
    editing history that produced it.
    """
    out: list[Run] = []
    for run in runs:
        if not run.text:
            continue
        if out and out[-1].same_formatting_as(run):
            out[-1] = Run(text=out[-1].text + run.text, style=out[-1].style)
        else:
            out.append(run.model_copy(deep=True))
    return out


def _new_node_id() -> str:
    return f"n_{uuid4().hex[:12]}"


class Node(BaseModel):
    id: str = Field(default_factory=_new_node_id)
    type: NodeType
    content: str = ""
    style: Style = Field(default_factory=Style)
    metadata: dict[str, Any] = Field(default_factory=dict)
    children: list["Node"] = Field(default_factory=list)
    # How `content` is formatted piece by piece. Empty means the whole node is
    # formatted alike, by `style` — which is every node that came from anywhere
    # but a .docx, so nothing has to know about runs to work.
    runs: list[Run] = Field(default_factory=list)

    def walk(self) -> Iterator["Node"]:
        """Depth-first pre-order traversal including self."""
        yield self
        for child in self.children:
            yield from child.walk()

    # ── inline formatting ───────────────────────────────────────────────────
    def runs_text(self) -> str:
        return "".join(run.text for run in self.runs)

    def runs_describe_content(self) -> bool:
        """Do the runs still spell out `content`?

        `content` is the text of record. Anything that rewrites it — an AI
        rewrite, a replace action, a restored version — is describing new words,
        and the old words' formatting no longer has anything to attach to.
        Rather than require every such caller to remember the runs, the runs are
        checked against the text and ignored when they have gone stale.
        """
        return bool(self.runs) and self.runs_text() == self.content

    def inline_runs(self) -> list["Run"]:
        """The node's text as formatted pieces — always safe to render.

        Falls back to one unformatted run covering the whole content, which
        renders exactly as the node did before runs existed.
        """
        if self.runs_describe_content():
            return self.runs
        return [Run(text=self.content)] if self.content else []

    def apply_style(self, patch: "Style") -> None:
        """Format the whole node, inline pieces included.

        A run that states `italic=False` would otherwise defeat "make the body
        italic" on the words it covers — the command would look like it had
        half worked. Formatting the paragraph clears the run-level overrides
        for the attributes being set, and only those: a superscript citation
        stays raised, a run in a different face keeps it.
        """
        fields = [k for k, v in patch.model_dump().items() if v is not None]
        self.style = self.style.merged(patch)
        if not fields or not self.runs:
            return
        for run in self.runs:
            run.style = Style(**{k: (None if k in fields else v)
                                 for k, v in run.style.model_dump().items()})
        self.runs = merge_runs(self.runs)

    def replace_text(self, find: str, repl: str) -> bool:
        """Swap one string for another, keeping inline formatting where it can.

        The replacement is made in each piece as well as in the text, and the
        pieces are kept only if they still spell out the result — a match that
        straddled a boundary between two of them did not survive, and guessing
        which piece the new words belong to would be inventing formatting the
        document never had.
        """
        if not find or find not in self.content:
            return False
        self.content = self.content.replace(find, repl)
        if self.runs:
            candidate = [Run(text=r.text.replace(find, repl), style=r.style) for r in self.runs]
            self.runs = merge_runs(candidate)                 if "".join(r.text for r in candidate) == self.content else []
        return True

    def style_span(self, find: str, patch: "Style") -> int:
        """Format just the words `find`, wherever they appear. Returns how many.

        "Bold results in the abstract" means the word, not the paragraph it sits
        in. Styling the node was the only thing an action could do, so a request
        about a phrase bolded everything around it too. The text is split into
        runs at the edges of each match and the patch applied to the matches
        alone; everything else keeps the formatting it had.
        """
        needle = (find or "").strip()
        if not needle or not self.content:
            return 0

        lowered, target = self.content.lower(), needle.lower()
        spans: list[tuple[int, int]] = []
        at = lowered.find(target)
        while at >= 0:
            spans.append((at, at + len(target)))
            at = lowered.find(target, at + len(target))
        if not spans:
            return 0

        pieces: list[Run] = []
        offset = 0
        for run in self.inline_runs():
            start, end = offset, offset + len(run.text)
            cut = start
            for span_start, span_end in spans:
                if span_end <= start or span_start >= end:
                    continue                      # this match is elsewhere
                hit_start, hit_end = max(span_start, start), min(span_end, end)
                if hit_start > cut:
                    pieces.append(Run(text=self.content[cut:hit_start], style=run.style))
                pieces.append(Run(text=self.content[hit_start:hit_end],
                                  style=run.style.merged(patch)))
                cut = hit_end
            if cut < end:
                pieces.append(Run(text=self.content[cut:end], style=run.style))
            offset = end

        self.runs = merge_runs(pieces)
        return len(spans)

    def set_text(self, text: str) -> None:
        """Replace the words, dropping inline formatting that described the old
        ones. The paragraph's own `style` survives, because that describes the
        paragraph rather than any particular word in it."""
        self.content = text
        self.runs = []


Node.model_rebuild()
Run.model_rebuild()


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
        if target == "table_header":
            # Not a node type but a role: the cells of a row the table treats as
            # its heading. "The headings in the table" means these, and it used
            # to reach the document's own headings instead.
            return [cell
                    for row in self.find_by_types([NodeType.TABLE_ROW])
                    if (row.metadata or {}).get("header_row")
                    for cell in row.children
                    if cell.type is NodeType.TABLE_CELL]

        if target == "title":
            # The document's own title: the first heading in it. "Make the
            # title larger" resized every section heading in the report while
            # reporting success, because a title was only a heading like any
            # other.
            headings = self.find_by_types([NodeType.HEADING])
            return headings[:1]

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
