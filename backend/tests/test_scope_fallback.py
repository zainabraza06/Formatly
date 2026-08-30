"""When no rule recognises what a request is about, the document is read.

The rules cover the requests they were written for. "Centre the fig captions
wherever present" and "make the header cells capitalised" are not among them,
and each used to come back as "nothing matched, so nothing changed". The
fallback asks the document which parts the instruction is about, and runs the
same plan against those.
"""
from __future__ import annotations

import json

import anyio

from app.docos.command.scope import resolve_nodes
from app.docos.graph import DocumentGraph, Node, NodeType
from app.docos.service import DocOSService
from app.docos.versioning import VersionEngine
from app.docos.versioning.store import VersionStore


class _Router:
    """A router that answers with the ids of whatever it is told to pick."""

    def __init__(self, pick):
        self.pick = pick
        self.calls = 0

    def chat(self, messages, **_kw):
        self.calls += 1
        parts = json.loads(messages[-1]["content"])["parts"]
        ids = [p["id"] for p in parts if self.pick(p)]
        return json.dumps({"ids": ids}), "stub", 0.0


class _DeadRouter:
    def chat(self, *_a, **_kw):
        raise RuntimeError("all providers failed")


def _graph() -> DocumentGraph:
    root = Node(type=NodeType.DOCUMENT)
    root.children = [
        Node(type=NodeType.HEADING, content="Results"),
        Node(type=NodeType.BODY, content="Accuracy reached 91.2% on the held-out set."),
        Node(type=NodeType.BODY, content="Fig. 3: accuracy against window length."),
    ]
    return DocumentGraph(root=root, title="t")


def test_resolve_nodes_returns_only_ids_that_are_in_the_document():
    graph = _graph()
    router = _Router(lambda p: p["text"].startswith("Fig."))
    found = resolve_nodes("centre the fig captions", graph, router=router)

    assert [graph.get(i).content for i in found] == [
        "Fig. 3: accuracy against window length."]


def test_resolve_nodes_drops_ids_the_model_invented():
    graph = _graph()

    class _Liar:
        def chat(self, *_a, **_kw):
            return json.dumps({"ids": ["no-such-node", 7, None]}), "stub", 0.0

    assert resolve_nodes("anything", graph, router=_Liar()) == []


def test_resolve_nodes_survives_a_provider_that_is_down():
    assert resolve_nodes("anything", _graph(), router=_DeadRouter()) == []


def test_a_command_no_rule_matched_is_answered_by_reading(tmp_path, monkeypatch):
    """The whole path: a plan that reaches nothing, then the document read."""
    service = DocOSService(versions=VersionEngine(
        store=VersionStore(db_path=tmp_path / "scope.db")))
    service.versions.init_document("d", "D", _graph(), owner_id="u")

    router = _Router(lambda p: p["text"].startswith("Fig."))
    monkeypatch.setattr("app.services.router.get_router", lambda: router)

    events: list[dict] = []

    async def emit(message):
        events.append(message)

    async def run():
        # A plan that resolves to nothing: this document has no caption nodes.
        return await service.run_command(
            "d", "centre the fig captions wherever present", emit, owner_id="u")

    # The planner is not available in a test, so the heuristic plans it; what
    # matters is that a plan reaching nothing is not the end of the request.
    monkeypatch.setattr(service.commands, "_llm_actions",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("offline")))
    result = anyio.run(run)

    assert result["ok"] is True, result
    names = [e.get("event") for e in events]
    assert "scope_search_finished" in names

    graph = service.versions.current_graph("d")
    centred = [n.content for n in graph.nodes() if n.style.alignment == "center"]
    assert centred == ["Fig. 3: accuracy against window length."]


def test_a_command_that_still_finds_nothing_says_so(tmp_path, monkeypatch):
    service = DocOSService(versions=VersionEngine(
        store=VersionStore(db_path=tmp_path / "none.db")))
    service.versions.init_document("d", "D", _graph(), owner_id="u")

    monkeypatch.setattr("app.services.router.get_router",
                        lambda: _Router(lambda _p: False))
    monkeypatch.setattr(service.commands, "_llm_actions",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("offline")))

    async def emit(_message):
        pass

    result = anyio.run(lambda: service.run_command(
        "d", "centre the fig captions wherever present", emit, owner_id="u"))

    assert result["ok"] is False
    assert "nothing" in result["error"]
