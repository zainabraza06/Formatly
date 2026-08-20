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


# ── reference numbering ─────────────────────────────────────────────────────

import pytest as _pytest  # noqa: E402

from app.paper.references import format_reference  # noqa: E402
from app.paper.renderer import render_paper  # noqa: E402
from app.paper.schema import PaperSpec as _Spec  # noqa: E402
from docx import Document as _Doc  # noqa: E402


@_pytest.mark.parametrize("entry", [
    '[1] B. Stroustrup, Programming, 2014.',
    '[1] [1] B. Stroustrup, Programming, 2014.',
    '1. B. Stroustrup, Programming, 2014.',
    '(1) B. Stroustrup, Programming, 2014.',
])
def test_the_model_numbering_itself_does_not_double_up(entry):
    """The renderer adds "[n] "; an entry that already carries one must lose it."""
    assert format_reference(entry).startswith("B. Stroustrup")


def test_a_year_at_the_start_is_not_mistaken_for_numbering():
    text = "2024 was a good year for compilers."
    assert format_reference(text) == text


def test_rendered_reference_is_numbered_exactly_once(tmp_path):
    spec = _Spec.model_validate({
        "meta": {"title": "T", "style": "assignment"},
        "blocks": [{"type": "paragraph", "text": "Body."}],
        "references": ['[1] B. Stroustrup, Programming, 2014.',
                       '[2] S. Prata, C++ Primer Plus, 2011.'],
    })
    out = render_paper(spec, tmp_path / "r.docx")
    refs = [p.text for p in _Doc(str(out)).paragraphs if p.text.startswith("[")]
    assert refs == ['[1] B. Stroustrup, Programming, 2014.',
                    '[2] S. Prata, C++ Primer Plus, 2011.']


def test_an_empty_listing_is_dropped_and_numbering_stays_contiguous(tmp_path):
    spec = _Spec.model_validate({
        "meta": {"title": "T", "style": "assignment"},
        "blocks": [
            {"type": "code", "language": "cpp", "text": "int main(){}", "caption": "first"},
            {"type": "code", "language": "cpp", "text": "   ", "caption": "promised, absent"},
            {"type": "code", "language": "cpp", "text": "int f(){}", "caption": "second"},
        ],
    })
    out = render_paper(spec, tmp_path / "c.docx")
    captions = [p.text for p in _Doc(str(out)).paragraphs if p.text.startswith("Listing")]
    assert captions == ["Listing 1. first", "Listing 2. second"]
