"""A bold phrase in a paragraph that also holds an equation.

"Bold the results in the abstract" reported bolding six figures and nothing on
the page changed. The model was right — the runs carried the bold — but the
renderer gave up a paragraph's inline formatting whenever it drew an equation,
and with maths rendering switched on that was every paragraph in the document.

The backend half is asserted here; `test_renderer_covers_the_model` asserts
that the page reads what the backend writes.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.docos.actions import validate_batch
from app.docos.execution.engine import ExecutionEngine
from app.docos.graph import DocumentGraph, Node, NodeType

NODE_VIEW = (Path(__file__).resolve().parents[2] / "frontend" / "src"
             / "components" / "docos" / "NodeView.tsx")

ABSTRACT = ("We report 89.01% ± 0.47% accuracy, with $F_1 = 0.88$ across "
            "subjects and 90.10% on the held-out split.")


def abstract_graph() -> DocumentGraph:
    return DocumentGraph(root=Node(type=NodeType.DOCUMENT, children=[
        Node(type=NodeType.BODY, content=ABSTRACT)]), title="paper")


def bolded(*phrases: str) -> Node:
    spans = [{"id": "", "text": p} for p in phrases]
    graph = abstract_graph()
    node = graph.root.children[0]
    for span in spans:
        span["id"] = node.id
    batch = validate_batch({"reasoning": "t", "actions": [
        {"type": "format", "target": "body", "style": {"bold": True},
         "params": {"spans": spans}}]})
    result = ExecutionEngine().execute(graph, batch)
    assert result.ok, result.error
    return next(n for n in result.graph.nodes() if n.type is NodeType.BODY)


def test_the_figures_are_bolded_and_the_words_are_not():
    node = bolded("89.01% ± 0.47%", "90.10%")
    bold = [r.text for r in node.runs if r.style.bold]
    assert bold == ["89.01% ± 0.47%", "90.10%"]
    assert "".join(r.text for r in node.runs) == ABSTRACT


def test_the_equation_is_left_whole():
    """A span that lands beside an equation must not cut it in half."""
    node = bolded("89.01% ± 0.47%")
    assert "$F_1 = 0.88$" in "".join(r.text for r in node.runs)


@pytest.mark.skipif(not NODE_VIEW.exists(), reason="frontend not present")
def test_the_renderer_draws_runs_on_the_maths_path_too():
    """The maths branch used to return before it ever looked at the runs."""
    source = NODE_VIEW.read_text(encoding="utf-8")
    maths_branch = source.split("const known = knownEquations(node)")[1]
    maths_branch = maths_branch.split("function RunSpan")[0]
    assert "inlineRuns(node)" in maths_branch, (
        "the maths branch of Text() never reads the runs, so a bold phrase in "
        "a paragraph with an equation cannot be drawn")
