"""Chart rendering for paper figures.

bar / line / pie reuse the existing publication-quality engine
(app.services.charts). scatter and grouped_bar are rendered here with the same
palette so all figures in a paper look like one system.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # non-interactive backend — must precede pyplot
import matplotlib.pyplot as plt
import numpy as np

from app.paper.schema import ChartSpec as PaperChart
from app.schemas import ChartSpec as BasicChart
from app.services.charts import _PALETTE, render_chart_png  # reuse palette + engine

_FIG_W, _FIG_H, _DPI = 8, 5, 150
_BG, _GRID, _TEXT, _AXIS = "#ffffff", "#e5e7eb", "#111827", "#6b7280"


def render_figure(chart: PaperChart, out_path: Path) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if chart.kind in ("bar", "line", "pie"):
        return render_chart_png(
            BasicChart(
                kind=chart.kind,
                title=chart.title,
                labels=[str(x) for x in chart.labels],
                values=[float(v) for v in chart.values],
                x_label=chart.x_label,
                y_label=chart.y_label,
            ),
            out_path,
        )
    if chart.kind == "grouped_bar":
        return _grouped_bar(chart, out_path)
    if chart.kind == "scatter":
        return _scatter(chart, out_path)
    # unknown kind → fall back to a bar chart rather than failing the render
    return render_chart_png(
        BasicChart(kind="bar", title=chart.title,
                   labels=[str(x) for x in chart.labels],
                   values=[float(v) for v in chart.values],
                   x_label=chart.x_label, y_label=chart.y_label),
        out_path,
    )


def _fig():
    fig, ax = plt.subplots(figsize=(_FIG_W, _FIG_H), dpi=_DPI)
    fig.patch.set_facecolor(_BG)
    ax.set_facecolor(_BG)
    ax.tick_params(colors=_AXIS, labelsize=10)
    return fig, ax


def _grouped_bar(chart: PaperChart, out: Path) -> Path:
    fig, ax = _fig()
    labels = [str(x) for x in chart.labels] or [f"G{i+1}" for i in range(
        max((len(s.values) for s in chart.series), default=0))]
    series = chart.series or []
    if not series:
        plt.close(fig)
        return render_chart_png(
            BasicChart(kind="bar", title=chart.title, labels=labels,
                       values=[float(v) for v in chart.values],
                       x_label=chart.x_label, y_label=chart.y_label), out)

    n_groups = len(labels)
    n_series = len(series)
    width = 0.8 / max(n_series, 1)
    x = np.arange(n_groups)

    for i, s in enumerate(series):
        vals = [float(v) for v in s.values][:n_groups]
        vals += [0.0] * (n_groups - len(vals))
        ax.bar(x + i * width - 0.4 + width / 2, vals, width=width,
               label=s.name or f"Series {i+1}",
               color=_PALETTE[i % len(_PALETTE)], edgecolor="white",
               linewidth=0.7, zorder=3)

    ax.set_title(chart.title or "", fontsize=14, fontweight="bold", color=_TEXT, pad=12)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_xlabel(chart.x_label or "", fontsize=11, color=_AXIS, labelpad=8)
    ax.set_ylabel(chart.y_label or "Value", fontsize=11, color=_AXIS, labelpad=8)
    ax.yaxis.grid(True, color=_GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    ax.legend(fontsize=9, frameon=False, ncol=min(n_series, 4))

    fig.tight_layout(pad=1.6)
    fig.savefig(str(out), dpi=_DPI, bbox_inches="tight", facecolor=_BG)
    plt.close(fig)
    return out


def _scatter(chart: PaperChart, out: Path) -> Path:
    """x from `labels` (numeric-coerced) or index; y from `values`.
    Additional `series` are plotted as extra point sets."""
    fig, ax = _fig()

    def _as_x(labels: list[str], n: int) -> list[float]:
        try:
            return [float(v) for v in labels][:n]
        except (TypeError, ValueError):
            return list(range(n))

    ys = [float(v) for v in chart.values]
    if ys:
        xs = _as_x([str(x) for x in chart.labels], len(ys)) or list(range(len(ys)))
        if len(xs) < len(ys):
            xs = list(range(len(ys)))
        ax.scatter(xs, ys, s=48, color=_PALETTE[0], edgecolor="white",
                   linewidth=0.8, zorder=3, label=chart.title or None)

    for i, s in enumerate(chart.series, start=1):
        sv = [float(v) for v in s.values]
        sx = _as_x([str(x) for x in chart.labels], len(sv)) or list(range(len(sv)))
        if len(sx) < len(sv):
            sx = list(range(len(sv)))
        ax.scatter(sx, sv, s=48, color=_PALETTE[i % len(_PALETTE)],
                   edgecolor="white", linewidth=0.8, zorder=3,
                   label=s.name or f"Series {i}")

    ax.set_title(chart.title or "", fontsize=14, fontweight="bold", color=_TEXT, pad=12)
    ax.set_xlabel(chart.x_label or "", fontsize=11, color=_AXIS, labelpad=8)
    ax.set_ylabel(chart.y_label or "", fontsize=11, color=_AXIS, labelpad=8)
    ax.grid(True, color=_GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    if chart.series:
        ax.legend(fontsize=9, frameon=False)

    fig.tight_layout(pad=1.6)
    fig.savefig(str(out), dpi=_DPI, bbox_inches="tight", facecolor=_BG)
    plt.close(fig)
    return out
