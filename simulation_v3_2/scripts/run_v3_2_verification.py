"""V3.2 Continuous Collision Re-Verification, FEA Consistency, and Visualization Generator."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from foldsim_v3_2.evaluate3d import evaluate_candidate_3d
from foldsim_v3_2.fea3d import evaluate_candidate_fea3d
from foldsim_v3_2.geometry3d import OBB, rot_z, swept_obb_vs_obb, verify_interval_collision
from foldsim_v3_2.mechanisms3d import scissor_state
from foldsim_v3_2.registry import load_candidates

plt.rcParams["font.sans-serif"] = ["Noto Sans CJK SC", "Noto Sans CJK JP", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def run_candidate_suite() -> list[dict]:
    cands = load_candidates(ROOT / "config" / "candidates_v3_2.json")
    targets = [
        ("F09", {"lift_mm": 85.0, "shift_x_mm": 0.0, "arm_fold_enabled": 1}, "Primary (215mm folding X-arm)"),
        ("F07", {"lift_mm": 75.0, "shift_x_mm": 0.0, "arm_fold_enabled": 1}, "Conditional Backup (Zero-gap tolerance risk)"),
        ("SCZ", {"arm_length_mm": 154.0, "height_fold_mm": 45.0, "height_work_max_mm": 270.0}, "Bench-only Mechanism Prototype"),
        ("F08", {"lift_mm": 25.0, "shift_x_mm": -75.0, "arm_fold_enabled": 1}, "Fallback (lift=25mm, compact)"),
        ("F08", {"lift_mm": 30.0, "shift_x_mm": -75.0, "arm_fold_enabled": 1}, "Fallback (lift=30mm, +5mm clearance)"),
        ("F12", {"overlap_mm": 52.0, "outer_size_mm": 60.0, "preload_rail": 1, "motor_side_mounted": 1}, "No-Go / Archived (6-week rail risk)"),
    ]

    results = []
    for cid, params, role in targets:
        spec = cands[cid]
        ev = evaluate_candidate_3d(spec, parameters=params, steps=31, max_depth=12)
        fea = evaluate_candidate_fea3d(cid, spec, parameters=params, n_sub=8 if cid == "SCZ" else 32, ideal_rigid_joints=False)
        fea_ideal = evaluate_candidate_fea3d(cid, spec, parameters=params, n_sub=8 if cid == "SCZ" else 32, ideal_rigid_joints=True)
        row = {
            "id": cid if cid != "F08" else f"F08_L{int(params['lift_mm'])}",
            "base_id": cid,
            "role": role,
            "collision_status": ev["collision_status"],
            "passed_screen": ev["passed_screen"],
            "storage_ratio": round(ev["storage_ratio"], 3),
            "folded_dims_mm": ev["folded_dims_mm"],
            "folded_max_dim_mm": ev["folded_max_dim_mm"],
            "max_penetration_mm": round(ev["max_penetration_mm"], 5),
            "worst_pen_pair": ev["worst_pen_pair"],
            "min_clearance_mm": round(ev["min_clearance_mm"], 3),
            "worst_clr_pair": ev["worst_clr_pair"],
            "max_interval_evals": ev["max_interval_evals"],
            "unresolved_pairs": ev["unresolved_pairs"],
            "com_stable": ev["com_stable"],
            "workspace_coverage": round(ev["workspace_coverage"], 3),
            "fea_y_mm": round(fea["tip_y_deflection_mm"], 4),
            "fea_x_mm": round(fea["tip_x_deflection_mm"], 4),
            "fea_z_mm": round(fea["tip_z_deflection_mm"], 4),
            "fea_ideal_y_mm": round(fea_ideal["tip_y_deflection_mm"], 4),
            "fea_dofs": fea["dofs"],
        }
        results.append(row)
        print(
            f"{row['id']:8s} | {row['collision_status']:10s} | stor={row['storage_ratio']:.3f} | "
            f"max_dim={row['folded_max_dim_mm']:6.1f}mm | pen={row['max_penetration_mm']:.4f} | "
            f"clr={row['min_clearance_mm']:.3f} | Y_fea={row['fea_y_mm']:.4f}mm"
        )
    return results


def generate_figures(results: list[dict]) -> None:
    fig_dir = ROOT / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    # Figure 1: Counterexamples A, B, C geometry illustration
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.3), dpi=160)

    # Panel A: 120-deg rotation miss
    ax = axes[0]
    for deg, alpha, lbl in [(0, 0.35, "t=0 (0°)"), (90, 0.85, "t=0.75 (90° 碰撞)"), (120, 0.35, "t=1 (120°)")]:
        r = np.radians(deg)
        xs = [0, 100 * np.cos(r)]
        ys = [0, 100 * np.sin(r)]
        ax.plot(xs, ys, lw=5, alpha=alpha, label=lbl)
    rect = plt.Rectangle((-4, 70), 8, 25, color="#DC2626", alpha=0.65, label="静态障碍物 (90°)")
    ax.add_patch(rect)
    th = np.linspace(0, np.radians(120), 60)
    ax.plot(95 * np.cos(th), 95 * np.sin(th), "k--", lw=1, alpha=0.5)
    ax.set_xlim(-65, 110)
    ax.set_ylim(-15, 110)
    ax.set_aspect("equal")
    ax.set_title("反例 A: 120° 旋转扫掠漏检修复")
    ax.legend(fontsize=7.5, loc="lower left")
    ax.grid(True, alpha=0.25)

    # Panel B: 180-deg + vs - direction
    ax = axes[1]
    th_p = np.linspace(0, np.pi, 60)
    th_m = np.linspace(0, -np.pi, 60)
    ax.plot(65 * np.cos(th_p), 65 * np.sin(th_p), "r-", lw=2.2, label="+180° 轨迹 (FAIL)")
    ax.plot(65 * np.cos(th_m), 65 * np.sin(th_m), "g-", lw=2.2, label="-180° 轨迹 (PASS)")
    ax.add_patch(plt.Rectangle((-4, 50), 8, 20, color="#DC2626", alpha=0.65, label="障碍物 (+90°)"))
    ax.set_xlim(-105, 105)
    ax.set_ylim(-85, 85)
    ax.set_aspect("equal")
    ax.set_title("反例 B: 180° 显式轨迹与 UNRESOLVED")
    ax.legend(fontsize=7.5, loc="lower right")
    ax.grid(True, alpha=0.25)

    # Panel C: Moving vs Moving crossing
    ax = axes[2]
    ax.annotate("", xy=(55, 0), xytext=(-55, 0), arrowprops=dict(arrowstyle="->", color="#2563EB", lw=2.2))
    ax.annotate("", xy=(0, 55), xytext=(0, -55), arrowprops=dict(arrowstyle="->", color="#D97706", lw=2.2))
    ax.scatter([0], [0], color="#DC2626", s=110, zorder=5, label="t=0.5 交叉碰撞 (FAIL)")
    ax.scatter([-55, 55], [0, 0], color="#2563EB", s=45, label="A 起止点")
    ax.scatter([0, 0], [-55, 55], color="#D97706", s=45, label="B 起止点")
    ax.set_xlim(-70, 70)
    ax.set_ylim(-70, 70)
    ax.set_aspect("equal")
    ax.set_title("反例 C: 双运动体交叉碰撞")
    ax.legend(fontsize=7.5, loc="upper right")
    ax.grid(True, alpha=0.25)

    fig.tight_layout()
    fig.savefig(fig_dir / "v3_2_counterexamples.png", dpi=160)
    plt.close(fig)

    # Figure 2: Candidate storage ratio vs FEA Y deflection
    fig, ax = plt.subplots(figsize=(8.2, 4.6), dpi=160)
    colors = {"PASS": "#16A34A", "FAIL": "#DC2626", "UNRESOLVED": "#D97706"}
    for r in results:
        c = colors.get(r["collision_status"], "#475569")
        marker = "o" if r["base_id"] != "F12" else "X"
        ax.scatter(r["storage_ratio"], r["fea_y_mm"], color=c, s=110, marker=marker, edgecolors="k", linewidths=0.7)
        ax.annotate(f"{r['id']}\n({r['collision_status']})", (r["storage_ratio"], r["fea_y_mm"]), xytext=(6, 4), textcoords="offset points", fontsize=8.5)
    ax.axvline(0.80, color="#94A3B8", linestyle="--", lw=1.2, label="收纳比上限 0.80")
    ax.set_xlabel("3D 完整运输收纳体积比 (含 215mm X臂与附件)")
    ax.set_ylabel("10 N 悬臂末端 Y 向挠度 (mm)")
    ax.set_title("V3.2 连续区间碰撞认证与结构刚度最终对比")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="upper left", fontsize=8.5)
    fig.tight_layout()
    fig.savefig(fig_dir / "v3_2_candidate_comparison.png", dpi=160)
    plt.close(fig)


def main() -> None:
    res_dir = ROOT / "results"
    res_dir.mkdir(parents=True, exist_ok=True)
    results = run_candidate_suite()
    generate_figures(results)

    with (res_dir / "v3_2_verification_summary.json").open("w", encoding="utf-8") as f:
        json.dump({"candidates": results}, f, ensure_ascii=False, indent=2)

    fieldnames = [
        "id", "base_id", "role", "collision_status", "passed_screen",
        "storage_ratio", "folded_max_dim_mm", "max_penetration_mm",
        "min_clearance_mm", "com_stable", "workspace_coverage",
        "fea_y_mm", "fea_x_mm", "fea_z_mm", "fea_ideal_y_mm", "fea_dofs",
    ]
    with (res_dir / "v3_2_candidates.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in results:
            w.writerow({k: r[k] for k in fieldnames})

    print("Saved V3.2 JSON, CSV, and PNG figures.")


if __name__ == "__main__":
    main()
