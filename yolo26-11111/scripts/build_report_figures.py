#!/usr/bin/env python3
"""Create report figures for the trained YOLO11n fruit detector."""

from __future__ import annotations

import csv
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS_CSV = ROOT / "runs" / "yolo11n-fruit-detect" / "results.csv"
OUTPUT_DIR = ROOT / "report_assets"
MATPLOTLIB_CACHE = ROOT / ".matplotlib-cache"
MATPLOTLIB_CACHE.mkdir(exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(MATPLOTLIB_CACHE))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.font_manager import FontProperties
from matplotlib.patches import FancyBboxPatch, Patch
from matplotlib.ticker import FormatStrFormatter


FONT_SIZE = 24
COLORS = {
    "blue": "#1d4ed8",
    "teal": "#0f766e",
    "green": "#16a34a",
    "orange": "#ea580c",
    "red": "#be123c",
    "purple": "#7c3aed",
    "ink": "#0f172a",
    "grid": "#cbd5e1",
}
METRIC_COLUMNS = {
    "Precision": "metrics/precision(B)",
    "Recall": "metrics/recall(B)",
    "mAP@0.5": "metrics/mAP50(B)",
    "mAP@0.5:0.95": "metrics/mAP50-95(B)",
}
LOSS_COLUMNS = {
    "Train box loss": "train/box_loss",
    "Train class loss": "train/cls_loss",
    "Train DFL loss": "train/dfl_loss",
    "Validation box loss": "val/box_loss",
}
TEST_METRICS = {
    "All": {"Precision": 0.851, "Recall": 0.917, "mAP@0.5": 0.931, "mAP@0.5:0.95": 0.784},
    "Apple": {"Precision": 0.900, "Recall": 0.964, "mAP@0.5": 0.975, "mAP@0.5:0.95": 0.861},
    "Banana": {"Precision": 0.547, "Recall": 0.818, "mAP@0.5": 0.781, "mAP@0.5:0.95": 0.629},
    "Litchi": {"Precision": 0.955, "Recall": 0.949, "mAP@0.5": 0.973, "mAP@0.5:0.95": 0.773},
    "Pear": {"Precision": 1.000, "Recall": 0.937, "mAP@0.5": 0.995, "mAP@0.5:0.95": 0.875},
}
TEST_INSTANCES = {"Apple": 28, "Banana": 11, "Litchi": 198, "Pear": 30}
TOTAL_INSTANCES = {"Apple": 584, "Banana": 398, "Litchi": 2877, "Pear": 675}


def available_font_names() -> set[str]:
    return {item.name for item in font_manager.fontManager.ttflist}


def choose_font(candidates: tuple[str, ...]) -> str:
    fonts = available_font_names()
    for candidate in candidates:
        if candidate in fonts:
            return candidate
    return candidates[-1]


CHINESE_FONT_NAME = choose_font(("Microsoft YaHei", "PingFang SC", "Hiragino Sans GB", "Arial Unicode MS"))
ENGLISH_FONT_NAME = choose_font(("Times New Roman", "DejaVu Serif"))
ZH_FONT = FontProperties(family=CHINESE_FONT_NAME, size=FONT_SIZE)
ZH_BOLD_FONT = FontProperties(family=CHINESE_FONT_NAME, size=FONT_SIZE, weight="bold")
EN_FONT = FontProperties(family=ENGLISH_FONT_NAME, size=FONT_SIZE)

plt.rcParams.update(
    {
        "axes.unicode_minus": False,
        "font.size": FONT_SIZE,
        "axes.labelsize": FONT_SIZE,
        "axes.titlesize": FONT_SIZE,
        "legend.fontsize": FONT_SIZE,
        "xtick.labelsize": FONT_SIZE,
        "ytick.labelsize": FONT_SIZE,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "axes.edgecolor": COLORS["ink"],
        "axes.linewidth": 1.8,
    }
)


def load_results() -> list[dict[str, float]]:
    rows: list[dict[str, float]] = []
    with RESULTS_CSV.open(newline="") as handle:
        for row in csv.DictReader(handle):
            rows.append({key.strip(): float(value) for key, value in row.items()})
    return rows


def style_axes(ax: plt.Axes, x_label: str, y_label: str) -> None:
    ax.set_xlabel(x_label, fontproperties=ZH_FONT, labelpad=22)
    ax.set_ylabel(y_label, fontproperties=ZH_FONT, labelpad=34)
    ax.grid(axis="y", color=COLORS["grid"], linewidth=1.0, alpha=0.9)
    ax.set_axisbelow(True)
    ax.tick_params(axis="x", length=8, width=1.5, pad=12)
    ax.tick_params(axis="y", length=8, width=1.5, pad=14)
    for label in [*ax.get_xticklabels(), *ax.get_yticklabels()]:
        label.set_fontproperties(EN_FONT)
        label.set_color(COLORS["ink"])
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def save_figure(fig: plt.Figure, output: Path) -> None:
    fig.savefig(output, dpi=220, bbox_inches="tight", pad_inches=0.28)
    plt.close(fig)


def rounded_bar(
    ax: plt.Axes,
    center: float,
    value: float,
    width: float,
    color: str,
    rounding: float,
) -> FancyBboxPatch:
    patch = FancyBboxPatch(
        (center - width / 2, 0),
        width,
        value,
        boxstyle=f"round,pad=0,rounding_size={rounding}",
        linewidth=0,
        facecolor=color,
        mutation_aspect=1,
        zorder=3,
    )
    ax.add_patch(patch)
    return patch


def draw_training_curves(
    rows: list[dict[str, float]],
    columns: dict[str, str],
    palette: list[str],
    output: Path,
    title: str,
    y_label: str,
    y_range: tuple[float, float],
    y_ticks: list[float],
    note_best: bool = False,
) -> None:
    fig, ax = plt.subplots(figsize=(18, 11))
    epochs = [int(row["epoch"]) for row in rows]

    for (label, column), color in zip(columns.items(), palette):
        ax.plot(
            epochs,
            [row[column] for row in rows],
            label=label,
            color=color,
            linewidth=3.2,
            marker="o",
            markersize=6.5,
        )

    fig.suptitle(title, fontproperties=ZH_BOLD_FONT, color=COLORS["ink"], y=0.98)
    ax.set_xlim(1, epochs[-1])
    ax.set_ylim(*y_range)
    ax.set_xticks([1, 5, 10, 15, 20, 25, 30])
    ax.set_yticks(y_ticks)
    ax.yaxis.set_major_formatter(FormatStrFormatter("%.2f"))
    style_axes(ax, "训练轮次", y_label)
    legend = fig.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, 0.92),
        ncol=2,
        frameon=False,
        columnspacing=2.0,
        handlelength=2.2,
    )
    for text in legend.get_texts():
        text.set_fontproperties(EN_FONT)

    if note_best:
        best = max(rows, key=lambda row: row["metrics/mAP50-95(B)"])
        best_epoch = int(best["epoch"])
        ax.axvline(best_epoch, color=COLORS["ink"], linestyle="--", linewidth=2.0, alpha=0.7)
        ax.text(
            0.64,
            0.18,
            (
                f"Best epoch {best_epoch}\n"
                f"mAP@0.5 = {best['metrics/mAP50(B)']:.3f}\n"
                f"mAP@0.5:0.95 = {best['metrics/mAP50-95(B)']:.3f}"
            ),
            transform=ax.transAxes,
            fontproperties=EN_FONT,
            color=COLORS["ink"],
            bbox={"boxstyle": "round,pad=0.45", "facecolor": "white", "edgecolor": COLORS["grid"]},
        )

    fig.subplots_adjust(left=0.16, bottom=0.16, right=0.97, top=0.72)
    save_figure(fig, output)


def save_test_metric_bars() -> None:
    metrics = list(METRIC_COLUMNS)
    names = list(TEST_METRICS)
    palette = [COLORS["blue"], COLORS["teal"], COLORS["green"], COLORS["orange"]]
    fig, ax = plt.subplots(figsize=(25, 12))
    x_positions = [index * 1.38 for index in range(len(names))]
    bar_width = 0.21
    offsets = [-1.65 * bar_width, -0.55 * bar_width, 0.55 * bar_width, 1.65 * bar_width]
    labels_by_class: dict[str, list[tuple[float, float]]] = {name: [] for name in names}

    for metric, color, offset in zip(metrics, palette, offsets):
        for position, name in zip(x_positions, names):
            value = TEST_METRICS[name][metric]
            center = position + offset
            rounded_bar(ax, center, value, bar_width, color, rounding=0.035)
            labels_by_class[name].append((center, value))

    for labels in labels_by_class.values():
        previous_y = -1.0
        for center, value in sorted(labels, key=lambda item: item[1]):
            label_y = max(value + 0.032, previous_y + 0.052)
            ax.text(
                center,
                label_y,
                f"{value:.2f}",
                ha="center",
                va="bottom",
                fontproperties=EN_FONT,
                color=COLORS["ink"],
                zorder=4,
            )
            previous_y = label_y
    fig.suptitle("测试集各类别检测指标", fontproperties=ZH_BOLD_FONT, color=COLORS["ink"], y=0.98)
    ax.set_xlim(x_positions[0] - 0.75, x_positions[-1] + 0.75)
    ax.set_ylim(0, 1.28)
    ax.set_xticks(x_positions, names)
    ax.set_yticks([0, 0.25, 0.50, 0.75, 1.00])
    ax.yaxis.set_major_formatter(FormatStrFormatter("%.2f"))
    style_axes(ax, "类别", "指标值")
    legend = fig.legend(
        handles=[Patch(facecolor=color, edgecolor="none", label=metric) for metric, color in zip(metrics, palette)],
        loc="upper center",
        bbox_to_anchor=(0.5, 0.92),
        ncol=4,
        frameon=False,
        columnspacing=1.4,
        handlelength=1.4,
    )
    for text in legend.get_texts():
        text.set_fontproperties(EN_FONT)
    fig.subplots_adjust(left=0.14, bottom=0.17, right=0.98, top=0.72)
    save_figure(fig, OUTPUT_DIR / "test_metrics_by_class.png")


def save_test_instance_counts() -> None:
    names = list(TEST_INSTANCES)
    values = [TEST_INSTANCES[name] for name in names]
    palette = [COLORS["red"], "#ca8a04", COLORS["purple"], COLORS["teal"]]
    fig, ax = plt.subplots(figsize=(15, 10))
    x_positions = list(range(len(names)))
    for position, value, color in zip(x_positions, values, palette):
        rounded_bar(ax, position, value, 0.55, color, rounding=0.06)
        ax.text(
            position,
            value + 7,
            str(value),
            ha="center",
            va="bottom",
            fontproperties=EN_FONT,
            color=COLORS["ink"],
        )
    ax.set_title("测试集目标实例数量分布", fontproperties=ZH_BOLD_FONT, color=COLORS["ink"], pad=30)
    ax.set_xlim(-0.55, len(names) - 0.45)
    ax.set_ylim(0, 228)
    ax.set_xticks(x_positions, names)
    ax.set_yticks([0, 50, 100, 150, 200])
    style_axes(ax, "类别", "实例数量")
    fig.subplots_adjust(left=0.18, bottom=0.18, right=0.97, top=0.86)
    save_figure(fig, OUTPUT_DIR / "test_instance_counts.png")


def save_test_share_by_class() -> None:
    names = list(TEST_INSTANCES)
    shares = [TEST_INSTANCES[name] / TOTAL_INSTANCES[name] * 100 for name in names]
    palette = [COLORS["red"], "#ca8a04", COLORS["purple"], COLORS["teal"]]
    fig, ax = plt.subplots(figsize=(15, 10))
    x_positions = list(range(len(names)))

    for position, name, share, color in zip(x_positions, names, shares, palette):
        rounded_bar(ax, position, share, 0.55, color, rounding=0.055)
        ax.text(
            position,
            share + 0.22,
            f"{share:.1f}%",
            ha="center",
            va="bottom",
            fontproperties=EN_FONT,
            color=COLORS["ink"],
        )
        ax.text(
            position,
            max(0.32, share * 0.48),
            f"{TEST_INSTANCES[name]}/{TOTAL_INSTANCES[name]}",
            ha="center",
            va="center",
            fontproperties=EN_FONT,
            color="white",
            zorder=4,
        )

    ax.set_title("各类别测试集实例占总体比例", fontproperties=ZH_BOLD_FONT, color=COLORS["ink"], pad=30)
    ax.set_xlim(-0.55, len(names) - 0.45)
    ax.set_ylim(0, 8.25)
    ax.set_xticks(x_positions, names)
    ax.set_yticks([0, 2, 4, 6, 8])
    ax.yaxis.set_major_formatter(FormatStrFormatter("%.0f%%"))
    style_axes(ax, "类别", "测试集占比")
    fig.subplots_adjust(left=0.18, bottom=0.18, right=0.97, top=0.86)
    save_figure(fig, OUTPUT_DIR / "test_share_by_class.png")


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    rows = load_results()
    draw_training_curves(
        rows,
        METRIC_COLUMNS,
        [COLORS["blue"], COLORS["teal"], COLORS["orange"], COLORS["red"]],
        OUTPUT_DIR / "training_accuracy_curves.png",
        "验证集精度指标随训练轮次变化",
        "指标值",
        (0.48, 0.99),
        [0.50, 0.60, 0.70, 0.80, 0.90],
        note_best=True,
    )
    draw_training_curves(
        rows,
        LOSS_COLUMNS,
        [COLORS["blue"], COLORS["red"], COLORS["green"], COLORS["purple"]],
        OUTPUT_DIR / "training_loss_curves.png",
        "训练与验证损失变化曲线",
        "损失值",
        (0.35, 2.80),
        [0.50, 1.00, 1.50, 2.00, 2.50],
    )
    save_test_metric_bars()
    save_test_instance_counts()
    save_test_share_by_class()
    print(f"Chinese font: {CHINESE_FONT_NAME}")
    print(f"English font: {ENGLISH_FONT_NAME}")
    print(f"Report figures saved to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
