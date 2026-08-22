"""Rewriting a document's words, page by page.

The command planner is shown node counts and headings, never prose, so an
instruction about the text could not be answered — and the run reported Done
regardless. These cover the pieces that make such an instruction work, and the
report that says so when it does not.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.docos.actions import Action, ActionBatch, ActionType  # noqa: E402
from app.docos.command.rewriter import passes, rewritable, rewrite_nodes  # noqa: E402
from app.docos.execution import ExecutionEngine  # noqa: E402
from app.docos.graph import DocumentGraph, Node, NodeType  # noqa: E402


def build(*bodies: str) -> DocumentGraph:
    root = Node(type=NodeType.DOCUMENT)
    root.children.append(Node(type=NodeType.HEADING, content="H", metadata={"level": 1}))
    for text in bodies:
        root.children.append(Node(type=NodeType.BODY, content=text))
    root.children.append(Node(type=NodeType.TABLE))
    return DocumentGraph(root=root, title="t")


class FakeRouter:
    """Replies with a scripted body per call, and records what it was sent."""

    def __init__(self, *replies: str):
        self.replies = list(replies)
        self.sent: list[str] = []

    def chat(self, messages, max_tokens=None, **_kw):
        self.sent.append(messages[-1]["content"])
        reply = self.replies[min(len(self.sent) - 1, len(self.replies) - 1)]
        return reply, "fake", 0.1


# ── scope ───────────────────────────────────────────────────────────────────

def test_only_prose_nodes_are_in_scope():
    graph = build("one", "two")
    nodes = rewritable(graph, [], None)
    assert [n.type for n in nodes] == [NodeType.HEADING, NodeType.BODY, NodeType.BODY]
    assert all(n.type is not NodeType.TABLE for n in nodes)


def test_empty_nodes_are_skipped():
    graph = build("real text", "   ")
    assert [n.content for n in rewritable(graph, [], "body")] == ["real text"]


# ── passes ──────────────────────────────────────────────────────────────────

def test_a_long_document_is_cut_into_passes():
    """One prompt carrying a whole paper truncates, and the middle goes unedited."""
    graph = build(*["x" * 400 for _ in range(30)])
    nodes = rewritable(graph, [], "body")
    batches = passes(nodes, budget=2000)
    assert len(batches) > 1
    assert sum(len(b) for b in batches) == len(nodes), "no node may be dropped"


def test_a_page_boundary_starts_a_new_pass():
    graph = build("a", "b")
    graph.root.children[2].metadata["page_break_before"] = True
    batches = passes(rewritable(graph, [], "body"), budget=10_000)
    assert len(batches) == 2


# ── the model round trip ────────────────────────────────────────────────────

def test_returned_text_becomes_an_edit():
    graph = build("$x$ is the value")
    node = graph.root.children[1]
    router = FakeRouter('{"edits": [{"id": "%s", "text": "x is the value"}]}' % node.id)

    edits, failures = rewrite_nodes(graph, [node], "de-latex", router=router)
    assert edits == {node.id: "x is the value"}
    assert failures == []


def test_the_text_is_actually_sent():
    """The planner never sees prose; this pass must."""
    graph = build("a distinctive sentence")
    node = graph.root.children[1]
    router = FakeRouter('{"edits": []}')
    rewrite_nodes(graph, [node], "do something", router=router)
    assert "a distinctive sentence" in router.sent[0]


@pytest.mark.parametrize("reply", [
    '{"edits": [{"id": "unknown-id", "text": "hello"}]}',   # not in this pass
    '{"edits": [{"id": "%s", "text": "   "}]}',             # would erase the node
    '{"edits": [{"id": "%s", "text": "unchanged"}]}',       # identical to the original
])
def test_unusable_edits_are_ignored(reply):
    graph = build("unchanged")
    node = graph.root.children[1]
    router = FakeRouter(reply.replace("%s", node.id) if "%s" in reply else reply)
    edits, _ = rewrite_nodes(graph, [node], "x", router=router)
    assert edits == {}


def test_a_failed_pass_is_reported_not_swallowed():
    graph = build("a", "b")
    router = FakeRouter("not json at all")
    edits, failures = rewrite_nodes(graph, rewritable(graph, [], "body"), "x", router=router)
    assert edits == {}
    assert failures and "pass 1" in failures[0]


def test_one_failed_pass_does_not_lose_the_others():
    # comfortably over the pass budget, so there really are two passes
    graph = build(*["y" * 400 for _ in range(30)])
    nodes = rewritable(graph, [], "body")
    assert len(passes(nodes)) > 1
    good = '{"edits": [{"id": "%s", "text": "edited"}]}' % nodes[-1].id
    router = FakeRouter("garbage", good)
    edits, failures = rewrite_nodes(graph, nodes, "x", router=router)
    assert len(failures) >= 1
    assert edits, "a later pass must still be applied"


# ── replay ──────────────────────────────────────────────────────────────────

def test_the_action_carries_its_edits_so_replay_is_deterministic():
    """A version is stored as its action log and replayed. Asking the model
    again would give different words, so the resolved text travels with it."""
    graph = build("before")
    node = graph.root.children[1]
    batch = ActionBatch(actions=[
        Action(type=ActionType.REWRITE, target="body", params={"edits": {node.id: "after"}}),
    ])

    result = ExecutionEngine().execute(graph, batch)
    assert result.ok
    assert result.graph.get(node.id).content == "after"
    # replaying the same log gives the same document
    again = ExecutionEngine().execute(graph, batch)
    assert again.graph.get(node.id).content == "after"


def test_a_rewrite_without_edits_changes_nothing_and_does_not_fail():
    graph = build("before")
    batch = ActionBatch(actions=[Action(type=ActionType.REWRITE, target="body")])
    result = ExecutionEngine().execute(graph, batch)
    assert result.ok
    assert result.graph.get(graph.root.children[1].id).content == "before"
