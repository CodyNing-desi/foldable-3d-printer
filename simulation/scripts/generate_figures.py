import json
import sys
from pathlib import Path

import imageio.v2 as imageio
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager

SIMULATION_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SIMULATION_DIR / "src"))

from foldsim.evaluate import evaluate_candidate
from foldsim.registry import load_candidates

FIGURES = SIMULATION_DIR / "figures"
ANIMATIONS = SIMULATION_DIR / "animations"
RESULTS = SIMULATION_DIR / "results"
COLORS = {"blue": "#0072B2", "orange": "#E69F00", "green": "#009E73", "red": "#D55E00", "purple": "#CC79A7", "grey": "#6B7280"}


def _font():
    path = Path("C:/Windows/Fonts/msyh.ttc")
    if path.exists():
        font_manager.fontManager.addfont(str(path))
        return font_manager.FontProperties(fname=str(path)).get_name()
    return "DejaVu Sans"


def _polygons(geometry):
    if geometry.geom_type == "Polygon":
        yield geometry
    elif hasattr(geometry, "geoms"):
        for part in geometry.geoms:
            yield from _polygons(part)


def plot_state(ax, state, title):
    for polygon in state["fixed"].values():
        for part in _polygons(polygon):
            x, y = part.exterior.xy
            ax.fill(x, y, color="#9CA3AF", alpha=0.35)
            ax.plot(x, y, color=COLORS["grey"], linewidth=0.8)
    for polygon in state["moving"].values():
        for part in _polygons(polygon):
            x, y = part.exterior.xy
            ax.fill(x, y, color=COLORS["blue"], alpha=0.30)
            ax.plot(x, y, color=COLORS["blue"], linewidth=1.1)
    for polygon in state["extra"].values():
        for part in _polygons(polygon):
            x, y = part.exterior.xy
            ax.plot(x, y, color=COLORS["orange"], linewidth=1.0, linestyle="--")
    ax.set_title(title, fontsize=10)
    ax.set_aspect("equal", adjustable="box")
    ax.autoscale_view()
    ax.grid(alpha=0.15)
    ax.set_xlabel("侧视 X / mm", fontsize=8)
    ax.set_ylabel("Z / mm", fontsize=8)
    ax.tick_params(labelsize=7)


def _save(fig, name):
    fig.savefig(FIGURES / f"{name}.png", dpi=180, facecolor="white")
    svg_path = FIGURES / f"{name}.svg"
    fig.savefig(svg_path, facecolor="white")
    svg_path.write_text(
        "\n".join(line.rstrip() for line in svg_path.read_text(encoding="utf-8").splitlines()) + "\n",
        encoding="utf-8",
    )
    plt.close(fig)


def screening_figure(screen):
    order = screen.sort_values("storage_ratio")
    x = np.arange(len(order))
    fig, ax = plt.subplots(figsize=(12, 6), layout="constrained")
    ax.bar(x - 0.2, order["core_storage_ratio"], width=0.4, color=COLORS["blue"], label="裸机芯体积比")
    bars = ax.bar(x + 0.2, order["storage_ratio"], width=0.4, color=COLORS["orange"], label="运输系统体积比")
    for bar, passed in zip(bars, order["passed_screen"]):
        if not passed:
            bar.set_hatch("//")
            bar.set_edgecolor(COLORS["red"])
    ax.axhline(0.8, color=COLORS["red"], linestyle="--", linewidth=1.2, label="初筛阈值 0.80")
    ax.set_xticks(x, order["id"])
    ax.set_ylabel("折叠体积 / 工作体积")
    ax.set_title("15 套候选统一几何初筛｜斜线表示至少一项硬约束失败")
    ax.legend(ncol=3)
    ax.grid(axis="y", alpha=0.2)
    _save(fig, "screening_storage_comparison")


def deep_figure(deep):
    fig, ax = plt.subplots(figsize=(10, 7), layout="constrained")
    passed = deep[deep["passed_screen"]]
    failed = deep[~deep["passed_screen"]]
    for frame, marker, label in ((passed, "o", "通过 L1"), (failed, "x", "L1 失败（仅示指示值）")):
        if frame.empty:
            continue
        marker_style = {"edgecolor": "black"} if marker == "o" else {}
        scatter = ax.scatter(
            frame["storage_ratio"], frame["p95_mm"], s=frame["estimated_incremental_cost_CNY"] / 4,
            c=frame["tip_deflection_mm"], cmap="viridis", marker=marker,
            alpha=0.8, linewidth=0.4, label=label, **marker_style,
        )
        for row in frame.itertuples():
            ax.annotate(row.id, (row.storage_ratio, row.p95_mm), xytext=(5, 5), textcoords="offset points")
    if passed.shape[0] + failed.shape[0]:
        fig.colorbar(scatter, ax=ax, label="10 N 侧载末端挠度 / mm")
    ax.set(xlabel="运输系统收纳体积比", ylabel="重复定位径向误差 P95 / mm", title="收纳—误差—成本—刚度关系｜点面积表示增量成本")
    ax.legend()
    ax.grid(alpha=0.2)
    _save(fig, "deep_tradeoff")


def optimization_figure(optimization):
    fig, ax = plt.subplots(figsize=(10, 7), layout="constrained")
    feasible = optimization[(optimization["feasible"]) & np.isfinite(optimization["storage_ratio"])]
    for candidate_id, frame in feasible.groupby("id"):
        frame = frame.sort_values("storage_ratio")
        ax.plot(frame["storage_ratio"], frame["tip_deflection_mm"], marker="o", markersize=3, linewidth=1, label=candidate_id)
    ax.set(xlabel="运输系统收纳体积比", ylabel="10 N 侧载末端挠度 / mm", title="NSGA-II 可行 Pareto 解（末代非支配集）")
    ax.legend(ncol=4, fontsize=8)
    ax.grid(alpha=0.2)
    _save(fig, "optimization_pareto")


def sensitivity_figure(sensitivity):
    pivot = sensitivity[sensitivity["output"] == "storage_ratio"].pivot(index="id", columns="parameter", values="spearman_rho")
    fig, ax = plt.subplots(figsize=(12, 7), layout="constrained")
    image = ax.imshow(pivot, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
    ax.set_xticks(np.arange(len(pivot.columns)), pivot.columns, rotation=35, ha="right")
    ax.set_yticks(np.arange(len(pivot.index)), pivot.index)
    for i in range(len(pivot.index)):
        for j in range(len(pivot.columns)):
            value = pivot.iloc[i, j]
            if np.isfinite(value):
                ax.text(j, i, f"{value:.2f}", ha="center", va="center", fontsize=7, color="white" if abs(value) > 0.55 else "black")
    fig.colorbar(image, ax=ax, label="与收纳体积比的 Spearman ρ")
    ax.set_title("拉丁超立方参数敏感性｜空白表示该机构无此变量")
    _save(fig, "sensitivity_storage_heatmap")


def motion_outputs(candidates):
    contact_rows = 5
    fig, axes = plt.subplots(contact_rows, 6, figsize=(18, 15), layout="constrained")
    for row, (candidate_id, spec) in enumerate(candidates.items()):
        result = evaluate_candidate(spec, steps=21)
        trace = result["trace"]
        axes_row = row // 3
        col = (row % 3) * 2
        plot_state(axes[axes_row, col], trace[0], f"{candidate_id} 工作态")
        plot_state(axes[axes_row, col + 1], trace[-1], f"{candidate_id} 收纳态")
        frames = []
        frame_dir = ANIMATIONS / candidate_id
        frame_dir.mkdir(parents=True, exist_ok=True)
        for index, state in enumerate(trace):
            frame_fig, frame_ax = plt.subplots(figsize=(5, 4), dpi=100, layout="constrained")
            plot_state(frame_ax, state, f"{candidate_id} {spec['name']}｜{index / (len(trace) - 1):.0%}")
            frame_ax.set_xlim(-150, 550)
            frame_ax.set_ylim(-80, 450)
            path = frame_dir / f"frame_{index:03d}.png"
            frame_fig.savefig(path, facecolor="white")
            plt.close(frame_fig)
            frames.append(imageio.imread(path))
        imageio.mimsave(ANIMATIONS / f"{candidate_id}_fold.gif", frames, duration=0.12, loop=0)
        print(candidate_id, "motion states and GIF written")
    _save(fig, "all_candidates_work_and_folded")


def main():
    FIGURES.mkdir(exist_ok=True)
    ANIMATIONS.mkdir(exist_ok=True)
    plt.rcParams["font.family"] = _font()
    plt.rcParams["axes.unicode_minus"] = False
    screen = pd.read_csv(RESULTS / "screening_summary.csv")
    deep = pd.read_csv(RESULTS / "deep_summary.csv")
    optimization = pd.read_csv(RESULTS / "optimization_solutions.csv")
    sensitivity = pd.read_csv(RESULTS / "sensitivity_rank_correlations.csv")
    screening_figure(screen)
    deep_figure(deep)
    optimization_figure(optimization)
    sensitivity_figure(sensitivity)
    candidates = load_candidates(SIMULATION_DIR / "config" / "candidates.json")
    motion_outputs(candidates)
    manifest = {
        "audience": "engineering concept-screening report",
        "publisher_requirements": "not specified; general provisional figures",
        "raw_data": ["results/screening_summary.csv", "results/deep_summary.csv", "results/optimization_solutions.csv", "results/sensitivity_rank_correlations.csv"],
        "transformations": ["declared pass/fail grouping", "feasible-only Pareto plot", "Spearman rank correlation"],
        "missing_data": "empty cells mean not applicable; no observations are connected across missing values",
        "color_encoding": "color is redundant with labels, markers, hatching and direct candidate IDs",
        "animations": "21 actual evaluated states per candidate; GIF is a visualization of L1 geometry, not physical video",
    }
    with (FIGURES / "figure_manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
