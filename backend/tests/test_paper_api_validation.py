"""/paper/render and /paper/preview must refuse a body that is not a spec.

Every PaperSpec field carries a default, so `{}` validates into an "Untitled"
document with no content. Both endpoints used to render that and return 200 with
a blank .docx — the caller got a file and no hint their body was wrong.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import HTTPException  # noqa: E402

from app.paper.api import _parse_spec  # noqa: E402

_VALID = {"meta": {"title": "Real", "style": "ieee"},
          "blocks": [{"type": "paragraph", "text": "Body."}]}


@pytest.mark.parametrize("body", [
    {},                                   # everything defaulted
    {"foo": 1},                           # not a spec at all
    {"meta": {"title": "X"}},             # metadata but nothing to render
    {"blocks": []},                       # explicitly empty
    [],                                   # wrong JSON type
    None,
    "a string",
])
def test_a_body_with_no_content_is_rejected(body):
    with pytest.raises(HTTPException) as exc:
        _parse_spec(body, None, "user-1")
    assert exc.value.status_code == 422


def test_the_error_says_what_to_send_instead():
    """A body that parses but carries nothing should name the fix, not just 422."""
    with pytest.raises(HTTPException) as exc:
        _parse_spec({"meta": {"title": "X"}}, None, "user-1")
    detail = str(exc.value.detail)
    assert "no content blocks" in detail
    assert "/paper/generate" in detail, "the message should point at the fix"


def test_an_empty_object_is_named_as_such():
    with pytest.raises(HTTPException) as exc:
        _parse_spec({}, None, "user-1")
    assert "non-empty JSON object" in str(exc.value.detail)


def test_a_spec_whose_blocks_are_malformed_is_rejected():
    with pytest.raises(HTTPException) as exc:
        _parse_spec({"blocks": [{"type": "heading"}]}, None, "user-1")
    assert exc.value.status_code == 422


def test_a_real_spec_passes_and_comes_back_resolved():
    parsed = _parse_spec(_VALID, None, "user-1")
    assert parsed.meta.title == "Real"
    assert len(parsed.blocks) == 1
    assert parsed.resolved, "the spec should come back fully styled"


def test_an_explicit_style_is_applied():
    parsed = _parse_spec(_VALID, "ieee_1col", "user-1")
    assert parsed.meta.style == "ieee_1col"
    assert parsed.meta.page.columns == 1
