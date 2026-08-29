"""Word's own equations, read from the file rather than guessed from a picture.

Word stores an equation as OMML — a small XML tree describing the maths, sitting
inside the paragraph. python-docx reads `w:t` runs and nothing else, so an
equation was invisible: a paragraph holding only one looked empty and was
dropped, and the equation did not survive an import and export. It was not
rendered badly; it was gone.

This turns that tree into LaTeX, which is what the rest of the world writes
maths in and what a model asked to "convert the equations" already understands.
The original XML is kept alongside it so an untouched equation can be written
back exactly as Word wrote it.

Anything this does not recognise falls back to the text inside it, so an
unusual construct comes out plainer than it went in but never disappears.
"""
from __future__ import annotations

from typing import Optional

from docx.oxml.ns import qn

# The nary operators Word names by character, in the LaTeX the character means.
_NARY = {
    "∑": r"\sum", "∏": r"\prod", "∐": r"\coprod",
    "∫": r"\int", "∬": r"\iint", "∭": r"\iiint", "∮": r"\oint",
    "⋃": r"\bigcup", "⋂": r"\bigcap", "⋁": r"\bigvee", "⋀": r"\bigwedge",
}

# Accents, by the character Word puts above the base.
_ACCENTS = {
    "̂": r"\hat", "^": r"\hat",
    "̄": r"\bar", "¯": r"\bar",
    "̃": r"\tilde", "~": r"\tilde",
    "̇": r"\dot", "̈": r"\ddot",
    "⃗": r"\vec", "→": r"\vec",
}


def _text_of(element) -> str:
    """Every character under an element, in order. The safety net."""
    return "".join(node.text or "" for node in element.iter(qn("m:t")))


def _children(element, *names: str) -> list:
    wanted = {qn(name) for name in names}
    return [child for child in element if child.tag in wanted]


def _first(element, name: str):
    return element.find(qn(name))


def _inside(element, name: str) -> str:
    """The LaTeX of a named child, or "" when there is none.

    Written out rather than `_first(...) or []`: an lxml element with no
    children is falsy, so that idiom silently discarded `<m:num><m:f/></m:num>`
    — a fraction whose numerator is itself a fraction.
    """
    child = _first(element, name)
    return _convert_all(child) if child is not None else ""


def _convert_all(element) -> str:
    return "".join(_convert(child) for child in element)


def _braced(text: str) -> str:
    """`{x}` — but a single character needs no braces, and reads better without."""
    return text if len(text) == 1 else "{" + text + "}"


def _convert(element) -> str:
    """One OMML element as LaTeX."""
    tag = element.tag

    if tag == qn("m:t"):
        return element.text or ""

    if tag in (qn("m:r"), qn("m:e"), qn("m:num"), qn("m:den"),
               qn("m:sup"), qn("m:sub"), qn("m:deg"), qn("m:oMath"),
               qn("m:oMathPara"), qn("m:fName"), qn("m:lim")):
        return _convert_all(element)

    if tag == qn("m:f"):                                    # fraction
        num = _inside(element, "m:num")
        den = _inside(element, "m:den")
        return r"\frac{%s}{%s}" % (num, den)

    if tag == qn("m:sSup"):                                 # x^2
        base = _inside(element, "m:e")
        sup = _inside(element, "m:sup")
        return "%s^%s" % (_braced(base), _braced(sup))

    if tag == qn("m:sSub"):                                 # x_i
        base = _inside(element, "m:e")
        sub = _inside(element, "m:sub")
        return "%s_%s" % (_braced(base), _braced(sub))

    if tag == qn("m:sSubSup"):                              # x_i^2
        base = _inside(element, "m:e")
        sub = _inside(element, "m:sub")
        sup = _inside(element, "m:sup")
        return "%s_%s^%s" % (_braced(base), _braced(sub), _braced(sup))

    if tag == qn("m:rad"):                                  # square or nth root
        degree = _inside(element, "m:deg")
        body = _inside(element, "m:e")
        return r"\sqrt[%s]{%s}" % (degree, body) if degree else r"\sqrt{%s}" % body

    if tag == qn("m:nary"):                                 # sum, integral, product
        properties = _first(element, "m:naryPr")
        symbol = "∫"
        if properties is not None:
            chr_element = _first(properties, "m:chr")
            if chr_element is not None:
                symbol = chr_element.get(qn("m:val")) or symbol
        operator = _NARY.get(symbol, r"\sum" if symbol == "∑" else None)
        if operator is None:
            operator = r"\operatorname{%s}" % symbol
        lower = _inside(element, "m:sub")
        upper = _inside(element, "m:sup")
        body = _inside(element, "m:e")
        out = operator
        if lower:
            out += "_%s" % _braced(lower)
        if upper:
            out += "^%s" % _braced(upper)
        return "%s %s" % (out, body) if body else out

    if tag == qn("m:d"):                                    # (x), [x], {x}
        properties = _first(element, "m:dPr")
        opening, closing = "(", ")"
        if properties is not None:
            begin, end = _first(properties, "m:begChr"), _first(properties, "m:endChr")
            if begin is not None:
                opening = begin.get(qn("m:val")) or opening
            if end is not None:
                closing = end.get(qn("m:val")) or closing
        inside = "".join(_convert(child) for child in _children(element, "m:e"))
        return r"\left%s %s \right%s" % (opening or ".", inside, closing or ".")

    if tag == qn("m:acc"):                                  # x̂, x̄, x⃗
        properties = _first(element, "m:accPr")
        mark = "̂"
        if properties is not None:
            chr_element = _first(properties, "m:chr")
            if chr_element is not None:
                mark = chr_element.get(qn("m:val")) or mark
        base = _inside(element, "m:e")
        return "%s{%s}" % (_ACCENTS.get(mark, r"\hat"), base)

    if tag == qn("m:bar"):
        return r"\overline{%s}" % _inside(element, "m:e")

    if tag == qn("m:func"):                                 # sin x, log x
        name = _inside(element, "m:fName")
        body = _inside(element, "m:e")
        return r"\%s %s" % (name.strip(), body) if name.strip().isalpha() else "%s %s" % (name, body)

    if tag in (qn("m:limLow"), qn("m:limUpp")):             # lim under / over
        base = _inside(element, "m:e")
        limit = _inside(element, "m:lim")
        joiner = "_" if tag == qn("m:limLow") else "^"
        return "%s%s%s" % (base, joiner, _braced(limit))

    # Properties describe how to draw the thing, not what it says.
    if tag in (qn("m:rPr"), qn("m:ctrlPr"), qn("m:fPr"), qn("m:naryPr"),
               qn("m:dPr"), qn("m:accPr"), qn("m:radPr"), qn("m:sSupPr"),
               qn("m:sSubPr"), qn("m:sSubSupPr"), qn("m:barPr"), qn("m:funcPr"),
               qn("m:limLowPr"), qn("m:limUppPr")):
        return ""

    # Something unrecognised: keep its words rather than lose them.
    return _convert_all(element) or _text_of(element)


def omml_to_latex(element) -> str:
    """One `m:oMath` element as a LaTeX string."""
    return " ".join(_convert(element).split())


def equations_in(paragraph) -> list:
    """The `m:oMath` elements of a paragraph, in order."""
    return list(paragraph._p.iter(qn("m:oMath")))


def paragraph_parts(paragraph) -> list[tuple[str, str, object]]:
    """The paragraph in document order, as (kind, text, element) pieces.

    Word interleaves text runs and equations, so reading the runs and then the
    equations would put every equation at the end of its paragraph. Walking the
    children keeps "we minimise L over the set" from becoming "we minimise over
    the set L".

    `kind` is "text" or "maths". A maths piece carries its own element so the
    original XML can be written back later, exactly as Word wrote it.
    """
    parts: list[tuple[str, str, object]] = []
    for child in paragraph._p:
        if child.tag == qn("w:r"):
            text = "".join(node.text or "" for node in child.iter(qn("w:t")))
            if text:
                parts.append(("text", text, child))
        elif child.tag in (qn("m:oMath"), qn("m:oMathPara")):
            for equation in ([child] if child.tag == qn("m:oMath")
                             else list(child.iter(qn("m:oMath")))):
                latex = omml_to_latex(equation)
                if latex:
                    parts.append(("maths", latex, equation))
    return parts


def paragraph_maths(paragraph) -> Optional[str]:
    """The paragraph's equations as LaTeX, or None if it has none.

    Several equations in one paragraph are joined by a space, which is how they
    read on the page.
    """
    found = equations_in(paragraph)
    if not found:
        return None
    return " ".join(latex for latex in (omml_to_latex(e) for e in found) if latex)
