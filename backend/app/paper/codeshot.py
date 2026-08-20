"""Code rendered as an editor screenshot.

A listing set in the document's own monospace font is the right thing for most
submissions. But when a brief asks to *see the code in the editor* — "include a
screenshot of your VS Code" is a real and common instruction — a picture of
plain text is not what it means. So code can also be rendered as an image that
looks like the editor: a title bar with the filename, line numbers down the
gutter, and syntax highlighting.

Pygments does the highlighting and Pillow the chrome; both already ship with the
project, so this needs no editor, no screenshot tool, and no browser.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont
from pygments import highlight
from pygments.formatters import ImageFormatter
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.util import ClassNotFound

# The two editor looks worth offering. Each is a Pygments style plus the chrome
# colours that surround it, so the window reads as one piece.
THEMES: dict[str, dict[str, str]] = {
    "dark": {
        "style": "one-dark",       # the Dark+ / One Dark palette VS Code ships with
        "background": "#282C34",
        "chrome": "#21252B",
        "tab": "#282C34",
        "text": "#ABB2BF",
        "muted": "#5C6370",
        "line_numbers": "#4B5263",
        "border": "#181A1F",
    },
    "light": {
        "style": "vs",             # the Visual Studio light palette
        "background": "#FFFFFF",
        "chrome": "#F3F3F3",
        "tab": "#FFFFFF",
        "text": "#333333",
        "muted": "#808080",
        "line_numbers": "#237893",
        "border": "#E5E5E5",
    },
}
DEFAULT_THEME = "dark"

# A console is not an editor: no gutter, no syntax colours (output is not code),
# and the near-black of a real terminal rather than an editor's grey.
TERMINAL_THEMES: dict[str, dict[str, str]] = {
    "dark": {
        "style": "bw",
        "background": "#0C0C0C",   # the Windows Terminal / PowerShell default
        "chrome": "#1F1F1F",
        "tab": "#2D2D2D",
        "text": "#CCCCCC",
        "output": "#CCCCCC",
        "border": "#000000",
    },
    "light": {
        "style": "bw",
        "background": "#FFFFFF",
        "chrome": "#F3F3F3",
        "tab": "#FFFFFF",
        "text": "#333333",
        "output": "#1A1A1A",
        "border": "#D0D0D0",
    },
}

_FONT = "Consolas"
_FONT_SIZE = 20          # rendered large, then placed small — keeps it crisp in print
_CHROME_H = 34
_PAD = 14
_DOTS = ("#FF5F57", "#FEBC2E", "#28C840")


def render_code_image(text: str, out_path: Path, *, language: str = "",
                      filename: str = "", theme: str = DEFAULT_THEME) -> Path:
    """Render `text` as an editor screenshot PNG. Raises ValueError if empty."""
    if not (text or "").strip():
        raise ValueError("no code to render")

    palette = THEMES.get(theme, THEMES[DEFAULT_THEME])
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    body = _highlight(text, language, palette)
    label = filename or (language.lower() if language else "code")
    image = _frame(body, label, palette)
    image.save(str(out_path))
    return out_path


def render_terminal_image(text: str, out_path: Path, *, title: str = "Command Prompt",
                          theme: str = DEFAULT_THEME) -> Path:
    """Render a console session as a terminal window.

    Program output is not code: it gets no line numbers and no syntax colours,
    which would invent meaning that is not there. Nothing is executed to produce
    it — the text is whatever the caller supplies.
    """
    if not (text or "").strip():
        raise ValueError("no output to render")

    palette = TERMINAL_THEMES.get(theme, TERMINAL_THEMES[DEFAULT_THEME])
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    body = _plain(text, palette)
    image = _frame(body, title, palette, dots=False)
    image.save(str(out_path))
    return out_path


def _plain(text: str, palette: dict[str, str]) -> Image.Image:
    """Monospace text on the terminal ground, no gutter, no highlighting."""
    formatter = ImageFormatter(
        style=palette["style"],
        font_name=_FONT,
        font_size=_FONT_SIZE,
        line_numbers=False,
        line_pad=4,
        image_pad=_PAD,
        image_bg=palette["background"],
    )
    png = highlight(text, get_lexer_by_name("text"), formatter)

    import io
    img = Image.open(io.BytesIO(png)).convert("RGB")
    return _recolour(img, palette)


def _recolour(img: Image.Image, palette: dict[str, str]) -> Image.Image:
    """Pygments' "bw" style writes black on white; map that onto the terminal's
    own ground and foreground so the window reads as one piece."""
    bg = Image.new("RGB", img.size, palette["background"])
    fg = Image.new("RGB", img.size, palette["output"])
    # dark pixels are glyphs, light pixels are ground
    mask = img.convert("L").point(lambda v: 255 if v < 128 else 0)
    bg.paste(fg, (0, 0), mask)
    return bg


def _highlight(text: str, language: str, palette: dict[str, str]) -> Image.Image:
    formatter = ImageFormatter(
        style=palette["style"],
        font_name=_FONT,
        font_size=_FONT_SIZE,
        line_numbers=True,
        line_number_bg=palette["background"],
        line_number_fg=palette["line_numbers"],
        line_number_separator=False,
        line_number_pad=10,
        line_pad=4,
        image_pad=_PAD,
    )
    png = highlight(text, _lexer(text, language), formatter)

    import io
    return Image.open(io.BytesIO(png)).convert("RGB")


def _lexer(text: str, language: str):
    """The named lexer, or a guess, or plain text — never an exception. A wrong
    guess costs some colour; a raised one costs the whole document."""
    if language:
        try:
            return get_lexer_by_name(language.strip().lower())
        except ClassNotFound:
            pass
    try:
        return guess_lexer(text)
    except ClassNotFound:
        return get_lexer_by_name("text")


def _frame(body: Image.Image, label: str, palette: dict[str, str],
           dots: bool = True) -> Image.Image:
    """Put the highlighted code inside an editor window: title bar, window dots,
    and a tab carrying the filename."""
    # Pygments pads the left of the longest line but not the right, which leaves
    # the widest line touching the frame. Give the code area its own margin.
    width = max(body.width + _PAD, 320)
    canvas = Image.new("RGB", (width, body.height + _CHROME_H), palette["chrome"])
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, _CHROME_H, width, canvas.height), fill=palette["background"])

    r, y = 5, _CHROME_H // 2
    if dots:
        for i, colour in enumerate(_DOTS):
            cx = _PAD + i * (r * 2 + 8)
            draw.ellipse((cx - r, y - r, cx + r, y + r), fill=colour)

    font = _ui_font()
    tab_x = _PAD + (len(_DOTS) * (r * 2 + 8) + 10 if dots else 0)
    tab_w = int(draw.textlength(label, font=font)) + 28
    draw.rectangle((tab_x, 0, tab_x + tab_w, _CHROME_H), fill=palette["tab"])
    draw.text((tab_x + 14, y), label, fill=palette["text"], font=font, anchor="lm")

    canvas.paste(body, (0, _CHROME_H))
    draw.rectangle((0, 0, width - 1, canvas.height - 1), outline=palette["border"])
    return canvas


def _ui_font() -> Optional[ImageFont.ImageFont]:
    for name in ("segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, 15)
        except OSError:
            continue
    return ImageFont.load_default()
