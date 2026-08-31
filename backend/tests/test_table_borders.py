"""A table's rules: read from the file, changed by a command, written back.

"Change the table style to only upper and lower borders, bold" reported that
nothing changed — correctly, since nothing in the system knew a table had
edges. The renderer drew a full grid on every cell whatever the document said,
and the exporter always wrote Table Grid.
"""
from __future__ import annotations

import io

import pytest
from docx import Document

from app.docos.actions import validate_batch
from app.docos.command.engine import CommandEngine
from app.docos.execution.engine import ExecutionEngine
from app.docos.export import graph_to_docx_bytes
from app.docos.graph import DocumentGraph, Node, NodeType
from app.docos.parser import parse_docx_bytes

RULES_ONLY = {"top": 1.5, "bottom": 1.5, "left": 0.0,
              "right": 0.0, "inside_h": 0.0, "inside_v": 0.0}


def _table_graph(borders: dict | None = None) -> DocumentGraph:
    cells = [Node(type=NodeType.TABLE_CELL, content=t)
             for t in ("COMPONENT", "CONFIGURATION")]
    table = Node(type=NodeType.TABLE,
                 metadata={"borders": borders} if borders else {},
                 children=[Node(type=NodeType.TABLE_ROW, children=cells)])
    return DocumentGraph(root=Node(type=NodeType.DOCUMENT, children=[table]), title="t")


def _borders_of(graph: DocumentGraph) -> dict | None:
    table = next(n for n in graph.nodes() if n.type is NodeType.TABLE)
    return table.metadata.get("borders")


def _run(graph: DocumentGraph, **params) -> DocumentGraph:
    batch = validate_batch({"reasoning": "t", "actions": [
        {"type": "border", "target": "table", "params": params}]})
    result = ExecutionEngine().execute(graph, batch)
    assert result.ok, result.error
    return result.graph


# ── the words people use ─────────────────────────────────────────────────────

@pytest.mark.parametrize("command, sides, width", [
    ("change table style to only upper and lower borders bold", ["top", "bottom"], 1.5),
    ("remove all borders from the table", [], 0.0),
    ("only the outer border of the table", ["outside"], 0.5),
    ("make the table borders thin", [], 0.5),
    ("remove the table gridlines", [], 0.0),
])
def test_a_request_about_the_rules_becomes_a_border_action(command, sides, width):
    action = CommandEngine()._heuristic_actions(command).actions[0]
    assert action.type.value == "border"
    assert action.target == "table"
    assert action.params["sides"] == sides
    assert action.params["width"] == width


def test_taking_one_kind_away_leaves_the_others():
    """"No vertical lines" is not "no lines"."""
    action = CommandEngine()._heuristic_actions("no vertical lines in the table").actions[0]
    assert action.params["sides"] == ["top", "bottom", "left", "right", "inside_h"]
    assert action.params["width"] == 0.5


def test_horizontal_lines_outside_a_table_are_still_the_page_rules():
    action = CommandEngine()._heuristic_actions("remove the horizontal lines").actions[0]
    assert action.type.value == "delete"
    assert action.target == "horizontal_rule"


# ── the action ───────────────────────────────────────────────────────────────

def test_naming_sides_means_those_and_no_others():
    graph = _run(_table_graph(), sides=["top", "bottom"], width=1.5)
    assert _borders_of(graph) == RULES_ONLY


def test_naming_none_means_all_of_them():
    graph = _run(_table_graph(), sides=[], width=1.0)
    assert set(_borders_of(graph).values()) == {1.0}


def test_outside_names_the_four_edges_around_it():
    graph = _run(_table_graph(), sides=["outside"], width=0.5)
    borders = _borders_of(graph)
    assert [borders[s] for s in ("top", "bottom", "left", "right")] == [0.5] * 4
    assert [borders[s] for s in ("inside_h", "inside_v")] == [0.0, 0.0]


def test_asking_twice_changes_nothing_the_second_time():
    once = _run(_table_graph(), sides=["top"], width=1.5)
    assert _borders_of(_run(once, sides=["top"], width=1.5)) == _borders_of(once)


# ── through Word ─────────────────────────────────────────────────────────────

def test_borders_survive_a_round_trip_through_the_file():
    exported = graph_to_docx_bytes(_table_graph(RULES_ONLY))
    assert _borders_of(parse_docx_bytes(exported, title="t")) == RULES_ONLY


def test_a_documents_own_borders_are_read():
    doc = Document()
    table = doc.add_table(rows=1, cols=2)
    table.style = "Table Grid"
    buf = io.BytesIO()
    doc.save(buf)

    graph = parse_docx_bytes(buf.getvalue(), title="t")
    # Table Grid states its edges in the style, not on the table, and a table
    # that states nothing states nothing — the empty answer means "as the style
    # has it", not "no borders".
    assert _borders_of(graph) in (None, {})
