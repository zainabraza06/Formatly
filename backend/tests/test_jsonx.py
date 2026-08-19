"""Extraction of a paper spec from whatever the model actually returned.

The cases here are the shapes seen in production, and every one of them used to
throw away a whole generated document.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.paper.jsonx import extract_json  # noqa: E402

_HEAD = '{"meta": {"title": "X"}, "blocks": [{"type":"paragraph","text":"hi"}'


def test_plain_object():
    assert extract_json('{"a": 1}') == {"a": 1}


def test_fenced():
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}


def test_prose_on_both_sides():
    text = 'Sure! Here you go:\n```json\n{"a": 1}\n```\nLet me know if you need changes.'
    assert extract_json(text) == {"a": 1}


def test_trailing_commas():
    assert extract_json('{"a": [1, 2,], "b": {"c": 3,},}') == {"a": [1, 2], "b": {"c": 3}}


def test_js_comments():
    assert extract_json('{ // title\n"a": 1, /* body */ "b": 2}') == {"a": 1, "b": 2}


def test_raw_newlines_inside_strings():
    assert extract_json('{"t": "one\ntwo"}') == {"t": "one\ntwo"}


def test_braces_inside_strings_do_not_confuse_the_scan():
    assert extract_json('{"t": "a {nested} brace", "u": 1}') == {"t": "a {nested} brace", "u": 1}


# ── truncation: the model ran out of output tokens ──────────────────────────

def test_truncated_after_a_complete_block():
    got = extract_json(_HEAD)
    assert got["blocks"] == [{"type": "paragraph", "text": "hi"}]


def test_truncated_mid_key_drops_the_dangling_key():
    got = extract_json(_HEAD + ',{"type":"paragraph","text"')
    assert got["meta"] == {"title": "X"}
    assert got["blocks"][0] == {"type": "paragraph", "text": "hi"}


def test_truncated_after_a_colon_drops_the_valueless_key():
    got = extract_json(_HEAD + '], "references":')
    assert "references" not in got
    assert got["blocks"] == [{"type": "paragraph", "text": "hi"}]


def test_truncated_mid_string_keeps_the_partial_text():
    got = extract_json('{"meta": {"title": "X"}, "blocks": '
                       '[{"type":"paragraph","text":"a sentence that got cut')
    assert got["blocks"][0]["text"] == "a sentence that got cut"


def test_truncated_mid_number():
    got = extract_json('{"blocks": [{"type":"heading","level": 1')
    assert got["blocks"] == [{"type": "heading", "level": 1}]


def test_truncated_deep_inside_nested_objects():
    got = extract_json('{"meta": {"title": "X", "authors": [{"name": "zainab", "affil')
    assert got["meta"]["authors"] == [{"name": "zainab"}]


def test_truncated_with_an_open_fence():
    got = extract_json('```json\n{"meta": {"title": "X"}, "blocks": [{"type":"paragraph"')
    assert got["meta"] == {"title": "X"}


# ── genuinely unusable output ───────────────────────────────────────────────

def test_no_json_at_all():
    assert extract_json("I cannot help with that.") is None
    assert extract_json("") is None
    assert extract_json("[1, 2, 3]") is None  # a list is not a paper spec
