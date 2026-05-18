"""
Chart rendering with matplotlib.
Produces publication-quality PNGs with titles, axis labels,
value annotations, and a clean visual style.
"""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")  # non-interactive backend — must be before pyplot import

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from pathlib import Path

from app.schemas import ChartSpec

# ── colour palette ────────────────────────────────────────────────────────────
_PALETTE = [
    "#4f86f7",  # blue
    "#22c55e",  # green
    "#f43f5e",  # rose
    "#a855f7",  # violet
    "#f59e0b",  # amber
    "#06b6d4",  # cyan
    "#84cc16",  # lime
    "#ec4899",  # pink
]

_FIG_W, _FIG_H = 10, 6          # inches
_DPI           = 150             # 1500 × 900 px output
_BG            = "#ffffff"
_GRID_COLOR    = "#e5e7eb"
_SPINE_COLOR   = "#d1d5db"
_TEXT_COLOR    = "#111827"
_AXIS_COLOR    = "#6b7280"


def _setup_figure() -> tuple[plt.Figure, plt.Axes]:
    fig, ax = plt.subplots(figsize=(_FIG_W, _FIG_H), dpi=_DPI)
    fig.patch.set_facecolor(_BG)
    ax.set_facecolor(_BG)
    for spine in ax.spines.values():
        spine.set_color(_SPINE_COLOR)
        spine.set_linewidth(0.8)
    ax.tick_params(colors=_AXIS_COLOR, labelsize=10)
    return fig, ax


def _apply_title(ax: plt.Axes, chart: ChartSpec) -> None:
    title = (chart.title or "Chart").strip()
    ax.set_title(title, fontsize=15, fontweight="bold", color=_TEXT_COLOR, pad=14)


def _safe_labels(chart: ChartSpec) -> list[str]:
    n = len(chart.values)
    if chart.labels and len(chart.labels) >= n:
        return [str(lbl) for lbl in chart.labels[:n]]
    return [f"Item {i + 1}" for i in range(n)]


def _safe_values(chart: ChartSpec) -> list[float]:
    if not chart.values:
        return [1.0, 2.0, 3.0]
    return [float(v) for v in chart.values]


# ── bar chart ─────────────────────────────────────────────────────────────────
def _bar(ax: plt.Axes, chart: ChartSpec) -> None:
    values = _safe_values(chart)
    labels = _safe_labels(chart)
    n      = len(values)
    colors = [_PALETTE[i % len(_PALETTE)] for i in range(n)]
    x      = np.arange(n)

    bars = ax.bar(x, values, color=colors, edgecolor="white",
                  linewidth=0.8, width=0.6, zorder=3)

    # value labels above each bar
    for bar, val in zip(bars, values):
        fmt = f"{val:,.1f}" if val != int(val) else f"{int(val):,}"
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(values) * 0.015,
            fmt,
            ha="center", va="bottom",
            fontsize=9, fontweight="bold", color=_TEXT_COLOR,
        )

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=0 if n <= 6 else 25,
                       ha="center" if n <= 6 else "right", fontsize=10)
    ax.set_xlabel(chart.x_label or "", fontsize=11, color=_AXIS_COLOR, labelpad=8)
    ax.set_ylabel(chart.y_label or "Value",   fontsize=11, color=_AXIS_COLOR, labelpad=8)
    ax.set_ylim(0, max(values) * 1.18)
    ax.yaxis.grid(True, color=_GRID_COLOR, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)


# ── line chart ────────────────────────────────────────────────────────────────
def _line(ax: plt.Axes, chart: ChartSpec) -> None:
    values = _safe_values(chart)
    labels = _safe_labels(chart)
    n      = len(values)
    x      = np.arange(n)

    ax.plot(x, values, color=_PALETTE[0], linewidth=2.2,
            marker="o", markersize=7, markerfacecolor="white",
            markeredgecolor=_PALETTE[0], markeredgewidth=2, zorder=3)

    # shade area under line
    ax.fill_between(x, values, alpha=0.12, color=_PALETTE[0], zorder=2)

    # value labels on each point
    for xi, val in zip(x, values):
        fmt = f"{val:,.1f}" if val != int(val) else f"{int(val):,}"
        ax.text(xi, val + max(values) * 0.025, fmt,
                ha="center", va="bottom", fontsize=9,
                fontweight="bold", color=_TEXT_COLOR)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=0 if n <= 6 else 25,
                       ha="center" if n <= 6 else "right", fontsize=10)
    ax.set_xlabel(chart.x_label or "", fontsize=11, color=_AXIS_COLOR, labelpad=8)
    ax.set_ylabel(chart.y_label or "Value",   fontsize=11, color=_AXIS_COLOR, labelpad=8)
    ax.set_ylim(0, max(values) * 1.22)
    ax.grid(True, color=_GRID_COLOR, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)


# ── pie chart ─────────────────────────────────────────────────────────────────
def _pie(ax: plt.Axes, chart: ChartSpec) -> None:
    values = _safe_values(chart)
    labels = _safe_labels(chart)
    colors = [_PALETTE[i % len(_PALETTE)] for i in range(len(values))]

    wedges, texts, autotexts = ax.pie(
        values,
        labels=None,           # we'll use a legend instead
        colors=colors,
        autopct="%1.1f%%",
        startangle=140,
        pctdistance=0.78,
        wedgeprops=dict(linewidth=1.5, edgecolor="white"),
    )
    for at in autotexts:
        at.set_fontsize(9)
        at.set_fontweight("bold")
        at.set_color("white")

    ax.legend(
        wedges, labels,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.12),
        ncol=min(len(labels), 4),
        fontsize=9,
        frameon=False,
    )
    ax.axis("equal")


# ── public entry point ────────────────────────────────────────────────────────
def render_chart_png(chart: ChartSpec, out_path: Path) -> Path:
    """Render chart to a PNG file and return the path."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = _setup_figure()
    _apply_title(ax, chart)

    if chart.kind == "bar":
        _bar(ax, chart)
    elif chart.kind == "line":
        _line(ax, chart)
    elif chart.kind == "pie":
        _pie(ax, chart)
    else:
        _bar(ax, chart)

    fig.tight_layout(pad=1.8)
    fig.savefig(str(out_path), dpi=_DPI, bbox_inches="tight", facecolor=_BG)
    plt.close(fig)
    return out_path
