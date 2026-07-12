"""IEEE paper pipeline.

    raw material ──generate_paper()──▶ PaperSpec JSON (fully-styled)
                  ──render_paper()───▶ IEEE-formatted DOCX
"""
from app.paper.generator import PaperGenerationError, generate_paper
from app.paper.renderer import render_paper
from app.paper.schema import PaperSpec
from app.paper.stylesheet import resolve

__all__ = [
    "generate_paper",
    "render_paper",
    "resolve",
    "PaperSpec",
    "PaperGenerationError",
]
