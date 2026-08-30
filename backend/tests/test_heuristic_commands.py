"""What the offline planner makes of an ordinary instruction.

This runs whenever the providers are unavailable, and it decides what happens
for a large share of real requests. Every case here is one that used to fall
past every branch and be answered with a selection — which changes nothing and
reports Done.
"""
from __future__ import annotations

import pytest

from app.docos.command.engine import CommandEngine


def _plan(command: str):
    batch = CommandEngine()._heuristic_actions(command)
    return batch.actions[0].type.value, batch.actions[0]


@pytest.mark.parametrize("command, style", [
    ("make the headings bold", {"bold": True}),
    ("italicise the table captions", {"italic": True}),
    ("underline the captions", {"underline": True}),
    ("make the headings bold and italic", {"bold": True, "italic": True}),
])
def test_formatting_verbs_become_a_format_action(command, style):
    op, action = _plan(command)
    assert op == "format"
    assert action.style.model_dump(exclude_none=True) == style


@pytest.mark.parametrize("command", [
    "make the header cells capitalized",
    "capitalise the headings",
    "spell out the abbreviations",
    "renumber the equations",
])
def test_changing_the_words_becomes_a_rewrite(command):
    op, action = _plan(command)
    assert op == "rewrite"
    assert action.params["instruction"] == command


def test_a_question_about_the_document_is_still_a_selection():
    assert _plan("show me the figures")[0] == "select"


def test_an_unrecognised_instruction_is_attempted_not_dismissed():
    """The fallback used to be a selection, which changes nothing and reads as
    success. An instruction with no rule for it goes to the rewriter."""
    op, action = _plan("make the notation consistent with the appendix")
    assert op == "rewrite"
    assert action.params["instruction"] == "make the notation consistent with the appendix"
