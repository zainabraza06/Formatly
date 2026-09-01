"""Many commands at once, each checked by what it did to the document.

Every bug in this area has had one of two shapes. Either the document had a
concept the model did not — a list, a table's edges, a title that is not a
Heading, a step that is not a size — and the request had nowhere to land; or
the model had it and the renderer did not, so the command worked and the page
did not move.

This is the first of those, swept rather than sampled: one document with the
things a real paper has, and a table of instructions each asserted by its
effect on the graph. It runs offline, so it is testing the rules rather than
the model's mood, and a rule that stops understanding a phrasing fails here
instead of in front of someone.

`test_renderer_covers_the_model` is the second half.
"""
from __future__ import annotations

from typing import Callable

import pytest

from app.docos.command.engine import CommandEngine
from app.docos.execution.engine import ExecutionEngine
from app.docos.graph import DocumentGraph, Node, NodeType, Style

Check = Callable[[DocumentGraph], bool]


# ── a document with the things a paper has ───────────────────────────────────

def paper() -> DocumentGraph:
    def body(text: str, **style) -> Node:
        return Node(type=NodeType.BODY, content=text, style=Style(**style))

    cells = [[Node(type=NodeType.TABLE_CELL, content=c) for c in row]
             for row in (("Component", "Configuration"),
                         ("MLP dropout", "0.3"),
                         ("Optimizer", "Adam"))]
    table = Node(type=NodeType.TABLE, metadata={"rows": 3, "cols": 2}, children=[
        Node(type=NodeType.TABLE_ROW, children=cells[0], metadata={"header_row": True}),
        Node(type=NodeType.TABLE_ROW, children=cells[1]),
        Node(type=NodeType.TABLE_ROW, children=cells[2]),
    ])

    root = Node(type=NodeType.DOCUMENT, metadata={"page": {"default_size_pt": 10.0}})
    root.children = [
        body("A Lightweight Classifier for Joint Fall Detection", bold=True, font_size=12),
        body("Abstract — the study reports 96.1 per cent accuracy.", font_size=10),
        Node(type=NodeType.HEADING, content="I. Introduction", style=Style(font_size=12)),
        body("Falls are a major cause of injury among older adults.", font_size=10),
        body("The contributions are: (i) a benchmark; (ii) a feature set.", font_size=10),
        Node(type=NodeType.SUBHEADING, content="A. Scope", style=Style(font_size=11)),
        body("The scope is limited to wrist-worn sensors.", font_size=10),
        Node(type=NodeType.HORIZONTAL_RULE),
        table,
        Node(type=NodeType.CAPTION, content="Table 1. Model configuration."),
        Node(type=NodeType.CAPTION, content="Figure 2: Accuracy against volume."),
        body("Unit cost is $C = \\frac{F + vQ}{Q}$ per parcel.", font_size=10),
        Node(type=NodeType.HEADING, content="V. References", style=Style(font_size=12)),
        Node(type=NodeType.REFERENCE, content="[1] Office for Statistics, London, 2025."),
        Node(type=NodeType.REFERENCE, content="[2] Department for Transport, 2024."),
    ]
    return DocumentGraph(root=root, title="paper")


def run(command: str) -> DocumentGraph:
    """One command, through the rules and the executor, as the app runs it."""
    batch = CommandEngine()._heuristic_actions(command)
    result = ExecutionEngine().execute(paper(), batch)
    assert result.ok, f"{command!r} failed: {result.error}"
    return result.graph


# ── reading the result ───────────────────────────────────────────────────────

def of_type(graph: DocumentGraph, kind: NodeType) -> list[Node]:
    return [n for n in graph.nodes() if n.type is kind]


def styled(kind: NodeType, **wanted) -> Check:
    """Every node of that kind carries this formatting."""
    def check(graph: DocumentGraph) -> bool:
        nodes = of_type(graph, kind)
        return bool(nodes) and all(
            all(getattr(n.style, k) == v for k, v in wanted.items()) for n in nodes)
    return check


def any_run_styled(text: str, **wanted) -> Check:
    """Those exact words are formatted this way, and the words around them are not."""
    def check(graph: DocumentGraph) -> bool:
        for node in graph.nodes():
            for run_ in node.runs:
                if run_.text.strip() == text:
                    return all(getattr(run_.style, k) == v for k, v in wanted.items())
        return False
    return check


def listed(kind: str, count: int) -> Check:
    def check(graph: DocumentGraph) -> bool:
        items = [n for n in graph.nodes()
                 if (n.metadata.get("list") or {}).get("kind") == kind]
        return len(items) == count
    return check


def bordered(**sides) -> Check:
    def check(graph: DocumentGraph) -> bool:
        tables = of_type(graph, NodeType.TABLE)
        return bool(tables) and all(
            all((t.metadata.get("borders") or {}).get(k) == v for k, v in sides.items())
            for t in tables)
    return check


def sizes(kind: NodeType, *expected: float) -> Check:
    def check(graph: DocumentGraph) -> bool:
        return [n.style.font_size for n in of_type(graph, kind)] == list(expected)
    return check


def gone(kind: NodeType) -> Check:
    return lambda graph: not of_type(graph, kind)


# ── the sweep ────────────────────────────────────────────────────────────────

MATRIX: list[tuple[str, Check]] = [
    # weight, slope, rules and colour
    ("make all the headings bold", styled(NodeType.HEADING, bold=True)),
    ("italicise the references", styled(NodeType.REFERENCE, italic=True)),
    ("underline the captions", styled(NodeType.CAPTION, underline=True)),
    ("make the headings bold and italic",
     styled(NodeType.HEADING, bold=True, italic=True)),
    ("make the headings blue", styled(NodeType.HEADING, color="#1f4e79")),
    ("colour the captions green", styled(NodeType.CAPTION, color="#2e7d32")),
    ("highlight the captions", styled(NodeType.CAPTION, highlight="#fff59d")),

    # alignment, all four and several phrasings
    ("centre every caption", styled(NodeType.CAPTION, alignment="center")),
    ("right align the references", styled(NodeType.REFERENCE, alignment="right")),
    ("align the captions to the left", styled(NodeType.CAPTION, alignment="left")),
    ("justify the body text", styled(NodeType.BODY, alignment="justify")),
    ("center align the document title",
     lambda g: g.resolve_target("title")[0].style.alignment == "center"),

    # size: a number, a step, a direction
    ("change the references to font size 9", sizes(NodeType.REFERENCE, 9.0, 9.0)),
    ("increase the headings by 2", sizes(NodeType.HEADING, 14.0, 14.0)),
    ("make the headings 2 points smaller", sizes(NodeType.HEADING, 10.0, 10.0)),
    ("make the subheadings larger", sizes(NodeType.SUBHEADING, 13.8)),

    # lists
    ("put the contributions in bullets", listed("bullet", 2)),
    ("number the introduction", listed("number", 2)),
    ("itemise the scope", lambda g: listed("bullet", 1)(g) or listed("bullet", 2)(g)),

    # a table's edges
    ("change table style to only upper and lower borders bold",
     bordered(top=1.5, bottom=1.5, left=0.0, inside_v=0.0)),
    ("remove all borders from the table", bordered(top=0.0, bottom=0.0)),
    ("no vertical lines in the table", bordered(inside_v=0.0, top=0.5)),
    ("only the outer border of the table",
     bordered(top=0.5, left=0.5, inside_h=0.0, inside_v=0.0)),

    # a request that says what to keep and what to take away in one breath
    ("change the table layout only keep top and bottom borders bold "
     "removing the left and right one",
     bordered(top=1.5, bottom=1.5, left=0.0, right=0.0, inside_v=0.0)),
    # a table has one top and one bottom; a row has one each as well
    ("keep all the top and bottom borders",
     bordered(top=0.5, bottom=0.5, inside_h=0.5, inside_v=0.0)),
    ("top and bottom borders, no verticals",
     bordered(top=0.5, bottom=0.5, inside_v=0.0)),
    ("make the table borders thin", bordered(top=0.5, inside_v=0.5)),

    # the rule under the heading row, which Word has no word for
    ("add a rule under the header row", bordered(header=0.5)),
    ("bold the header row border and the last bottom one",
     bordered(header=1.5, bottom=1.5, top=0.0)),
    ("for tables keep borders top and bottom for all cells bold only the "
     "header cells and last bottom one",
     bordered(top=1.5, bottom=1.5, header=1.5, inside_h=1.5, inside_v=0.0)),

    # a phrase, wherever it is
    ("bold the word Adam wherever it appears", any_run_styled("Adam", bold=True)),
    ('italicise the phrase "older adults"', any_run_styled("older adults", italic=True)),

    # things that are not text
    ("remove the horizontal lines", gone(NodeType.HORIZONTAL_RULE)),

    # letter case, which changes no words
    ("make the headings uppercase",
     lambda g: [n.content for n in of_type(g, NodeType.HEADING)][0] == "I. INTRODUCTION"),
    ("lowercase the references",
     lambda g: of_type(g, NodeType.REFERENCE)[0].content.islower()),
    ("capitalise the captions",
     lambda g: of_type(g, NodeType.CAPTION)[0].content.startswith("Table 1.")),
    # "I. Introduction" is already sentence case — the full stop ends a
    # sentence — so this asks it of something where it shows.
    ("sentence case the captions",
     lambda g: of_type(g, NodeType.CAPTION)[1].content
     == "Figure 2: accuracy against volume."),

    # spacing, which the document has always carried
    ("double space the document",
     lambda g: all(n.metadata.get("line_spacing") == 2.0 for n in of_type(g, NodeType.BODY))),
    ("set the line spacing to 1.5",
     lambda g: of_type(g, NodeType.BODY)[0].metadata.get("line_spacing") == 1.5),
    ("single space the references",
     lambda g: of_type(g, NodeType.REFERENCE)[0].metadata.get("line_spacing") == 1.0),
    ("increase the space between paragraphs",
     lambda g: of_type(g, NodeType.BODY)[0].metadata.get("space_after_pt") == 12.0),

    # a typeface
    ("set the body font to Arial", styled(NodeType.BODY, font_family="Arial")),
    ("change the references font to Times New Roman",
     styled(NodeType.REFERENCE, font_family="Times New Roman")),

    # removing words rather than paragraphs
    ('delete the word "Adam"',
     lambda g: not any("Adam" in (n.content or "") for n in g.nodes())),

    # taking formatting off, which is asked for as often as putting it on
    ("remove the highlighting",
     lambda g: all(not n.style.highlight for n in g.nodes())),

    # the table's own headings
    ("make the headings in the table bold",
     lambda g: [n.style.bold for n in of_type(g, NodeType.TABLE_CELL)][:2] == [True, True]),
]


@pytest.mark.parametrize("command, check", MATRIX, ids=[c for c, _ in MATRIX])
def test_the_command_does_what_it_says(command: str, check: Check):
    assert check(run(command)), f"{command!r} did not do what it says"


def test_the_sweep_is_worth_running():
    """A guard on the guard: a shrinking matrix is a shrinking net."""
    assert len(MATRIX) >= 25
