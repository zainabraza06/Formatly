"""The names a document uses for its own things.

"Rephrase the title around the architecture" came back with the instruction's
own word stuck on the front, because the rewriter was shown a paragraph and a
sentence and had no way to learn what this paper calls its architecture.
"""
from __future__ import annotations

import pytest

from app.docos.command.terms import document_terms


def test_a_defined_abbreviation_comes_back_with_its_words():
    assert document_terms([
        "We train a subject-independent classifier (SIC) on the raw signal.",
        "The SIC is compared with a feature-independent classifier (FIC).",
        "SIC beats FIC on every subject.",
    ]) == ["subject-independent classifier (SIC)",
           "feature-independent classifier (FIC)"]


def test_a_hyphenated_term_spells_the_whole_abbreviation():
    """"Leave-One-Subject-Out" is all four letters of LOSO by itself."""
    assert document_terms([
        "Evaluated under a Leave-One-Subject-Out (LOSO) protocol.",
        "The LOSO result is reported per subject. LOSO throughout.",
    ])[0] == "Leave-One-Subject-Out (LOSO)"


def test_the_words_before_the_bracket_are_not_swept_up():
    """The sentence runs on before the term; only the term is the term."""
    terms = document_terms([
        "Performance is evaluated under subject-independent "
        "Leave-One-Subject-Out (LOSO) cross-validation.",
        "LOSO again, and LOSO once more.",
    ])
    assert terms[0] == "Leave-One-Subject-Out (LOSO)"


def test_a_name_used_often_is_a_term_even_undefined():
    assert "MobiAct" in document_terms([
        "We use MobiAct v2.0.", "MobiAct holds 15 activity types.",
        "Every MobiAct subject is included.",
    ])


@pytest.mark.parametrize("noise", ["THE", "AND", "PDF", "IEEE"])
def test_words_that_only_look_like_abbreviations_are_left_out(noise: str):
    assert noise not in document_terms([f"{noise} {noise} {noise} something."])


def test_a_passing_mention_is_not_the_documents_vocabulary():
    """Once is a mention; twice is a name the document uses."""
    assert document_terms(["A single mention of XYZ in passing."]) == []


def test_a_document_with_nothing_to_say_says_nothing():
    assert document_terms([]) == []
    assert document_terms(["", "   "]) == []
