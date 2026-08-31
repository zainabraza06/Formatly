"""The line under Done says what happened to the document."""
from __future__ import annotations

import pytest

from app.docos.actions import validate_batch
from app.docos.command.describe import describe_outcome
from app.docos.graph import Node, NodeType


def nodes(kind: NodeType, count: int) -> list[Node]:
    return [Node(type=kind) for _ in range(count)]


def described(action: dict, changed: list[Node], section: str | None = None) -> str:
    return describe_outcome(
        validate_batch({"reasoning": "the planner's own note", "actions": [action]}),
        changed, section)


def test_quoted_words_are_named_not_counted():
    got = described(
        {"type": "format", "target": "body", "style": {"bold": True},
         "params": {"spans": [{"id": "1", "text": "4.2 million"},
                              {"id": "1", "text": "11.3 per cent"}]}},
        nodes(NodeType.BODY, 1), "Abstract")
    assert got == "Bolded “4.2 million” and “11.3 per cent” in Abstract."


def test_a_long_list_of_spans_is_cut_short_without_two_ands():
    got = described(
        {"type": "format", "target": "body", "style": {"bold": True},
         "params": {"spans": [{"id": "1", "text": t} for t in "abcdef"]}},
        nodes(NodeType.BODY, 1))
    assert got == "Bolded “a”, “b”, “c” and 3 more."


def test_things_are_named_by_what_they_are_not_by_the_target():
    """A colour applied to a table lands on its cells, and says so."""
    got = described({"type": "format", "target": "table", "style": {"color": "#2e7d32"}},
                    nodes(NodeType.TABLE_CELL, 12))
    assert got == "Coloured 12 cells."


@pytest.mark.parametrize("action, changed, expected", [
    ({"type": "list", "target": "body", "params": {"kind": "bullet"}},
     (NodeType.BODY, 4), "Bulleted 4 paragraphs."),
    ({"type": "list", "target": "body", "params": {"kind": "none"}},
     (NodeType.BODY, 3), "Took the bullets off 3 paragraphs."),
    ({"type": "align", "target": "caption", "params": {"alignment": "center"}},
     (NodeType.CAPTION, 2), "Centred 2 captions."),
    ({"type": "resize", "target": "reference", "params": {"font_size": 9}},
     (NodeType.REFERENCE, 3), "Set 3 references to 9 pt."),
    ({"type": "resize", "target": "title", "params": {"scale": 1.25}},
     (NodeType.HEADING, 1), "Made 1 heading larger."),
    ({"type": "delete", "target": "horizontal_rule"},
     (NodeType.HORIZONTAL_RULE, 2), "Deleted 2 lines."),
    ({"type": "render_maths", "params": {"on": True}},
     (NodeType.BODY, 0), "Drew the equations as mathematics."),
])
def test_each_kind_of_action_says_what_it_did(action, changed, expected):
    assert described(action, nodes(*changed)) == expected


def test_the_section_is_not_said_twice():
    got = described({"type": "resize", "target": "reference", "params": {"font_size": 9}},
                    nodes(NodeType.REFERENCE, 3), "References")
    assert got == "Set 3 references to 9 pt."


def test_nothing_to_say_is_said_as_nothing():
    assert describe_outcome(validate_batch({"reasoning": "", "actions": [
        {"type": "select", "target": "heading"}]}), []) == "Selected headings."
