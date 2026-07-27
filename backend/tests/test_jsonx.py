"""The JSON extractor is the last line of defence between a model's messy reply
and a lost document, so it must survive the ways models actually deviate."""
from __future__ import annotations

from app.paper.jsonx import extract_json

GOOD = {"meta": {"title": "T"}, "blocks": [{"type": "paragraph", "text": "hi"}]}


def test_plain_json():
    assert extract_json('{"a": 1}') == {"a": 1}


def test_json_fenced_in_markdown():
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('```\n{"a": 1}\n```') == {"a": 1}


def test_prose_around_json():
    text = 'Sure! Here is the document:\n{"a": 1, "b": [2, 3]}\nHope that helps.'
    assert extract_json(text) == {"a": 1, "b": [2, 3]}


def test_nested_braces_do_not_confuse_the_match():
    text = 'noise {"outer": {"inner": {"deep": 1}}, "x": 2} trailing'
    assert extract_json(text) == {"outer": {"inner": {"deep": 1}}, "x": 2}


def test_braces_inside_strings_are_ignored():
    text = '{"formula": "f(x) = {a + b}", "n": 1}'
    assert extract_json(text) == {"formula": "f(x) = {a + b}", "n": 1}


def test_escaped_quotes_inside_strings():
    text = r'{"q": "she said \"hi\"", "n": 2}'
    assert extract_json(text) == {"q": 'she said "hi"', "n": 2}


def test_trailing_commas_are_repaired():
    assert extract_json('{"a": 1, "b": 2,}') == {"a": 1, "b": 2}
    assert extract_json('{"list": [1, 2, 3,],}') == {"list": [1, 2, 3]}


def test_truncated_json_returns_none():
    # a response cut off mid-object cannot be recovered — must fail cleanly
    assert extract_json('{"a": 1, "b": {"c":') is None


def test_no_json_at_all():
    assert extract_json("I'm sorry, I can't help with that.") is None
    assert extract_json("") is None
    assert extract_json(None) is None  # type: ignore[arg-type]


def test_realistic_paper_reply_with_fence_and_prose():
    reply = (
        "Here is your report as strict JSON:\n\n```json\n"
        '{"meta": {"title": "Q3 Report"}, '
        '"blocks": [{"type": "heading", "level": 1, "text": "Intro"}], '
        '"references": [],}\n'  # note the trailing comma models love
        "```\n\nLet me know if you'd like changes."
    )
    out = extract_json(reply)
    assert out is not None
    assert out["meta"]["title"] == "Q3 Report"
    assert out["blocks"][0]["text"] == "Intro"
