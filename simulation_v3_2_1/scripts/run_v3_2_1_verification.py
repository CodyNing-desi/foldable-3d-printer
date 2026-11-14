"""V3.2.1 Certified Continuous Collision Re-Verification, F09 Consistency Audit, and Reporting."""

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
WORKSPACE_ROOT = ROOT.parent
sys.path.insert(0, str(ROOT / "src"))

from foldsim_v3_2_1.evaluate3d import evaluate_candidate_3d
from foldsim_v3_2_1.fea3d import evaluate_candidate_fea3d
from foldsim_v3_2_1.geometry3d import LipschitzTrajectory, OBB, StaticTrajectory, verify_interval_collision
from foldsim_v3_2_1.registry import load_candidates

plt.rcParams["font.sans-serif"] = ["Noto Sans CJK SC", "Noto Sans CJK JP", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def check_before_after_sinusoid() -> dict:
    """Compare V3.2 broken bound vs V3.2.1 certified bound on x(t)=50*sin(2*pi*t)."""
    v32_src = WORKSPACE_ROOT / "simulation_v3_2" / "src"
    before_res = None
    if v32_src.exists():
        sys.path.insert(0, str(v32_src))
        from foldsim_v3_2.geometry3d import OBB as OBB32, verify_interval_collision as verify32
        m32 = OBB32.from_bounds("moving", -1, -1, -1, 1, 1, 1)
        o32 = OBB32.from_bounds("obstacle", 49, -1, -1, 51, 1, 1)
        before_res = verify32(
            lambda t: m32.transformed(translation=np.array([50.0 * np.sin(2.0 * np.pi * t), 0.0, 0.0])),
            lambda t: o32,
            t0=0.0, t1=1.0,
        )
        sys.path.pop(0)

    m = OBB.from_bounds("moving", -1, -1, -1, 1, 1, 1)
    o = OBB.from_bounds("obstacle", 49, -1, -1, 51, 1, 1)
    traj = LipschitzTrajectory(
        pose_fn=lambda t: m.transformed(translation=np.array([50.0 * np.sin(2.0 * np.pi * t), 0.0, 0.0])),
        v_center_max=50.0 * 2.0 * np.pi,
        omega_max_rad=0.0,
        r_obb=m.bounding_radius,
        label="Sin(2*pi*t) A=50",
    )
    after_res = verify_interval_collision(traj, StaticTrajectory(o), t0=0.0, t1=1.0)
    uncertified_res = verify_interval_collision(
        lambda t: m.transformed(translation=np.array([50.0 * np.sin(2.0 * np.pi * t), 0.0, 0.0])),
        lambda t: o,
        t0=0.0, t1=1.0,
    )
    return {
        "v3_2_before_fix": before_res,
        "v3_2_1_certified": after_res,
        "v3_2_1_uncertified_callable": uncertified_res,
    }


def run_candidate_suite() -> list[dict]:
    cands = load_candidates(ROOT / "config" / "candidates_v3_2_1.json")
    targets = [
        ("F09_L85", "F09", {"lift_mm": 85.0, "shift_x_mm": 0.0, "arm_fold_enabled": 1}, "未通过整体筛选 (0.802 > 0.800)", "仅作原参数基线对照"),
        ("F09_L82", "F09", {"lift_mm": 82.0, "shift_x_mm": 0.0, "arm_fold_enabled": 1}, "主候选 1 (Conditional Go: 折叠X臂锁紧与0.061mm公差待台架实测)", "几何微调 lift=82mm 后达标 <=0.800"),
        ("F07", "F07", {"lift_mm": 75.0, "shift_x_mm": 0.0, "arm_fold_enabled": 1}, "主候选 2 (Conditional Go: 0.053mm净距与Y向0.8166mm挠度待实测)", "单柱结构刚度偏低且导杆间隙极小"),
        ("SCZ", "SCZ", {"arm_length_mm": 154.0, "height_fold_mm": 45.0, "height_work_max_mm": 270.0}, "主候选 3 (Bench-only 台架机构验证: 仅验证推力与回差)", "剪刀臂交叉净距仅0.006mm，不作整机主力"),
        ("F08_L25", "F08", {"lift_mm": 25.0, "shift_x_mm": -75.0, "arm_fold_enabled": 1}, "工程兜底备选 (Fallback: 体积比最优但最长边897mm)", "折叠后最长边超便携箱包限制"),
        ("F08_L30", "F08", {"lift_mm": 30.0, "shift_x_mm": -75.0, "arm_fold_enabled": 1}, "工程兜底备选对照 (+5mm底座净空)", "折叠后最长边仍为897mm"),
        ("F12", "F12", {"overlap_mm": 52.0, "outer_size_mm": 60.0, "preload_rail": 1, "motor_side_mounted": 1}, "淘汰归档 (No-Go)", "6周内精密多级伸缩导轨晃动与卡滞风险不可控"),
    ]

    results = []
    for label_id, cid, params, qualification, risk_note in targets:
        spec = cands[cid]
        ev = evaluate_candidate_3d(spec, parameters=params, steps=31, max_depth=14)
        fea = evaluate_candidate_fea3d(cid, spec, parameters=params, n_sub=8 if cid == "SCZ" else 32, ideal_rigid_joints=False)
        fea_ideal = evaluate_candidate_fea3d(cid, spec, parameters=params, n_sub=8 if cid == "SCZ" else 32, ideal_rigid_joints=True)
        row = {
            "id": label_id,
            "base_id": cid,
            "collision_status": ev["collision_status"],
            "passed_screen": ev["passed_screen"],
            "screen_reasons": ev["screen_reasons"],
            "storage_ratio": round(ev["storage_ratio"], 3),
            "folded_dims_mm": ev["folded_dims_mm"],
            "folded_max_dim_mm": ev["folded_max_dim_mm"],
            "max_penetration_mm": round(ev["max_penetration_mm"], 5),
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
            "risk_note": risk_note,
            "qualification": qualification,
        }
        results.append(row)
        print(
            f"{row['id']:8s} | col={row['collision_status']:4s} | screen={str(row['passed_screen']):5s} | "
            f"stor={row['storage_ratio']:.3f} | max_dim={row['folded_max_dim_mm']:6.1f} | "
            f"clr={row['min_clearance_mm']:.3f}mm | Y_fea={row['fea_y_mm']:.4f}mm"
        )
    return results


def generate_figure(results: list[dict]) -> None:
    fig_dir = ROOT / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8.6, 4.8), dpi=160)
    for r in results:
        c = "#16A34A" if r["passed_screen"] else "#DC2626"
        if r["base_id"] == "F12":
            c = "#64748B"
        ax.scatter(r["storage_ratio"], r["fea_y_mm"], color=c, s=110, edgecolors="k", linewidths=0.7)
        ax.annotate(f"{r['id']}\n(screen={'PASS' if r['passed_screen'] else 'FAIL'})", (r["storage_ratio"], r["fea_y_mm"]), xytext=(6, 4), textcoords="offset points", fontsize=8)
    ax.axvline(0.80, color="#DC2626", linestyle="--", lw=1.2, label="收纳比门槛 <= 0.800")
    ax.set_xlabel("3D 完整运输收纳体积比 (含 215mm X臂与附件)")
    ax.set_ylabel("10 N 悬臂末端 Y 向挠度 (mm)")
    ax.set_title("V3.2.1 严格连续碰撞认证与整体筛选一致性对比")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="upper left", fontsize=8.5)
    fig.tight_layout()
    fig.savefig(fig_dir / "v3_2_1_screening_consistency.png", dpi=160)
    plt.close(fig)


def main() -> None:
    res_dir = ROOT / "results"
    res_dir.mkdir(parents=True, exist_ok=True)
    ba = check_before_after_sinusoid()
    results = run_candidate_suite()
    generate_figure(results)

    with (res_dir / "v3_2_1_verification_summary.json").open("w", encoding="utf-8") as f:
        json.dump({"sinusoid_before_after": ba, "candidates": results}, f, ensure_ascii=False, indent=2)

    fieldnames = [
        "id", "base_id", "collision_status", "passed_screen", "storage_ratio",
        "folded_max_dim_mm", "max_penetration_mm", "min_clearance_mm",
        "fea_y_mm", "fea_x_mm", "fea_z_mm", "risk_note", "qualification",
    ]
    with (res_dir / "v3_2_1_candidates.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in results:
            w.writerow({k: r[k] for k in fieldnames})
    print("Saved V3.2.1 verification JSON, CSV, and PNG.")


if __name__ == "__main__":
    main()
