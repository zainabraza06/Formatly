"""A bold border is a heavy line, not bold words.

"Keep the top and bottom borders, bold" came back as a border action and two
format actions, and every cell in the document was set in bold type. The word
had already been spent on the rule.
"""
from __future__ import annotations

import pytest

from app.docos.actions import validate_batch
from app.docos.service import _rules_are_not_type


def kinds(command: str, actions: list[dict]) -> list[str]:
    batch = validate_batch({"reasoning": "t", "actions": actions})
    _rules_are_not_type(command, batch)
    return [a.type.value for a in batch.actions]


BORDER = {"type": "border", "target": "table",
          "params": {"sides": ["top", "bottom"], "width": 1.5}}
BOLD_CELLS = {"type": "format", "target": "table_header", "style": {"bold": True}}


def test_bold_beside_a_border_does_not_bold_the_text():
    assert kinds("keep top and bottom borders bold", [BORDER, BOLD_CELLS]) == ["border"]


@pytest.mark.parametrize("word", ["bold", "thick", "heavy"])
def test_every_word_for_a_heavy_line(word: str):
    assert kinds(f"{word} borders top and bottom", [BORDER, BOLD_CELLS]) == ["border"]


def test_bold_on_its_own_is_still_bold():
    assert kinds("make the headings bold", [BOLD_CELLS]) == ["format"]


def test_a_border_request_that_also_asks_for_italics_keeps_them():
    """Only a format asking for nothing but bold is the word being spent
    twice; anything else was asked for in its own right."""
    both = {"type": "format", "target": "table_header",
            "style": {"bold": True, "italic": True}}
    assert kinds("bold borders and bold italic headers", [BORDER, both]) == [
        "border", "format"]


def test_bold_text_beside_a_border_request_that_never_says_bold():
    """No word was spent on the rule, so nothing is taken from the text."""
    assert kinds("thin borders, and embolden the header cells",
                 [BORDER, BOLD_CELLS]) == ["border", "format"]
