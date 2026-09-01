"""A download holds equations when the page is drawing them.

An equation read out of a .docx kept its original XML and went back untouched.
One the author typed as LaTeX had no such XML, so it was written to the file as
the characters `$C = \\frac{F}{Q}$` — with the maths drawn on screen, the
download was the one place the equations were not equations.
"""
from __future__ import annotations

import pytest

from app.docos.export import graph_to_docx_bytes
from app.docos.graph import DocumentGraph, Node, NodeType
from app.docos.parser import parse_docx_bytes
from app.docos.parser.omml import omml_to_latex
from app.docos.parser.omml_write import latex_to_omml

TYPED = r"Unit cost is $C = \frac{F + vQ}{Q}$ per parcel, with $F_1 = 0.88$ overall."


def document(render_maths: bool) -> DocumentGraph:
    root = Node(type=NodeType.DOCUMENT,
                metadata={"page": {"render_maths": render_maths},
                          "render_maths": render_maths})
    root.children = [Node(type=NodeType.BODY, content=TYPED)]
    return DocumentGraph(root=root, title="t")


def equations_in(graph: DocumentGraph) -> list[str]:
    out: list[str] = []
    for node in graph.nodes():
        out += [e["latex"] for e in (node.metadata or {}).get("equations") or []]
    return out


# ── the download ─────────────────────────────────────────────────────────────

def test_with_the_maths_drawn_the_file_holds_equations():
    back = parse_docx_bytes(graph_to_docx_bytes(document(True)), title="t")
    assert len(equations_in(back)) == 2


def test_with_the_maths_off_the_file_says_what_was_typed():
    """The page shows the characters the author wrote, and so should the file."""
    back = parse_docx_bytes(graph_to_docx_bytes(document(False)), title="t")
    assert equations_in(back) == []
    assert r"$C = \frac{F + vQ}{Q}$" in next(
        n.content for n in back.nodes() if n.type is NodeType.BODY)


def test_the_words_around_an_equation_are_kept():
    back = parse_docx_bytes(graph_to_docx_bytes(document(True)), title="t")
    text = next(n.content for n in back.nodes() if n.type is NodeType.BODY)
    assert text.startswith("Unit cost is ")
    assert text.endswith(" overall.")


# ── the reader's own toggle ──────────────────────────────────────────────────

def test_the_download_follows_the_toggle_without_changing_the_document():
    """Saving a file with the maths drawn is a way of looking at the document,
    not an edit to it: nobody else's view changes."""
    from app.docos.api import _with_maths

    graph = document(False)
    written = parse_docx_bytes(graph_to_docx_bytes(_with_maths(graph, True)), title="t")
    assert len(equations_in(written)) == 2
    assert graph.root.metadata.get("render_maths") is False


def test_the_toggle_off_leaves_the_graph_alone_too():
    from app.docos.api import _with_maths

    graph = document(False)
    assert _with_maths(graph, False) is graph


# ── the conversion itself ────────────────────────────────────────────────────

@pytest.mark.parametrize("latex, expected", [
    (r"h = 16", "h=16"),
    (r"C = \frac{F + vQ}{Q}", r"C=\frac{F+vQ}{Q}"),
    (r"3 \times 10^{-3}", "3×10^{-3}"),
    (r"\sqrt{a^2 + b^2}", r"\sqrt{a^2+b^2}"),
    (r"\sum_{i=1}^{N} x_i", r"\sum_{i=1}^N x_i"),
    (r"\alpha \leq \beta", "α≤β"),
    (r"F_1 = 0.88", "F_1=0.88"),
])
def test_latex_goes_to_word_and_reads_back_the_same(latex: str, expected: str):
    """Round-tripped through Word's own markup and this parser's reading of it."""
    element = latex_to_omml(latex)
    assert element is not None
    assert omml_to_latex(element) == expected


def test_nothing_at_all_produces_nothing():
    assert latex_to_omml("") is None
    assert latex_to_omml("   ") is None


def test_an_unknown_command_survives_as_itself():
    """Better to write it out as typed than to guess at it or drop it."""
    assert "widetilde" in omml_to_latex(latex_to_omml(r"\widetilde{x}"))
