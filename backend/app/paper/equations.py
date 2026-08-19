"""Typeset equations, without a LaTeX installation.

Word's own equation editor is not reachable from python-docx, and plain text
cannot show a fraction, a radical or a summation with limits — `d = (x1 - x2) /
sqrt((s1^2 + s2^2)/2)` is a line of code, not an equation.

matplotlib's mathtext engine parses the TeX *math subset* and rasterises it
itself: no TeX distribution, no dvipng, nothing to install. So the model writes
familiar `\\frac{a}{b}` markup and the reader gets real typeset mathematics.

Anything mathtext cannot parse falls back to being set as text, so an unusual
construct costs one equation's typography rather than the document.
"""
from __future__ import annotations

import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # non-interactive backend — must precede pyplot/mathtext
from matplotlib import mathtext
from matplotlib.font_manager import FontProperties

# Rendered well above print resolution, then placed at its true physical size.
_DPI = 400

# STIX is metrically the Times companion, so an equation sits with a serif body
# text instead of beside it.
_FONTSET = "stix"

# Markup that only ever appears in mathematics. Plain prose equations such as
# "y = mx + c" read perfectly well as text and are left alone.
_MATH_MARKUP = re.compile(
    r"\\(?:frac|sqrt|sum|prod|int|lim|partial|infty|cdot|times|pm|leq|geq|neq|approx"
    r"|alpha|beta|gamma|delta|theta|lambda|mu|sigma|tau|phi|omega|bar|hat|vec|mathrm"
    r"|left|right|begin|text)\b"
    r"|[_^]\{|[_^][A-Za-z0-9]"
)


def looks_like_math(text: str) -> bool:
    """Is this worth rasterising, or will plain text serve it just as well?"""
    return bool(_MATH_MARKUP.search(text or ""))


def render_equation_png(text: str, out_path: Path, *, size_pt: float = 11.0,
                        color: str = "black") -> tuple[Path, float]:
    """Render `text` as an image. Returns the path and its width in INCHES, so
    the caller can place it at the size it was typeset at rather than guessing.

    Raises ValueError if the markup will not parse.
    """
    expr = _normalise(text)
    if not expr:
        raise ValueError("no equation to render")

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    previous = matplotlib.rcParams["mathtext.fontset"]
    matplotlib.rcParams["mathtext.fontset"] = _FONTSET
    try:
        mathtext.math_to_image(f"${expr}$", str(out_path), dpi=_DPI, format="png",
                               prop=FontProperties(size=size_pt), color=color)
    except (ValueError, RuntimeError, KeyError) as exc:
        raise ValueError(f"could not typeset {text!r}: {exc}") from exc
    finally:
        matplotlib.rcParams["mathtext.fontset"] = previous

    from PIL import Image
    with Image.open(str(out_path)) as img:
        width_in = img.width / _DPI
    return out_path, width_in


def _normalise(text: str) -> str:
    """Accept what a model actually emits: `$...$`, `\\[...\\]`, `\\(...\\)`, or
    bare markup. mathtext wants the bare expression."""
    expr = (text or "").strip()
    for opener, closer in (("$$", "$$"), ("\\[", "\\]"), ("\\(", "\\)"), ("$", "$")):
        if expr.startswith(opener) and expr.endswith(closer) and len(expr) > len(opener) + len(closer) - 1:
            expr = expr[len(opener):-len(closer)].strip()
            break
    # mathtext has no display-math environments; the expression alone is enough
    expr = re.sub(r"\\(?:begin|end)\{(?:equation|displaymath|math)\*?\}", "", expr)
    return expr.strip()
