"""What happens when the model's reply is not the clean JSON we asked for.

Every case here previously ended as "the model did not return usable JSON",
losing a whole generated document.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.paper.generator import (  # noqa: E402
    PaperGenerationError, _salvage_spec, generate_paper,
)

_GOOD = ('{"meta": {"title": "A Paper", "abstract": "x"}, "blocks": '
         '[{"type":"heading","level":1,"text":"Introduction"},'
         '{"type":"paragraph","text":"Body text."}]}')


class FakeRouter:
    """Replays a scripted list of replies, one per chat() call."""

    def __init__(self, *replies: str):
        self.replies = list(replies)
        self.calls: list[list[dict[str, str]]] = []

    def chat(self, messages, max_tokens=None, **_kw):
        self.calls.append(messages)
        reply = self.replies[min(len(self.calls) - 1, len(self.replies) - 1)]
        return reply, "fake", 0.1


def _generate(router):
    return generate_paper(raw_text="some source material", style="ieee",
                          depth="standard", router=router)


def test_clean_reply_needs_one_call():
    router = FakeRouter(_GOOD)
    spec, provider = _generate(router)
    assert spec.meta.title == "A Paper"
    assert provider == "fake"
    assert len(router.calls) == 1


def test_prose_wrapped_reply_is_still_used():
    spec, _ = _generate(FakeRouter(f"Certainly!\n```json\n{_GOOD}\n```\nEnjoy."))
    assert spec.meta.title == "A Paper"


def test_truncated_reply_is_repaired_not_retried():
    """The reply is cut off mid-block, but everything before it is usable."""
    cut = _GOOD[:_GOOD.index('{"type":"paragraph"')] + '{"type":"paragraph","tex'
    router = FakeRouter(cut)
    spec, _ = _generate(router)
    assert spec.meta.title == "A Paper"
    assert spec.blocks[0].text == "Introduction"
    assert len(router.calls) == 1


def test_unusable_reply_is_retried_with_a_corrective_note():
    router = FakeRouter("I'm sorry, I can't do that.", _GOOD)
    spec, _ = _generate(router)
    assert spec.meta.title == "A Paper"
    assert len(router.calls) == 2
    # the retry must say something the first call did not
    assert "JSON object ONLY" in router.calls[1][-1]["content"]


def test_three_attempts_before_falling_back():
    router = FakeRouter("nope", "still nope", _GOOD)
    spec, _ = _generate(router)
    assert spec.meta.title == "A Paper"
    assert len(router.calls) == 3


def test_hopeless_model_reports_clearly():
    with pytest.raises(PaperGenerationError) as exc:
        _generate(FakeRouter("nope"))
    assert "nope" in str(exc.value)


# ── schema salvage ──────────────────────────────────────────────────────────

def test_salvage_drops_only_the_malformed_block():
    raw = {
        "meta": {"title": "T"},
        "blocks": [
            {"type": "paragraph", "text": "kept"},
            {"type": "heading"},                       # no text — invalid
            {"type": "nonsense", "text": "unknown"},   # not a block type
            {"type": "paragraph", "text": "also kept"},
        ],
    }
    spec = _salvage_spec(raw)
    assert [b.text for b in spec.blocks] == ["kept", "also kept"]
    assert spec.meta.title == "T"


def test_salvage_sheds_bad_metadata_before_giving_up():
    raw = {"meta": {"authors": "not a list"}, "blocks": [{"type": "paragraph", "text": "kept"}]}
    spec = _salvage_spec(raw)
    assert [b.text for b in spec.blocks] == ["kept"]


def test_salvage_gives_up_when_no_block_survives():
    assert _salvage_spec({"blocks": [{"type": "heading"}]}) is None
    assert _salvage_spec({"blocks": []}) is None
