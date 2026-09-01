"""Three different requests about size, only one of which names a size.

"Increase the headings by 2" was read as "set the headings to 2 pt" — the step
taken for the size — and every heading in the document came out in 2 pt type.
"""
from __future__ import annotations

import pytest

from app.docos.actions import validate_batch
from app.docos.command.engine import CommandEngine
from app.docos.execution.engine import ExecutionEngine
from app.docos.graph import DocumentGraph, Node, NodeType, Style


def plan(command: str):
    return CommandEngine()._heuristic_actions(command).actions[0]


def headings(*sizes: float) -> DocumentGraph:
    return DocumentGraph(root=Node(type=NodeType.DOCUMENT, children=[
        Node(type=NodeType.HEADING, content=f"H{i}", style=Style(font_size=s))
        for i, s in enumerate(sizes)]), title="t")


def sizes_after(graph: DocumentGraph, **params) -> list[float]:
    batch = validate_batch({"reasoning": "t", "actions": [
        {"type": "resize", "target": "heading", "params": params}]})
    result = ExecutionEngine().execute(graph, batch)
    assert result.ok, result.error
    return [n.style.font_size for n in result.graph.nodes()
            if n.type is NodeType.HEADING]


# ── reading the request ──────────────────────────────────────────────────────

@pytest.mark.parametrize("command, expected", [
    ("select all headings increase font by 2 units", {"delta": 2.0}),
    ("increase the heading font by 2", {"delta": 2.0}),
    ("increase headings by 2 pt", {"delta": 2.0}),
    ("make the headings 2 points smaller", {"delta": -2.0}),
    ("reduce the headings by 1", {"delta": -1.0}),
    ("change the headings to font size 9", {"font_size": 9.0}),
    ("make the headings larger", {"scale": 1.25}),
])
def test_a_step_is_not_a_size(command, expected):
    assert plan(command).params == expected


# ── carrying it out ──────────────────────────────────────────────────────────

def test_a_step_moves_each_thing_from_the_size_it_has():
    """12 becomes 14, 20 becomes 22 — the document's hierarchy is kept."""
    assert sizes_after(headings(12, 20), delta=2) == [14.0, 22.0]


def test_a_negative_step_goes_the_other_way():
    assert sizes_after(headings(12, 20), delta=-2) == [10.0, 18.0]


def test_a_size_is_still_a_size():
    assert sizes_after(headings(12, 20), font_size=16) == [16.0, 16.0]


def test_a_size_too_small_to_be_one_is_read_as_the_step_it_was():
    """A planner that reads "by 2" as font_size=2 would set 2 pt type; no
    document does that, so the number is taken as the step it plainly is."""
    assert sizes_after(headings(12, 20), font_size=2) == [14.0, 22.0]


def test_a_step_cannot_shrink_text_out_of_existence():
    assert sizes_after(headings(5), delta=-20) == [4.0]
