"""Render the Terminal-Bench 2.1 task-level distribution chart for this post."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "assets" / "data" / "navi-agent-terminal-bench-2-1-task-metrics.json"
OUTPUT_PATH = ROOT / "assets" / "img" / "202610" / "navi-agent-terminal-bench-2-1-ranked-task-dots.png"

COLORS = {"point": "#3b82f6", "tail": "#e11d48", "median": "#0891b2", "p90": "#db2777"}

def duration(value: float) -> str:
    seconds = int(round(value / 1000))
    return f"{seconds // 60}m {seconds % 60}s"

def tokens(value: float) -> str:
    return f"{value / 1_000_000:.2f}M" if value >= 1_000_000 else f"{value / 1_000:.0f}K"

def percentile(values: list[int], fraction: float) -> int:
    return values[int(-(-len(values) * fraction // 1)) - 1]

def panel(ax: plt.Axes, values: list[int], title: str, subtitle: str, formatter) -> None:
    ranks = list(range(1, len(values) + 1))
    median = percentile(values, 0.5)
    p90 = percentile(values, 0.9)
    tail_start = 72

    ax.scatter(ranks[:tail_start], values[:tail_start], s=22, color=COLORS["point"], alpha=0.82, linewidths=0)
    ax.scatter(ranks[tail_start:], values[tail_start:], s=28, color=COLORS["tail"], alpha=0.96, linewidths=0)
    ax.plot(ranks, values, color=COLORS["point"], alpha=0.3, linewidth=1.1)
    ax.axhline(median, color=COLORS["median"], linestyle=(0, (5, 4)), linewidth=1.4)
    ax.axhline(p90, color=COLORS["p90"], linestyle=(0, (5, 4)), linewidth=1.4)

    ax.text(0.01, 1.10, title, transform=ax.transAxes, fontsize=16, fontweight="bold", color="#172033")
    ax.text(0.01, 1.015, subtitle, transform=ax.transAxes, fontsize=10.5, color="#65738d")
    ax.text(0.985, median, f" median {formatter(median)} ", transform=ax.get_yaxis_transform(), ha="right", va="bottom", fontsize=9.5, color=COLORS["median"], bbox={"facecolor": "#f8fbff", "edgecolor": "none", "pad": 1.5})
    ax.text(0.985, p90, f" P90 {formatter(p90)} ", transform=ax.get_yaxis_transform(), ha="right", va="bottom", fontsize=9.5, color=COLORS["p90"], bbox={"facecolor": "#fff7fa", "edgecolor": "none", "pad": 1.5})

    ax.set_xlim(0, 90)
    ax.set_xticks([1, 25, 50, 75, 89])
    ax.set_xlabel("Tasks ranked by this metric", color="#65738d")
    ax.grid(axis="y", color="#dce5f2", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.spines["bottom"].set_color("#c9d5e6")
    ax.tick_params(axis="both", colors="#65738d", length=0, pad=7)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: formatter(value)))

def main() -> None:
    data = json.loads(DATA_PATH.read_text())
    figure, axes = plt.subplots(3, 1, figsize=(14, 12))
    figure.set_facecolor("#ffffff")
    figure.suptitle("Navi-agent on Terminal-Bench 2.1: each point is one task", x=0.06, y=0.985, ha="left", fontsize=23, fontweight="bold", color="#172033")
    figure.text(0.06, 0.943, "89 tasks · deepseek-flash · Modal sandbox · tasks are independently ranked in each panel", fontsize=11.5, color="#65738d")
    figure.subplots_adjust(top=0.885, bottom=0.065, left=0.075, right=0.97, hspace=0.62)

    panel(axes[0], data["iterations"], "Iterations", "Budget is 50; summary fallback can report 51.", str)
    panel(axes[1], data["duration_ms"], "Agent-loop duration", "Runtime duration only; Harbor verifier post-processing is excluded.", duration)
    panel(axes[2], data["input_tokens"], "Input tokens", "Runtime-trace input tokens; provider billing uses a broader accounting boundary.", tokens)

    figure.savefig(OUTPUT_PATH, dpi=180, bbox_inches="tight", facecolor=figure.get_facecolor())
    print(OUTPUT_PATH)

if __name__ == "__main__":
    main()
