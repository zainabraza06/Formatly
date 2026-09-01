"""LaTeX → OMML, so a downloaded document holds equations and not dollar signs.

An equation read out of a .docx keeps its original XML and goes back untouched.
An equation the author typed as LaTeX — or that this editor produced — has no
such XML, so it was written to the file as the characters `$C = \\frac{F}{Q}$`,
which is what a reader then saw. With the maths drawn on screen, the download
was the one place the equations were not equations.

This builds Word's own markup for the part of LaTeX a paper actually uses:
fractions, powers and indices, roots, sums and integrals with their limits,
bracketed groups, Greek and the usual operators. Anything it does not know it
writes as text rather than guessing, so an exotic formula degrades to what it
looked like before instead of coming out wrong.
"""
from __future__ import annotations

import re
from typing import Optional

from docx.oxml import OxmlElement
from docx.oxml.ns import qn

# What each command means in Word's world: a character, mostly.
SYMBOLS = {
    # Greek, lower and upper
    "alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "epsilon": "ε",
    "varepsilon": "ε", "zeta": "ζ", "eta": "η", "theta": "θ", "iota": "ι",
    "kappa": "κ", "lambda": "λ", "mu": "μ", "nu": "ν", "xi": "ξ", "pi": "π",
    "rho": "ρ", "sigma": "σ", "tau": "τ", "upsilon": "υ", "phi": "φ",
    "varphi": "φ", "chi": "χ", "psi": "ψ", "omega": "ω",
    "Gamma": "Γ", "Delta": "Δ", "Theta": "Θ", "Lambda": "Λ", "Xi": "Ξ",
    "Pi": "Π", "Sigma": "Σ", "Phi": "Φ", "Psi": "Ψ", "Omega": "Ω",
    # operators and relations
    "times": "×", "cdot": "⋅", "div": "÷", "pm": "±", "mp": "∓",
    "leq": "≤", "le": "≤", "geq": "≥", "ge": "≥", "neq": "≠", "ne": "≠",
    "approx": "≈", "sim": "∼", "simeq": "≃", "equiv": "≡", "propto": "∝",
    "to": "→", "rightarrow": "→", "leftarrow": "←", "Rightarrow": "⇒",
    "in": "∈", "notin": "∉", "subset": "⊂", "subseteq": "⊆", "cup": "∪",
    "cap": "∩", "forall": "∀", "exists": "∃", "infty": "∞", "partial": "∂",
    "nabla": "∇", "ldots": "…", "cdots": "⋯", "dots": "…", "circ": "∘",
    "star": "⋆", "oplus": "⊕", "otimes": "⊗", "perp": "⊥", "angle": "∠",
    "degree": "°", "prime": "′", "ell": "ℓ", "hbar": "ℏ", "Re": "ℜ",
    "Im": "ℑ", "aleph": "ℵ", "emptyset": "∅", "surd": "√",
}

# Big operators, which carry their limits above and below.
NARY = {"sum": "∑", "prod": "∏", "coprod": "∐", "int": "∫", "iint": "∬",
        "iiint": "∭", "oint": "∮", "bigcup": "⋃", "bigcap": "⋂",
        "bigoplus": "⨁", "bigotimes": "⨂", "max": "max", "min": "min"}

# Functions Word sets upright: sin x, not s·i·n·x.
FUNCTIONS = {"sin", "cos", "tan", "cot", "sec", "csc", "arcsin", "arccos",
             "arctan", "sinh", "cosh", "tanh", "log", "ln", "exp", "lim",
             "det", "dim", "ker", "deg", "gcd", "arg"}

# Fonts a paper asks for. Word carries them on the run's properties.
FONTS = {"mathbf": "b", "bm": "b", "boldsymbol": "b", "mathit": "i",
         "mathrm": "p", "text": "p", "textrm": "p", "mathsf": "sans",
         "mathtt": "mono", "mathcal": "script", "mathbb": "double-struck",
         "mathfrak": "fraktur"}

_TOKEN = re.compile(r"""
    \\[A-Za-z]+ |          # a command
    \\[{}|,;! ] |          # an escaped character
    [{}^_&] |              # structure
    \s+ |                  # space, which LaTeX mostly ignores
    .                      # anything else, one character at a time
""", re.VERBOSE)

M = "http://schemas.openxmlformats.org/officeDocument/2006/math"


def latex_to_omml(latex: str, *, display: bool = False):
    """An `m:oMath` element for `latex`, or None if there is nothing in it."""
    tokens = [t for t in _TOKEN.findall(latex or "") if t.strip() or t == " "]
    if not tokens:
        return None
    node = OxmlElement("m:oMath")
    for child in _parse(_Reader(tokens), stop=None):
        node.append(child)
    return node if len(node) else None


class _Reader:
    """The tokens, with one step of lookahead. LaTeX needs no more than that."""

    def __init__(self, tokens: list[str]):
        self.tokens = tokens
        self.at = 0

    def peek(self) -> Optional[str]:
        while self.at < len(self.tokens) and self.tokens[self.at].isspace():
            self.at += 1
        return self.tokens[self.at] if self.at < len(self.tokens) else None

    def next(self) -> Optional[str]:
        token = self.peek()
        if token is not None:
            self.at += 1
        return token


def _parse(reader: _Reader, stop: Optional[str]) -> list:  # noqa: C901
    """Elements until `stop` (or the end), scripts already attached."""
    out: list = []
    while True:
        token = reader.peek()
        if token is None or token == stop:
            reader.next()
            break
        if token in ("^", "_"):
            reader.next()
            base = out.pop() if out else _run("")
            out.append(_scripted(base, token, reader))
            continue
        element = _one(reader, stop)
        if element is not None:
            out.append(element)
    return out


def _one(reader: _Reader, stop: Optional[str] = None):
    """The next thing: a command, a group, or a character."""
    token = reader.next()
    if token is None:
        return None
    if token == "{":
        return _group(_parse(reader, stop="}"))
    if token == "}":
        return None
    if token.startswith("\\"):
        return _command(token[1:], reader, stop)
    if token in "([":
        return _delimited(token, reader)
    return _run(token)


def _command(name: str, reader: _Reader, stop: Optional[str] = None):
    if name == "frac" or name == "dfrac" or name == "tfrac":
        return _fraction(_argument(reader), _argument(reader))
    if name == "sqrt":
        return _root(reader)
    if name in NARY:
        return _nary(NARY[name], reader, stop)
    if name in FONTS:
        return _styled(_argument(reader), FONTS[name], literal=name.startswith("text"))
    if name in FUNCTIONS:
        return _run(name, upright=True)
    if name in SYMBOLS:
        return _run(SYMBOLS[name])
    if name in ("left", "right", "big", "Big", "bigg", "Bigg"):
        return None                         # the bracket itself follows
    if name in ("quad", "qquad", ",", ";", "!", " "):
        return _run(" ")
    # Something this does not know: write the command as it was typed rather
    # than dropping it, so nothing is silently lost.
    return _run("\\" + name)


def _argument(reader: _Reader) -> list:
    """One argument: a braced group, or the single token that follows."""
    token = reader.peek()
    if token == "{":
        reader.next()
        return _parse(reader, stop="}")
    element = _one(reader)
    return [element] if element is not None else []


# ── the elements Word uses ───────────────────────────────────────────────────

def _run(text: str, *, upright: bool = False, style: str = ""):
    run = OxmlElement("m:r")
    if upright or style:
        properties = OxmlElement("m:rPr")
        if upright or style == "p":
            nor = OxmlElement("m:nor")
            properties.append(nor)
        run.append(properties)
    if style in ("b", "i"):
        run_properties = OxmlElement("w:rPr")
        weight = OxmlElement("w:b" if style == "b" else "w:i")
        run_properties.append(weight)
        run.append(run_properties)
    element = OxmlElement("m:t")
    # A control character cannot go into XML, and a stray one in the text
    # should not lose the whole equation.
    element.text = "".join(c for c in text if c >= " " or c == "	")
    # Word keeps the spaces an equation states.
    element.set(qn("xml:space"), "preserve")
    run.append(element)
    return run


def _group(children: list):
    """Several elements as one.

    OMML has no bare group: `m:e` is only ever a part of something else, and
    putting one straight into an `m:oMath` is invalid — Word refuses the whole
    file over it, saying only that it found a problem with the contents. A
    delimiter with no brackets is Word's own way of holding a run of elements
    together, and it draws nothing.
    """
    if len(children) == 1:
        return children[0]

    element = OxmlElement("m:d")
    properties = OxmlElement("m:dPr")
    for tag in ("m:begChr", "m:endChr"):
        marker = OxmlElement(tag)
        marker.set(qn("m:val"), "")
        properties.append(marker)
    element.append(properties)
    element.append(_wrap("m:e", children))
    return element


def _wrap(tag: str, children: list):
    element = OxmlElement(tag)
    for child in children:
        element.append(child)
    return element


def _fraction(numerator: list, denominator: list):
    fraction = OxmlElement("m:f")
    fraction.append(OxmlElement("m:fPr"))
    fraction.append(_wrap("m:num", numerator))
    fraction.append(_wrap("m:den", denominator))
    return fraction


def _root(reader: _Reader):
    degree: list = []
    if reader.peek() == "[":
        reader.next()
        degree = _parse(reader, stop="]")
    radicand = _argument(reader)

    radical = OxmlElement("m:rad")
    properties = OxmlElement("m:radPr")
    if not degree:
        hide = OxmlElement("m:degHide")
        hide.set(qn("m:val"), "1")
        properties.append(hide)
    radical.append(properties)
    radical.append(_wrap("m:deg", degree))
    radical.append(_wrap("m:e", radicand))
    return radical


def _scripted(base, kind: str, reader: _Reader):
    """A base with a superscript, a subscript, or both."""
    first = _argument(reader)
    second: list = []
    both = False
    other = "_" if kind == "^" else "^"
    if reader.peek() == other:
        reader.next()
        second = _argument(reader)
        both = True

    if both:
        element = OxmlElement("m:sSubSup")
        element.append(OxmlElement("m:sSubSupPr"))
        element.append(_wrap("m:e", [base]))
        sub, sup = (second, first) if kind == "^" else (first, second)
        element.append(_wrap("m:sub", sub))
        element.append(_wrap("m:sup", sup))
        return element

    tag = "m:sSup" if kind == "^" else "m:sSub"
    element = OxmlElement(tag)
    element.append(OxmlElement(tag + "Pr"))
    element.append(_wrap("m:e", [base]))
    element.append(_wrap("m:sup" if kind == "^" else "m:sub", first))
    return element


def _nary(symbol: str, reader: _Reader, stop: Optional[str] = None):
    """A sum, product or integral, with whatever limits it carries."""
    lower: list = []
    upper: list = []
    while reader.peek() in ("_", "^"):
        which = reader.next()
        if which == "_":
            lower = _argument(reader)
        else:
            upper = _argument(reader)

    element = OxmlElement("m:nary")
    properties = OxmlElement("m:naryPr")
    character = OxmlElement("m:chr")
    character.set(qn("m:val"), symbol)
    properties.append(character)
    for tag, present in (("m:subHide", not lower), ("m:supHide", not upper)):
        if present:
            hide = OxmlElement(tag)
            hide.set(qn("m:val"), "1")
            properties.append(hide)
    element.append(properties)
    element.append(_wrap("m:sub", lower))
    element.append(_wrap("m:sup", upper))
    # What the operator applies to: everything up to the end of the term it is
    # in. Taking one token instead left "sum of x sub i" reading as "the sum of
    # x, all of it subscripted i".
    element.append(_wrap("m:e", _parse(reader, stop)))
    return element


def _delimited(opening: str, reader: _Reader):
    closing = {"(": ")", "[": "]"}[opening]
    inside = _parse(reader, stop=closing)

    element = OxmlElement("m:d")
    properties = OxmlElement("m:dPr")
    for tag, char in (("m:begChr", opening), ("m:endChr", closing)):
        marker = OxmlElement(tag)
        marker.set(qn("m:val"), char)
        properties.append(marker)
    element.append(properties)
    element.append(_wrap("m:e", inside))
    return element


def _styled(children: list, style: str, *, literal: bool):
    """\\mathbf{x} and \\text{...}: the same characters, set differently."""
    if literal:
        text = "".join(child.findtext(qn("m:t")) or "" for child in children)
        return _run(text, upright=True)
    if len(children) == 1 and children[0].tag == qn("m:r"):
        text = children[0].findtext(qn("m:t")) or ""
        return _run(text, style=style)
    return _group(children)
