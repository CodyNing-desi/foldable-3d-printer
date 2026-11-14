"""End-to-end Round 2 high-fidelity 3D simulation, CAD export, FEA, optimization, and figures."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np

SIM_V2 = Path(__file__).resolve().parents[1]
ROOT = SIM_V2.parent
sys.path.insert(0, str(SIM_V2 / "src"))

from foldsim_v2.evaluate3d import evaluate_candidate_3d
from foldsim_v2.fea3d import evaluate_candidate_fea3d
from foldsim_v2.geometry3d import export_obj, export_stl_binary, obb_triangles
from foldsim_v2.mechanisms3d import build_trace_3d
from foldsim_v2.metrics_v2 import repeatability_monte_carlo_v2, scz_scissor_mechanics, structural_metrics_v2
from foldsim_v2.optimize_v2 import optimize_candidate_v2
from foldsim_v2.registry import load_candidates

from matplotlib import font_manager
_cjk = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
if Path(_cjk).exists():
    font_manager.fontManager.addfont(_cjk)
    plt.rcParams["font.sans-serif"] = [font_manager.FontProperties(fname=_cjk).get_name(), "DejaVu Sans"]
else:
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

RESULTS = SIM_V2 / "results"
FIGURES = SIM_V2 / "figures"
CAD = SIM_V2 / "cad"


def render_3d_assembly(obbs, title: str, out_path: Path) -> None:
    fig = plt.figure(figsize=(7.2, 5.4), dpi=160)
    ax = fig.add_subplot(111, projection="3d")
    all_pts = []
    for o in obbs:
        tris = obb_triangles(o)
        all_pts.append(tris.reshape(-1, 3))
        poly = Poly3DCollection(tris, alpha=0.35 if o.group == "extra" else 0.78, edgecolor="#1E293B", linewidth=0.3)
        poly.set_facecolor(o.color)
        ax.add_collection3d(poly)
    pts = np.vstack(all_pts)
    mn, mx = np.min(pts, axis=0), np.max(pts, axis=0)
    ctr = 0.5 * (mn + mx)
    span = 0.55 * float(np.max(mx - mn))
    ax.set_xlim(ctr[0] - span, ctr[0] + span)
    ax.set_ylim(ctr[1] - span, ctr[1] + span)
    ax.set_zlim(ctr[2] - span, ctr[2] + span)
    ax.set_xlabel("X (mm)")
    ax.set_ylabel("Y (mm)")
    ax.set_zlabel("Z (mm)")
    ax.set_title(title, fontsize=10)
    ax.view_init(elev=22, azim=-48)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=160, facecolor="white")
    plt.close(fig)


def run_f04_audit(spec: dict) -> dict:
    """Test F04 across (lift, shift_x) grid to separate parameter failure from family infeasibility."""
    lifts = [40.0, 70.0, 100.0, 130.0, 160.0]
    shifts = [-60.0, -30.0, 0.0, 20.0, 45.0, 70.0, 100.0]
    grid = []
    feasible_count = 0
    for lf in lifts:
        for sx in shifts:
            res = evaluate_candidate_3d(spec, parameters={"lift_mm": lf, "shift_x_mm": sx, "slot_width_mm": 11.0, "dual_roller": 1}, steps=31)
            if res["passed_screen"]:
                feasible_count += 1
            grid.append({
                "lift_mm": lf,
                "shift_x_mm": sx,
                "passed": res["passed_screen"],
                "max_penetration_mm": res["max_penetration_mm"],
                "storage_ratio": res["storage_ratio"],
                "max_pressure_angle_deg": res["max_pressure_angle_deg"],
                "worst_pair": res["worst_collision_pair"],
            })
    single_roller = evaluate_candidate_3d(spec, parameters={"lift_mm": 100.0, "shift_x_mm": 0.0, "dual_roller": 0}, steps=21)
    return {
        "grid_count": len(grid),
        "feasible_count": feasible_count,
        "single_roller_dof": single_roller["dof"],
        "single_roller_reasons": single_roller["screen_reasons"],
        "grid": grid,
    }


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    candidates = load_candidates(SIM_V2 / "config" / "candidates_v2.json")

    # 1. 3D Screening (201 states)
    screening = []
    for cid, spec in candidates.items():
        res = evaluate_candidate_3d(spec, steps=201)
        res_clean = {k: v for k, v in res.items() if k not in {"trace", "trace_rows"}}
        screening.append(res_clean)
        print(f"[Screen 3D] {cid:4s}: pass={res_clean['passed_screen']} pen={res_clean['max_penetration_mm']:.2f}mm stor={res_clean['storage_ratio']:.3f} {res_clean['screen_reasons']}")
    (RESULTS / "screening_v2.json").write_text(json.dumps(screening, ensure_ascii=False, indent=2), encoding="utf-8")

    # 2. Deep Mechanics + 10,000-sample Tolerance/Material Monte Carlo
    deep = []
    for idx, (cid, spec) in enumerate(candidates.items()):
        st = structural_metrics_v2(spec, steps=51)
        mc = repeatability_monte_carlo_v2(spec, samples=10000, seed=20261113 + idx)
        row = {**st, **mc}
        deep.append(row)
        print(f"[Deep 3D]   {cid:4s}: defl={row['tip_deflection_mm']:.3f}mm P95={row['p95_mm']:.3f}mm F_drive={row['peak_drive_force_N']:.1f}N")
    (RESULTS / "deep_v2.json").write_text(json.dumps(deep, ensure_ascii=False, indent=2), encoding="utf-8")

    # 3. 3D Space-Frame FEA on core candidates
    fea_results = {}
    for cid in ["F07", "F12", "SCZ", "F08"]:
        fea_results[cid] = evaluate_candidate_fea3d(cid, candidates[cid], n_sub=12)
    (RESULTS / "fea3d_v2.json").write_text(json.dumps(fea_results, ensure_ascii=False, indent=2), encoding="utf-8")

    # 4. F04 Family Feasibility Audit
    f04_audit = run_f04_audit(candidates["F04"])
    (RESULTS / "f04_family_audit.json").write_text(json.dumps(f04_audit, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[F04 Audit] feasible={f04_audit['feasible_count']}/{f04_audit['grid_count']}, single_roller_dof={f04_audit['single_roller_dof']}")

    # 5. NSGA-II Optimization on variable candidates
    opt_results = []
    for idx, (cid, spec) in enumerate(candidates.items()):
        if not spec["bounds"]:
            continue
        opt = optimize_candidate_v2(spec, pop_size=20, generations=12, seed=20261113 + idx)
        opt_results.append(opt)
        print(f"[NSGA-II]   {cid:4s}: feasible_pareto={len(opt['solutions'])}, min_cv={opt['least_infeasible']['max_constraint_violation']:.4f}")
    (RESULTS / "optimization_v2.json").write_text(json.dumps(opt_results, ensure_ascii=False, indent=2), encoding="utf-8")

    # 6. Weight Perturbation Ranking across all feasible optimized solutions
    rows = []
    for opt in opt_results:
        cid = opt["id"]
        spec = candidates[cid]
        for s_idx, sol in enumerate(opt["solutions"]):
            m = sol["metrics"]
            rows.append({
                "id": cid,
                "family": spec["family"],
                "solution_index": s_idx,
                "parameters": sol["parameters"],
                "storage": m["storage_ratio"],
                "error": sol["objectives"][1],
                "deflection": m["tip_deflection_mm"],
                "reliability": -m["reliability_proxy_score"],
                "cost": m["estimated_incremental_cost_CNY"],
                "complexity": m["manufacturing_complexity_score"],
                "peak_drive_force_N": m["peak_drive_force_N"],
            })
    best_by_id = {}
    if rows:
        names = ["storage", "error", "deflection", "reliability", "cost", "complexity"]
        mat = np.array([[r[k] for k in names] for r in rows], dtype=float)
        mn, mx = mat.min(axis=0), mat.max(axis=0)
        span = np.where(mx - mn > 1e-12, mx - mn, 1.0)
        norm = (mat - mn) / span
        rng = np.random.default_rng(20261113)
        w_sets = rng.uniform([0.15, 0.20, 0.08, 0.08, 0.05, 0.05], [0.35, 0.50, 0.25, 0.25, 0.20, 0.20], size=(100, 6))
        w_sets /= w_sets.sum(axis=1, keepdims=True)
        base_w = np.array([0.25, 0.25, 0.15, 0.15, 0.10, 0.10])
        ids = sorted({r["id"] for r in rows})
        top3_freq = {cid: 0 for cid in ids}
        for w in w_sets:
            sc = norm @ w
            best_c = {}
            for i, r in enumerate(rows):
                if r["id"] not in best_c or sc[i] < sc[best_c[r["id"]]]:
                    best_c[r["id"]] = i
            rank = sorted(best_c, key=lambda c: sc[best_c[c]])
            for c in rank[:3]:
                top3_freq[c] += 1
        base_sc = norm @ base_w
        for cid in ids:
            idxs = [i for i, r in enumerate(rows) if r["id"] == cid]
            bi = min(idxs, key=lambda i: base_sc[i])
            r = dict(rows[bi])
            r["baseline_score"] = float(base_sc[bi])
            r["top3_frequency"] = top3_freq[cid] / len(w_sets)
            # Re-verify at 1001 states + 20,000 MC
            dense = evaluate_candidate_3d(candidates[cid], parameters=r["parameters"], steps=1001)
            mc20 = repeatability_monte_carlo_v2(candidates[cid], parameters=r["parameters"], samples=20000, seed=20261200 + len(best_by_id))
            r["dense_1001_passed"] = dense["passed_screen"]
            r["dense_1001_pen_mm"] = dense["max_penetration_mm"]
            r["mc20000_p95_mm"] = mc20["p95_mm"]
            best_by_id[cid] = r

    ranking = sorted(best_by_id.values(), key=lambda x: (-x["top3_frequency"], x["baseline_score"]))
    selection_v2 = {"ranking": ranking, "feasible_candidate_ids": [r["id"] for r in ranking]}
    (RESULTS / "selection_v2.json").write_text(json.dumps(selection_v2, ensure_ascii=False, indent=2), encoding="utf-8")

    # 7. Export Parametric 3D CAD (STL + OBJ + 3D views) for F07, F12, SCZ, F08
    cad_manifest = {}
    for cid in ["F07", "F12", "SCZ", "F08"]:
        params = best_by_id[cid]["parameters"] if cid in best_by_id else candidates[cid]["parameters"]
        tr = build_trace_3d(candidates[cid], parameters=params, steps=31)
        cdir = CAD / cid
        cdir.mkdir(parents=True, exist_ok=True)
        work_obbs = tr[0]["fixed"] + tr[0]["moving"]
        fold_obbs = tr[-1]["fixed"] + tr[-1]["moving"] + tr[-1]["extra"]
        stl_w = export_stl_binary(work_obbs, cdir / f"{cid.lower()}_work.stl", f"{cid} work state")
        stl_f = export_stl_binary(fold_obbs, cdir / f"{cid.lower()}_folded.stl", f"{cid} folded state")
        obj_f = export_obj(fold_obbs, cdir / f"{cid.lower()}_folded.obj")
        render_3d_assembly(work_obbs, f"{cid} 工作展开态 (3D CAD)", cdir / f"{cid.lower()}_work_3d.png")
        render_3d_assembly(fold_obbs, f"{cid} 折叠收纳态 (3D CAD)", cdir / f"{cid.lower()}_folded_3d.png")
        cad_manifest[cid] = {"parameters": params, "work_stl": stl_w, "folded_stl": stl_f, "folded_obj": obj_f}
    (RESULTS / "cad_manifest_v2.json").write_text(json.dumps(cad_manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    # 8. Comparison Round 1 vs Round 2
    r1_screen = {r["id"]: r for r in json.loads((ROOT / "downloads" / "screening_summary.json").read_text(encoding="utf-8"))}
    r1_deep = {r["id"]: r for r in json.loads((ROOT / "downloads" / "deep_summary.json").read_text(encoding="utf-8"))}
    r2_screen = {r["id"]: r for r in screening}
    r2_deep = {r["id"]: r for r in deep}
    comp = []
    for cid in candidates:
        comp.append({
            "id": cid,
            "name": candidates[cid]["name"],
            "r1_pass": r1_screen[cid]["passed_screen"],
            "r2_pass": r2_screen[cid]["passed_screen"],
            "r1_storage": r1_screen[cid]["storage_ratio"],
            "r2_storage": r2_screen[cid]["storage_ratio"],
            "r1_defl_mm": r1_deep[cid]["tip_deflection_mm"],
            "r2_defl_mm": r2_deep[cid]["tip_deflection_mm"],
            "r1_p95_mm": r1_deep[cid]["p95_mm"],
            "r2_p95_mm": r2_deep[cid]["p95_mm"],
            "r2_reasons": r2_screen[cid]["screen_reasons"],
        })
    (RESULTS / "comparison_r1_vs_r2.json").write_text(json.dumps(comp, ensure_ascii=False, indent=2), encoding="utf-8")

    # 9. Generate High-Resolution Charts
    # Chart 1: Round 1 vs Round 2 Storage Ratio & Deflection
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.2), dpi=180)
    cids = [c["id"] for c in comp]
    x = np.arange(len(cids))
    ax1.bar(x - 0.18, [c["r1_storage"] for c in comp], width=0.36, color="#94A3B8", label="第一轮 (2.5D)")
    ax1.bar(x + 0.18, [c["r2_storage"] for c in comp], width=0.36, color="#2563EB", label="第二轮 (3D 实包络)")
    ax1.axhline(0.80, color="#DC2626", linestyle="--", linewidth=1.2, label="收纳阈值 0.80")
    ax1.set_xticks(x, cids, rotation=45)
    ax1.set_ylabel("系统收纳体积比")
    ax1.set_title("第一轮 vs 第二轮｜3D 系统收纳体积比对比")
    ax1.legend(fontsize=8)
    ax1.grid(axis="y", alpha=0.25)

    core_ids = ["F07", "F12", "SCZ", "F08"]
    xc = np.arange(len(core_ids))
    ax2.bar(xc - 0.18, [r1_deep[c]["tip_deflection_mm"] for c in core_ids], width=0.36, color="#94A3B8", label="第一轮 (1D 简化梁)")
    ax2.bar(xc + 0.18, [r2_deep[c]["tip_deflection_mm"] for c in core_ids], width=0.36, color="#0284C7", label="第二轮 (3D 空间梁架 FEA+间隙)")
    ax2.set_xticks(xc, core_ids)
    ax2.set_ylabel("10 N 侧载末端挠度 (mm)")
    ax2.set_title("核心候选｜一二轮刚度/挠度对比")
    ax2.legend(fontsize=8)
    ax2.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIGURES / "r1_vs_r2_comparison.png", dpi=180, facecolor="white")
    plt.close(fig)

    # Chart 2: SCZ Nonlinear Mechanics vs Working Height
    hs = np.linspace(50.0, 305.0, 60)
    scz_spec = candidates["SCZ"]
    forces, backlashes, bucklings = [], [], []
    for h in hs:
        p_mod = dict(scz_spec["parameters"], height_fold_mm=h, height_work_max_mm=h + 180.0)
        # Evaluate at height h directly via arm_length=160
        span = np.sqrt(max(1.0, 4 * 160.0**2 - h**2))
        gain = span / h
        W = scz_spec["mass_kg"] * 9.81
        theta = np.arctan2(h, span)
        f_pin = 4 * 0.12 * (4.0 / 160.0) * W / max(np.sin(theta), 0.1)
        forces.append((W * gain + f_pin + 0.08 * W) / 0.55)
        backlashes.append(gain * 0.04 + 2 * 0.06 / max(np.sin(theta), 0.1))
        P_cr = (np.pi**2 * 69000.0 * (20.0 * 6.0**3 / 12.0)) / (160.0**2)
        bucklings.append(P_cr / (0.25 * W / max(np.sin(theta), 0.1)))
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.8), dpi=180)
    ax1.plot(hs, forces, color="#DC2626", linewidth=2, label="水平丝杆驱动力 (N)")
    ax1.axhline(350.0, color="#64748B", linestyle="--", label="NEMA17+T8 推力上限参考 350 N")
    ax1.set_xlabel("剪刀机构当前高度 H (mm)")
    ax1.set_ylabel("驱动力 (N)")
    ax1.set_title("SCZ 低位非线性驱动力剧增曲线")
    ax1.legend(fontsize=8)
    ax1.grid(alpha=0.25)

    ax2.plot(hs, backlashes, color="#D97706", linewidth=2, label="Z 向回差放大 (mm)")
    ax2.set_xlabel("剪刀机构当前高度 H (mm)")
    ax2.set_ylabel("Z 向回差 (mm)", color="#D97706")
    ax2b = ax2.twinx()
    ax2b.plot(hs, bucklings, color="#059669", linewidth=2, linestyle="-.", label="欧拉屈曲安全系数")
    ax2b.set_ylabel("屈曲安全系数", color="#059669")
    ax2.set_title("SCZ 回差放大与压杆屈曲安全系数")
    ax2.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIGURES / "scz_nonlinear_mechanics.png", dpi=180, facecolor="white")
    plt.close(fig)

    # Chart 3: F04 Family Feasibility Map
    lifts = sorted({g["lift_mm"] for g in f04_audit["grid"]})
    shifts = sorted({g["shift_x_mm"] for g in f04_audit["grid"]})
    pen_mat = np.zeros((len(lifts), len(shifts)))
    for g in f04_audit["grid"]:
        pen_mat[lifts.index(g["lift_mm"]), shifts.index(g["shift_x_mm"])] = g["max_penetration_mm"]
    fig, ax = plt.subplots(figsize=(8.5, 4.8), dpi=180)
    im = ax.imshow(pen_mat, origin="lower", cmap="YlOrRd", aspect="auto")
    ax.set_xticks(np.arange(len(shifts)), [f"{s:.0f}" for s in shifts])
    ax.set_yticks(np.arange(len(lifts)), [f"{l:.0f}" for l in lifts])
    ax.set_xlabel("水平平移 shift_x_mm")
    ax.set_ylabel("抬升行程 lift_mm")
    ax.set_title(f"F04 槽轨全参数域 3D 干涉热力图 (可行解 {f04_audit['feasible_count']}/{f04_audit['grid_count']})")
    for i in range(len(lifts)):
        for j in range(len(shifts)):
            ax.text(j, i, f"{pen_mat[i, j]:.0f}", ha="center", va="center", color="black", fontsize=8)
    fig.colorbar(im, ax=ax, label="最大 3D 穿透深度 (mm)")
    fig.tight_layout()
    fig.savefig(FIGURES / "f04_family_feasibility_map.png", dpi=180, facecolor="white")
    plt.close(fig)

    print("ALL ROUND 2 SIMULATIONS, CAD, AND FIGURES COMPLETED.")


if __name__ == "__main__":
    main()
