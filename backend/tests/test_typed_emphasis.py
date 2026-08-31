"""Emphasis a model typed instead of applying.

Asked to bold and capitalise the table headers, the rewriter answered
`**COMPONENT**`, and the header read `**COMPONENT**` on the page: this
document is a Word document, where an asterisk is an asterisk.
"""
from __future__ import annotations

import pytest

from app.docos.actions import validate_batch
from app.docos.execution.engine import ExecutionEngine
from app.docos.execution.markdown import strip_emphasis
from app.docos.graph import DocumentGraph, Node, NodeType


@pytest.mark.parametrize("text, cleaned", [
    ("**COMPONENT**", "COMPONENT"),
    ("__CONFIGURATION__", "CONFIGURATION"),
    ("***both***", "both"),
    ("The **model** was trained", "The model was trained"),
    ("a `code` span", "a code span"),
])
def test_markers_are_taken_off_the_text(text, cleaned):
    assert strip_emphasis(text)[0] == cleaned


@pytest.mark.parametrize("text", [
    "2 * 3 * 4 = 24",              # arithmetic, not emphasis
    "snake_case_name stays",       # an identifier, not italics
    "plain text",
    "a * b",
])
def test_text_that_only_looks_like_markup_is_left_alone(text):
    assert strip_emphasis(text) == (text, [])


def test_the_emphasis_becomes_real_formatting():
    cell = Node(type=NodeType.TABLE_CELL, content="COMPONENT")
    graph = DocumentGraph(root=Node(type=NodeType.DOCUMENT, children=[cell]), title="t")
    batch = validate_batch({"reasoning": "t", "actions": [
        {"type": "rewrite", "target": "body",
         "params": {"edits": {cell.id: "**COMPONENT**"}}}]})

    result = ExecutionEngine().execute(graph, batch)
    after = next(n for n in result.graph.nodes() if n.type is NodeType.TABLE_CELL)
    assert after.content == "COMPONENT"
    assert after.style.bold is True


def test_emphasis_inside_a_sentence_formats_only_those_words():
    body = Node(type=NodeType.BODY, content="The model was trained")
    graph = DocumentGraph(root=Node(type=NodeType.DOCUMENT, children=[body]), title="t")
    batch = validate_batch({"reasoning": "t", "actions": [
        {"type": "rewrite", "target": "body",
         "params": {"edits": {body.id: "The **model** was trained"}}}]})

    result = ExecutionEngine().execute(graph, batch)
    after = next(n for n in result.graph.nodes() if n.type is NodeType.BODY)
    assert after.content == "The model was trained"
    assert [(r.text, bool(r.style and r.style.bold)) for r in after.runs] == [
        ("The ", False), ("model", True), (" was trained", False)]
