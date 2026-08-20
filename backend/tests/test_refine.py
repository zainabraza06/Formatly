"""Refining a user's special instructions, and doing it again on feedback."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.paper.prompt import build_improve_message  # noqa: E402
from app.paper.refine import (  # noqa: E402
    InstructionRefinementError, RefinedInstructions, refine_instructions,
)

_GOOD = ('{"improved": "Bold key terms.\nKeep it under four pages.",'
         ' "changes": ["named the page limit"], "questions": []}')


class FakeRouter:
    def __init__(self, *replies: str):
        self.replies = list(replies)
        self.calls: list[list[dict[str, str]]] = []

    def chat(self, messages, max_tokens=None, **_kw):
        self.calls.append(messages)
        return self.replies[min(len(self.calls) - 1, len(self.replies) - 1)], "fake", 0.1


def test_a_refinement_comes_back_structured():
    refined, provider = refine_instructions(
        instructions="make it professional", router=FakeRouter(_GOOD))
    assert isinstance(refined, RefinedInstructions)
    assert "Bold key terms." in refined.improved
    assert refined.changes == ["named the page limit"]
    assert provider == "fake"


def test_empty_instructions_are_refused():
    with pytest.raises(InstructionRefinementError):
        refine_instructions(instructions="   ", router=FakeRouter(_GOOD))


def test_unusable_output_is_reported_not_returned_empty():
    """An empty box is worse than an error: the user's own text is still better."""
    with pytest.raises(InstructionRefinementError):
        refine_instructions(instructions="x", router=FakeRouter("I cannot help"))
    with pytest.raises(InstructionRefinementError):
        refine_instructions(instructions="x", router=FakeRouter('{"improved": "  "}'))


def test_a_provider_failure_surfaces_as_a_refinement_error():
    class Broken:
        def chat(self, *_a, **_k):
            raise RuntimeError("provider down")

    with pytest.raises(InstructionRefinementError, match="provider down"):
        refine_instructions(instructions="x", router=Broken())


@pytest.mark.parametrize("payload,expected", [
    ('{"improved":"a","changes":"one\ntwo"}', ["one", "two"]),      # sent as a string
    ('{"improved":"a","changes":["- one","• two"]}', ["one", "two"]),  # bulleted
    ('{"improved":"a","changes":null}', []),
])
def test_change_lists_survive_the_shapes_models_use(payload, expected):
    refined, _ = refine_instructions(instructions="x", router=FakeRouter(payload))
    assert refined.changes == expected


def test_questions_are_capped():
    many = '{"improved":"a","questions":["q1","q2","q3","q4","q5"]}'
    refined, _ = refine_instructions(instructions="x", router=FakeRouter(many))
    assert len(refined.questions) == 3, "a list of questions should not become an interrogation"


# ── the retry loop ──────────────────────────────────────────────────────────

def test_feedback_and_the_previous_attempt_reach_the_model():
    """A retry has to be a correction, not another roll of the dice."""
    router = FakeRouter(_GOOD)
    refine_instructions(instructions="make it professional", router=router,
                        previous="an earlier attempt",
                        feedback="drop the table of contents")
    sent = router.calls[0][-1]["content"]
    assert "an earlier attempt" in sent
    assert "drop the table of contents" in sent


def test_a_first_pass_carries_no_previous_attempt():
    router = FakeRouter(_GOOD)
    refine_instructions(instructions="make it professional", router=router)
    sent = router.calls[0][-1]["content"]
    assert "your_previous_attempt" not in sent
    assert "their_feedback_on_it" not in sent


def test_the_material_is_excerpted_not_sent_whole():
    """The refiner needs to know what the document is about, not re-read it."""
    msg = build_improve_message(instructions="x", raw_text="y" * 20_000)
    assert len(msg) < 6000
