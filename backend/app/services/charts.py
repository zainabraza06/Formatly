from __future__ import annotations

import math
from pathlib import Path
from typing import Iterable

import png  # type: ignore

from app.schemas import ChartSpec


def _clamp(v: int) -> int:
    return 0 if v < 0 else 255 if v > 255 else v


def _color(i: int) -> tuple[int, int, int, int]:
    palette = [
        (56, 189, 248, 220),  # sky
        (34, 197, 94, 220),  # emerald
        (244, 63, 94, 220),  # rose
        (168, 85, 247, 220),  # violet
        (245, 158, 11, 220),  # amber
        (148, 163, 184, 220),  # slate
    ]
    return palette[i % len(palette)]


def _new_canvas(w: int, h: int, bg: tuple[int, int, int, int]) -> list[list[int]]:
    r, g, b, a = bg
    row = [r, g, b, a] * w
    return [row.copy() for _ in range(h)]


def _set_px(buf: list[list[int]], x: int, y: int, c: tuple[int, int, int, int]) -> None:
    if y < 0 or y >= len(buf):
        return
    w = len(buf[0]) // 4
    if x < 0 or x >= w:
        return
    i = x * 4
    # Alpha blend onto existing pixel
    br, bg, bb, ba = buf[y][i : i + 4]
    cr, cg, cb, ca = c
    alpha = ca / 255.0
    inv = 1.0 - alpha
    nr = int(cr * alpha + br * inv)
    ng = int(cg * alpha + bg * inv)
    nb = int(cb * alpha + bb * inv)
    na = int(255)
    buf[y][i : i + 4] = [_clamp(nr), _clamp(ng), _clamp(nb), na]


def _draw_line(buf: list[list[int]], x0: int, y0: int, x1: int, y1: int, c: tuple[int, int, int, int]) -> None:
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    x, y = x0, y0
    while True:
        _set_px(buf, x, y, c)
        if x == x1 and y == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x += sx
        if e2 <= dx:
            err += dx
            y += sy


def _fill_rect(buf: list[list[int]], x: int, y: int, w: int, h: int, c: tuple[int, int, int, int]) -> None:
    for yy in range(y, y + h):
        for xx in range(x, x + w):
            _set_px(buf, xx, yy, c)


def _draw_axes(buf: list[list[int]], x0: int, y0: int, x1: int, y1: int) -> None:
    axis = (148, 163, 184, 180)
    _draw_line(buf, x0, y1, x1, y1, axis)
    _draw_line(buf, x0, y0, x0, y1, axis)


def _safe_values(values: list[float]) -> list[float]:
    if not values:
        return [1.0, 2.0, 3.0]
    return [float(v) for v in values]


def render_chart_png(chart: ChartSpec, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    w, h = 900, 480
    # Use an opaque background: it avoids unexpected rendering when embedded
    # into DOCX/PDF viewers that don't handle alpha consistently.
    buf = _new_canvas(w, h, (255, 255, 255, 255))

    # Plot area
    pad = 50
    x0, y0 = pad, pad
    x1, y1 = w - pad, h - pad

    values = _safe_values(chart.values)
    labels = chart.labels or [f"Item {i+1}" for i in range(len(values))]

    _draw_axes(buf, x0, y0, x1, y1)

    if chart.kind == "bar":
        maxv = max(values) if max(values) > 0 else 1.0
        n = len(values)
        slot = max(1, (x1 - x0) // max(1, n))
        barw = max(6, int(slot * 0.6))
        for i, v in enumerate(values):
            bh = int((y1 - y0) * (v / maxv))
            bx = x0 + i * slot + (slot - barw) // 2
            by = y1 - bh
            _fill_rect(buf, bx, by, barw, bh, _color(i))

    elif chart.kind == "line":
        maxv = max(values) if max(values) > 0 else 1.0
        n = len(values)
        step = (x1 - x0) / max(1, n - 1)
        pts: list[tuple[int, int]] = []
        for i, v in enumerate(values):
            x = int(x0 + i * step)
            y = int(y1 - (y1 - y0) * (v / maxv))
            pts.append((x, y))
        c = (56, 189, 248, 220)
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            _draw_line(buf, ax, ay, bx, by, c)
        for x, y in pts:
            _fill_rect(buf, x - 3, y - 3, 6, 6, c)

    elif chart.kind == "pie":
        total = sum(abs(v) for v in values) or 1.0
        cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
        r = min(x1 - x0, y1 - y0) // 3
        start = 0.0
        for i, v in enumerate(values):
            frac = abs(v) / total
            end = start + frac * 2 * math.pi
            col = _color(i)
            # Fill sector by scanning pixels in bounding box
            for yy in range(cy - r, cy + r):
                for xx in range(cx - r, cx + r):
                    dx, dy = xx - cx, yy - cy
                    if dx * dx + dy * dy > r * r:
                        continue
                    ang = math.atan2(dy, dx)
                    if ang < 0:
                        ang += 2 * math.pi
                    if start <= ang < end:
                        _set_px(buf, xx, yy, col)
            start = end

    # Write PNG (RGBA). Be explicit about non-greyscale output; otherwise pypng
    # may default to greyscale+alpha and reject 4-channel rows.
    writer = png.Writer(width=w, height=h, alpha=True, greyscale=False, bitdepth=8)
    with out_path.open("wb") as f:
        writer.write(f, buf)

    return out_path
