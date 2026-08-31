"""What the system can do when no model can be reached.

The planner is unavailable often enough — a provider outage, a rate limit, an
offline machine — that the rule-based path is not a token fallback. It is what
carries out ordinary instructions, so these are the instructions it has to
understand: a class of thing, a named part, a phrase, and the several ways
people ask for each.
"""
from __future__ import annotations

import pytest

from app.docos.command.engine import CommandEngine
from app.docos.execution.engine import ExecutionEngine
from app.docos.graph import DocumentGraph, Node, NodeType, Style


def plan(command: str):
    batch = CommandEngine()._heuristic_actions(command)
    assert len(batch.actions) == 1, command
    return batch.actions[0]


@pytest.mark.parametrize("command, kind, target, params, style", [
    # alignment, in the ways people write it
    ("right align the references", "align", "reference", {"alignment": "right"}, {}),
    ("align the captions to the left", "align", "caption", {"alignment": "left"}, {}),
    ("centre every caption", "align", "caption", {"alignment": "center"}, {}),
    ("justify the body text", "align", "body", {"alignment": "justify"}, {}),
    # size, absolute and relative
    ("change the references to font size 9", "resize", "reference", {"font_size": 9.0}, {}),
    ("make the title larger", "resize", "title", {"scale": 1.25}, {}),
    ("make the subheadings smaller", "resize", "subheading", {"scale": 0.8}, {}),
    # colour
    ("make the headings blue", "format", "heading", {}, {"color": "#1f4e79"}),
    ("colour the captions green", "format", "caption", {}, {"color": "#2e7d32"}),
    # several attributes at once
    ("make the headings bold and italic", "format", "heading", {},
     {"bold": True, "italic": True}),
    # lists
    ("number the recommendations", "list", "body", {"kind": "number"}, {}),
    ("put the objectives in bullets", "list", "body", {"kind": "bullet"}, {}),
])
def test_a_request_becomes_the_action_it_asks_for(command, kind, target, params, style):
    action = plan(command)
    assert action.type.value == kind
    assert action.target == target
    for key, value in params.items():
        assert action.params.get(key) == value
    assert (action.style.model_dump(exclude_none=True) if action.style else {}) == style


def test_a_quoted_phrase_is_looked_for_everywhere():
    """"Bold Midlands wherever it appears" is not a request about headings."""
    action = plan("bold the word Midlands wherever it appears")
    assert action.target == "document"
    assert action.params["find"] == "Midlands"
    assert action.style.bold is True


def test_a_named_scope_still_wins_over_the_whole_document():
    action = plan('italicise the phrase "per parcel" in the captions')
    assert action.target == "caption"
    assert action.params["find"] == "per parcel"


def test_a_caption_of_a_table_is_a_caption():
    """Both nouns are in the sentence; the request is about the caption."""
    assert plan("centre the table 1 caption").target == "caption"


def test_the_title_is_not_every_heading():
    graph = DocumentGraph(root=Node(type=NodeType.DOCUMENT, children=[
        Node(type=NodeType.HEADING, content="Annual Review"),
        Node(type=NodeType.HEADING, content="Objectives"),
    ]), title="t")
    assert [n.content for n in graph.resolve_target("title")] == ["Annual Review"]


def test_larger_moves_each_node_from_the_size_it_has():
    graph = DocumentGraph(root=Node(type=NodeType.DOCUMENT, children=[
        Node(type=NodeType.BODY, content="a", style=Style(font_size=10)),
        Node(type=NodeType.BODY, content="b", style=Style(font_size=20)),
    ]), title="t")
    from app.docos.actions import validate_batch

    batch = validate_batch({"reasoning": "t", "actions": [
        {"type": "resize", "target": "body", "params": {"scale": 1.25}}]})
    result = ExecutionEngine().execute(graph, batch)
    assert [n.style.font_size for n in result.graph.nodes()
            if n.type is NodeType.BODY] == [12.5, 25.0]


def test_formatting_a_table_reaches_the_cells():
    cells = [Node(type=NodeType.TABLE_CELL, content=t) for t in ("Region", "96.8")]
    graph = DocumentGraph(root=Node(type=NodeType.DOCUMENT, children=[
        Node(type=NodeType.TABLE, children=[
            Node(type=NodeType.TABLE_ROW, children=cells)]),
    ]), title="t")
    from app.docos.actions import validate_batch

    batch = validate_batch({"reasoning": "t", "actions": [
        {"type": "format", "target": "table", "style": {"color": "#2e7d32"}}]})
    result = ExecutionEngine().execute(graph, batch)
    assert [n.style.color for n in result.graph.nodes()
            if n.type is NodeType.TABLE_CELL] == ["#2e7d32", "#2e7d32"]
