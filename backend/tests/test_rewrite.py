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


def test_table_cells_are_in_scope():
    """A paper's display equations sit in a one-row table, equation then number,
    so a rewrite that skips cells reaches none of the equations."""
    graph = DocumentGraph(root=Node(type=NodeType.DOCUMENT, children=[
        Node(type=NodeType.BODY, content="The objective is defined below."),
        Node(type=NodeType.TABLE, children=[
            Node(type=NodeType.TABLE_ROW, children=[
                Node(type=NodeType.TABLE_CELL, content=r"$\mathcal{L} = -\sum y_i$"),
                Node(type=NodeType.TABLE_CELL, content="(1)"),
            ]),
        ]),
        Node(type=NodeType.CAPTION, content=r"Figure 1. $x = rac{a}{b}$ per channel."),
    ]))

    scoped = rewritable(graph, [], None)
    kinds = [n.type for n in scoped]
    assert NodeType.TABLE_CELL in kinds
    assert NodeType.CAPTION in kinds
    assert NodeType.TABLE not in kinds, "the table itself holds no text of its own"

    # Targeting the body alone still means the body alone.
    assert [n.type for n in rewritable(graph, [], "body")] == [NodeType.BODY]


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
    """A pass whose replies never parse is reported, and the rest still apply."""
    # comfortably over the pass budget, so there really are two passes
    graph = build(*["y" * 400 for _ in range(30)])
    nodes = rewritable(graph, [], "body")
    assert len(passes(nodes)) > 1
    doomed = passes(nodes)[0][0].id

    class Router:
        """Nothing usable for the first pass, however often it is asked."""

        def __init__(self):
            self.sent = []

        def chat(self, messages, max_tokens=None, **_kw):
            body = messages[-1]["content"]
            self.sent.append(body)
            if doomed in body:
                return "garbage", "fake", 0.1
            nid = next(n.id for n in nodes if n.id in body)
            return '{"edits": [{"id": "%s", "text": "edited"}]}' % nid, "fake", 0.1

    edits, failures = rewrite_nodes(graph, nodes, "x", router=Router())

    assert failures, "the pass that never answered usefully is reported"
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


# ── whose scope is it ───────────────────────────────────────────────────────

def test_a_request_that_names_no_part_of_the_document_is_not_narrowed():
    """The planner fills in a target whether or not the request named one, and
    it nearly always guesses "body". Only the request may narrow the scope."""
    from app.docos.service import _names_a_scope

    assert not _names_a_scope("convert all latex equations into readable maths")
    assert not _names_a_scope("shorten everything")
    assert not _names_a_scope("fix the spelling")

    assert _names_a_scope("make the body paragraphs more concise")
    assert _names_a_scope("reword every figure caption")
    assert _names_a_scope("rewrite the abstract")
    assert _names_a_scope("tidy up the references")


# ── a reply that did not survive the trip ───────────────────────────────────

def test_a_truncated_reply_keeps_what_arrived_and_asks_again_for_the_rest():
    """A conversion can be longer than what it converts, so a pass that fits
    going in can overrun the reply ceiling coming back and be cut mid-JSON."""
    graph = build("alpha", "beta", "gamma")
    nodes = rewritable(graph, [], "body")
    ids = [n.id for n in nodes]

    cut = '{"edits": [{"id": "%s", "text": "ALPHA"}, {"id": "%s", "text": "BET' % (ids[0], ids[1])
    whole = '{"edits": [{"id": "%s", "text": "BETA"}, {"id": "%s", "text": "GAMMA"}]}' % (ids[1], ids[2])
    router = FakeRouter(cut, whole)

    edits, failures = rewrite_nodes(graph, nodes, "shout", router=router)

    assert edits[ids[0]] == "ALPHA", "the finished edit in the cut reply is kept"
    assert edits[ids[1]] == "BETA", "the unfinished one is asked for again"
    assert edits[ids[2]] == "GAMMA"
    assert not failures
    assert len(router.sent) > 1, "the nodes it missed were retried"


def test_a_node_that_never_comes_back_is_reported_not_silently_skipped():
    graph = build("alpha", "beta")
    nodes = rewritable(graph, [], "body")
    router = FakeRouter("not json at all")

    edits, failures = rewrite_nodes(graph, nodes, "shout", router=router)

    assert edits == {}
    assert failures, "the caller has to be able to say what was not edited"


def test_a_retry_only_asks_about_the_nodes_a_broken_reply_missed():
    """Retries are for a reply that arrived damaged. A whole reply is final,
    however few nodes it mentions."""
    graph = build("alpha", "beta", "gamma", "delta")
    nodes = rewritable(graph, [], "body")
    ids = [n.id for n in nodes]

    # Cut mid-string: the first edit is complete, the rest never arrived.
    cut = '{"edits": [{"id": "%s", "text": "ALPHA"}, {"id": "%s", "text": "BET' % (ids[0], ids[1])
    rest = '{"edits": [%s]}' % ", ".join(
        '{"id": "%s", "text": "X"}' % nid for nid in ids[1:])
    router = FakeRouter(cut, rest, rest, rest)

    rewrite_nodes(graph, nodes, "shout", router=router)

    retries = " ".join(router.sent[1:])
    assert ids[0] not in retries, "a node already edited is not asked about again"
    for nid in ids[1:]:
        assert nid in retries, "every node the broken reply missed is asked about again"


# ── reading a document once ─────────────────────────────────────────────────

def test_reading_records_what_each_section_is_about():
    from app.docos.command.reading import brief_with_reading, read_document
    from app.docos.graph import DocumentGraph, Node, NodeType

    graph = DocumentGraph(title="Falls", root=Node(type=NodeType.DOCUMENT, children=[
        Node(type=NodeType.HEADING, content="I. INTRODUCTION"),
        Node(type=NodeType.BODY, content="Falls are a major cause of injury among older adults."),
        Node(type=NodeType.HEADING, content="III. RESULTS"),
        Node(type=NodeType.BODY, content="The model reaches 89.01% accuracy on held-out subjects."),
    ]))
    router = FakeRouter(
        '{"notes": [{"heading": "I. INTRODUCTION", "about": "motivates automated fall detection"},'
        ' {"heading": "III. RESULTS", "about": "reports 89.01% accuracy on held-out subjects"}]}')

    about, failures = read_document(graph, router=router)

    assert not failures
    assert about["I. INTRODUCTION"] == "motivates automated fall detection"

    brief = brief_with_reading(graph, about)
    results = next(s for s in brief["sections"] if s["heading"] == "III. RESULTS")
    assert results["about"] == "reports 89.01% accuracy on held-out subjects"


def test_a_page_that_could_not_be_read_is_named():
    from app.docos.command.reading import read_document
    from app.docos.graph import DocumentGraph, Node, NodeType

    graph = DocumentGraph(root=Node(type=NodeType.DOCUMENT, children=[
        Node(type=NodeType.BODY, content="Some prose to read."),
    ]))
    about, failures = read_document(graph, router=FakeRouter("not json"))

    assert about == {}
    assert failures and "page 1" in failures[0]


def test_a_reading_that_was_never_taken_leaves_the_brief_as_it_was():
    from app.docos.command.brief import document_brief
    from app.docos.command.reading import brief_with_reading
    from app.docos.graph import DocumentGraph, Node, NodeType

    graph = DocumentGraph(root=Node(type=NodeType.DOCUMENT, children=[
        Node(type=NodeType.HEADING, content="I. INTRODUCTION"),
    ]))
    assert brief_with_reading(graph, {}) == document_brief(graph)


def test_a_passage_the_instruction_does_not_touch_is_not_a_failure():
    """"Convert the equations" over a document mostly without equations gets
    {"edits": []} for most passes. Those paragraphs were considered and left
    alone; re-asking cannot change that, and calling it a failure is a lie."""
    graph = build("alpha", "beta")
    nodes = rewritable(graph, [], "body")
    router = FakeRouter('{"edits": []}')

    edits, failures = rewrite_nodes(graph, nodes, "convert the equations", router=router)

    assert edits == {}
    assert not failures, "nothing failed; there was nothing to do"
    assert len(router.sent) == 1, "and nothing was asked twice"


def test_a_reply_that_covers_only_some_nodes_leaves_the_rest_alone():
    graph = build("alpha", "beta", "gamma")
    nodes = rewritable(graph, [], "body")
    ids = [n.id for n in nodes]
    router = FakeRouter('{"edits": [{"id": "%s", "text": "ALPHA"}]}' % ids[0])

    edits, failures = rewrite_nodes(graph, nodes, "shout at alpha", router=router)

    assert edits == {ids[0]: "ALPHA"}
    assert not failures
    assert len(router.sent) == 1, "beta and gamma were skipped on purpose"
