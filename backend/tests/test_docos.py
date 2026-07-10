"""End-to-end tests for the DocOS engines.

Covers: DOCX parsing, action validation, execution + events, version engine
(snapshot/replay, undo/redo/rewind/diff) and the command engine heuristics.
Runs fully offline — no LLM provider is contacted (heuristic fallback is exercised).
"""
from __future__ import annotations

import io
import os
import tempfile

import pytest

from app.docos.actions import ActionValidationError, validate_batch
from app.docos.command import CommandEngine
from app.docos.execution import ExecutionEngine
from app.docos.graph import DocumentGraph, Node, NodeType
from app.docos.parser import parse_docx_bytes
from app.docos.versioning import VersionEngine
from app.docos.versioning.store import VersionStore


# ── fixtures ────────────────────────────────────────────────────────────────

def _sample_docx_bytes() -> bytes:
    from docx import Document

    doc = Document()
    doc.add_heading("Introduction", level=1)
    doc.add_paragraph("This is the first body paragraph.")
    doc.add_heading("Methodology", level=2)
    doc.add_paragraph("We used a rigorous approach.")
    table = doc.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "A"
    table.cell(1, 1).text = "D"
    doc.add_heading("References", level=1)
    doc.add_paragraph("Smith, J. (2020). A study.")
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _sample_graph() -> DocumentGraph:
    root = Node(type=NodeType.DOCUMENT, children=[
        Node(type=NodeType.HEADING, content="Intro"),
        Node(type=NodeType.BODY, content="Body one."),
        Node(type=NodeType.BODY, content="Body two."),
        Node(type=NodeType.FIGURE, children=[Node(type=NodeType.IMAGE, content="img")]),
        Node(type=NodeType.HORIZONTAL_RULE),
        Node(type=NodeType.REFERENCE, content="Ref 1"),
    ])
    return DocumentGraph(root=root, title="T")


@pytest.fixture()
def engine(tmp_path):
    store = VersionStore(db_path=tmp_path / "test.db")
    return VersionEngine(store=store)


# ── parser ──────────────────────────────────────────────────────────────────

def test_parser_classifies_nodes():
    graph = parse_docx_bytes(_sample_docx_bytes(), title="Sample")
    types = [n.type for n in graph.nodes()]
    assert NodeType.HEADING in types
    assert NodeType.SUBHEADING in types  # heading level 2
    assert NodeType.TABLE in types
    assert NodeType.REFERENCE in types   # paragraph after "References" heading
    tables = graph.find_by_types([NodeType.TABLE])
    assert tables and tables[0].metadata["cols"] == 2


# ── action validation ───────────────────────────────────────────────────────

def test_validate_rejects_unknown_target():
    with pytest.raises(ActionValidationError):
        validate_batch({"actions": [{"type": "select", "target": "banana"}]})


def test_validate_rejects_bulk_delete_without_confirm():
    with pytest.raises(ActionValidationError):
        validate_batch({"actions": [{"type": "delete", "target": "body"}]})


def test_validate_accepts_good_batch():
    batch = validate_batch({"actions": [
        {"type": "select", "target": "heading"},
        {"type": "format", "target": "heading", "style": {"bold": True, "font_size": 18}},
    ]})
    assert len(batch.actions) == 2


# ── execution ───────────────────────────────────────────────────────────────

def test_execution_formats_and_emits_events():
    graph = _sample_graph()
    batch = validate_batch({"actions": [
        {"type": "format", "target": "heading", "style": {"bold": True, "color": "#003366"}},
    ]})
    result = ExecutionEngine().execute(graph, batch)
    assert result.ok
    heading = result.graph.find_by_types([NodeType.HEADING])[0]
    assert heading.style.bold is True and heading.style.color == "#003366"
    names = {e.name.value for e in result.events}
    assert {"batch_started", "format_started", "format_finished", "batch_finished"} <= names
    # original graph untouched (execution works on a clone)
    assert graph.find_by_types([NodeType.HEADING])[0].style.bold is None


def test_execution_deletes_horizontal_rule():
    graph = _sample_graph()
    batch = validate_batch({"actions": [{"type": "delete", "target": "horizontal_rule"}]})
    result = ExecutionEngine().execute(graph, batch)
    assert result.ok
    assert not result.graph.find_by_types([NodeType.HORIZONTAL_RULE])


# ── version engine ──────────────────────────────────────────────────────────

def test_version_snapshot_replay_and_undo(engine):
    graph = _sample_graph()
    engine.init_document("doc1", "T", graph)

    # apply 12 edits so at least one non-checkpoint replay happens
    for i in range(12):
        g = engine.current_graph("doc1")
        batch = validate_batch({"actions": [
            {"type": "highlight", "target": "heading", "params": {"color": f"#00000{i%9}"}}
        ]})
        res = ExecutionEngine().execute(g, batch)
        engine.commit("doc1", batch, res.graph)

    hist = engine.history("doc1")
    assert len(hist) == 13                 # v0 import + 12 edits
    assert any(v.is_checkpoint and v.seq == 10 for v in hist)  # snapshot at seq 10

    # materialise a non-checkpoint version by replay
    mid = next(v for v in hist if v.seq == 7)
    g7 = engine.materialize(mid.id)
    assert g7.find_by_types([NodeType.HEADING])[0].style.highlight == "#000006"

    # undo moves pointer back one version
    info = engine.undo("doc1")
    assert info is not None and info.seq == 11
    redo = engine.redo("doc1")
    assert redo is not None and redo.seq == 12


def test_version_rewind_and_diff(engine):
    graph = _sample_graph()
    engine.init_document("doc2", "T", graph)
    g = engine.current_graph("doc2")
    batch = validate_batch({"actions": [
        {"type": "format", "target": "heading", "style": {"font_size": 22}}]})
    res = ExecutionEngine().execute(g, batch)
    v1 = engine.commit("doc2", batch, res.graph)

    diff = engine.diff(engine.history("doc2")[0].id, v1.id)
    assert diff.changed and diff.changed[0]["style"]["after"]["font_size"] == 22

    back = engine.rewind("doc2", engine.history("doc2")[0].id)
    assert back.seq == 0
    assert engine.current_graph("doc2").find_by_types([NodeType.HEADING])[0].style.font_size is None


# ── command engine (offline heuristics) ─────────────────────────────────────

def test_command_engine_heuristics():
    # force heuristic path by injecting a router that always fails
    class DeadRouter:
        def chat(self, *a, **k):
            raise RuntimeError("no providers")

    ce = CommandEngine(router=DeadRouter())
    graph = _sample_graph()

    r = ce.parse("Highlight all figures", graph)
    assert r.kind == "actions" and r.source == "heuristic"
    assert r.batch.actions[0].type.value == "highlight"

    r2 = ce.parse("Remove every horizontal line", graph)
    assert r2.batch.actions[0].type.value == "delete"
    assert r2.batch.actions[0].target == "horizontal_rule"

    r3 = ce.parse("Undo", graph)
    assert r3.kind == "control" and r3.control.kind == "undo"

    r4 = ce.parse("Rewind to version 8", graph)
    assert r4.control.kind == "rewind" and r4.control.params["seq"] == 8
