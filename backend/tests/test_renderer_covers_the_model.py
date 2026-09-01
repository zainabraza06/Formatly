"""The page has to draw everything the document can carry.

The other half of the sweep. Twice now a concept has been added to the model,
the parser, the actions and the export, and the renderer has been left behind:
bullets were stored and not drawn, and a table's borders were set on the node
while every cell went on drawing its own four edges. Both times the command
worked, the version committed, the export was right, and the page did not
move — which reads as the command failing.

Nothing here renders anything; it reads the renderer's source and asks whether
each thing the model can say appears in it at all. That is a coarse question,
and a coarse answer is what was missing: an edit that silently does not apply
leaves no other trace.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.docos.graph import Style

FRONTEND = Path(__file__).resolve().parents[2] / "frontend" / "src" / "components" / "docos"
NODE_VIEW = FRONTEND / "NodeView.tsx"

# What a node can carry in `metadata` that changes how it looks. A key here
# that the renderer never mentions is a document saying something the page
# cannot show.
VISIBLE_METADATA = [
    "list",             # a bullet or a number beside the paragraph
    "borders",          # which edges a table draws
    "line_spacing",     # how far apart its lines are
    "space_before_pt",  # the gap above
    "space_after_pt",   # and below
    "indent_left_pt",
    "indent_first_line_pt",
]


@pytest.mark.skipif(not NODE_VIEW.exists(), reason="frontend not present")
@pytest.mark.parametrize("field", sorted(Style.model_fields))
def test_every_style_the_model_carries_is_drawn(field: str):
    """A style field the page never reads is a command that cannot show."""
    assert field in NODE_VIEW.read_text(encoding="utf-8"), (
        f"Style.{field} is not mentioned in NodeView.tsx — the model can carry "
        f"it and the page cannot draw it")


@pytest.mark.skipif(not NODE_VIEW.exists(), reason="frontend not present")
@pytest.mark.parametrize("key", VISIBLE_METADATA)
def test_every_visible_property_is_drawn(key: str):
    assert key in NODE_VIEW.read_text(encoding="utf-8"), (
        f"metadata[{key!r}] changes how a document looks and NodeView.tsx "
        f"never mentions it")
