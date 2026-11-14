"""Round 3 complete pipeline: 3D + swept + accessory screening, FEA convergence, SymPy cross-check, NSGA-II, CAD & figures."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
from matplotlib import font_manager
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
import sympy as sp

SIM_V3 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SIM_V3 / "src"))

from foldsim_v3.evaluate3d import evaluate_candidate_3d
from foldsim_v3.fea3d import evaluate_candidate_fea3d
from foldsim_v3.geometry3d import export_obj, export_stl_binary, obb_triangles
from foldsim_v3.mechanisms3d import build_trace_3d, scissor_state
from foldsim_v3.metrics_v3 import repeatability_monte_carlo_v3, structural_metrics_v3
from foldsim_v3.optimize_v3 import optimize_candidate_v3
from foldsim_v3.registry import load_candidates

_cjk = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
if Path(_cjk).exists():
    font_manager.fontManager.addfont(_cjk)
    plt.rcParams["font.sans-serif"] = [font_manager.FontProperties(fname=_cjk).get_name(), "DejaVu Sans"]
else:
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

RESULTS = SIM_V3 / "results"
FIGURES = SIM_V3 / "figures"
CAD = SIM_V3 / "cad"


def render_3d_assembly(obbs, title: str, out_path: Path) -> None:
    fig = plt.figure(figsize=(7.0, 5.2), dpi=160)
    ax = fig.add_subplot(111, projection="3d")
    all_pts = []
    for o in obbs:
        tris = obb_triangles(o)
        all_pts.append(tris.reshape(-1, 3))
        poly = Poly3DCollection(tris, alpha=0.35 if o.group == "extra" else 0.80, edgecolor="#1E293B", linewidth=0.3)
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


def run_independent_crosschecks(candidates: dict) -> dict:
    # 1. SymPy symbolic Jacobian vs numeric scissor_state
    arm, span = sp.symbols("arm span", positive=True, real=True)
    H = sp.sqrt(4 * arm**2 - span**2)
    dH_dS = sp.simplify(sp.diff(H, span))
    num_dH = float(dH_dS.subs({arm: 160.0, span: 180.0}))
    ref = scissor_state(160.0, 180.0)
    sympy_err = abs(num_dH - ref["dH_dS"])

    # 2. FEA mesh convergence across all 5 core candidates (n_sub = 4, 8, 16)
    conv = {}
    for cid in ["F07", "F09", "SCZ", "F12", "F08"]:
        levels = []
        for n in (4, 8, 16):
            r = evaluate_candidate_fea3d(cid, candidates[cid], n_sub=n)
            levels.append({"n_sub": n, "dofs": r["dofs"], "tip_deflection_mm": r["tip_lateral_deflection_mm"]})
        rel_diff_8_16 = abs(levels[2]["tip_deflection_mm"] - levels[1]["tip_deflection_mm"]) / max(levels[2]["tip_deflection_mm"], 1e-9)
        conv[cid] = {"levels": levels, "rel_change_8_to_16": rel_diff_8_16}
    return {"sympy_jacobian_error": sympy_err, "fea_convergence": conv}


def run_f04_expanded_audit(spec: dict) -> dict:
    lifts = np.linspace(60.0, 170.0, 8)
    shifts = np.linspace(-60.0, 120.0, 11)
    grid = []
    feasible_grid = 0
    for lf in lifts:
        for sx in shifts:
            res = evaluate_candidate_3d(spec, parameters={"lift_mm": float(lf), "shift_x_mm": float(sx), "slot_width_mm": 11.0, "dual_roller": 1}, steps=25)
            if res["passed_screen"]:
                feasible_grid += 1
            grid.append({"lift_mm": float(lf), "shift_x_mm": float(sx), "passed": res["passed_screen"], "pen": res["max_penetration_mm"]})
    # Additional 150-point LHS/random search over all 4 F04 bounds
    rng = np.random.default_rng(20261113)
    feasible_rand = 0
    for _ in range(150):
        p = {
            "lift_mm": float(rng.uniform(60.0, 170.0)),
            "shift_x_mm": float(rng.uniform(-60.0, 120.0)),
            "slot_width_mm": float(rng.uniform(8.5, 14.0)),
            "roller_spacing_mm": float(rng.uniform(25.0, 60.0)),
            "dual_roller": 1,
        }
        res = evaluate_candidate_3d(spec, parameters=p, steps=25)
        if res["passed_screen"]:
            feasible_rand += 1
    return {"grid_total": len(grid), "grid_feasible": feasible_grid, "random_total": 150, "random_feasible": feasible_rand, "grid": grid}


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    candidates = load_candidates(SIM_V3 / "config" / "candidates_v3.json")

    # 1. Unified 3D + Swept + Accessory Screening (201 states)
    screening = []
    for cid, spec in candidates.items():
        res = evaluate_candidate_3d(spec, steps=201, swept_check=True)
        clean = {k: v for k, v in res.items() if k not in {"trace", "trace_rows"}}
        screening.append(clean)
        print(f"[Screen V3] {cid:4s}: pass={str(clean['passed_screen']):5s} pen={clean['max_penetration_mm']:5.2f}mm stor={clean['storage_ratio']:.3f} com={clean['com_stable']} {clean['screen_reasons']}")
    (RESULTS / "screening_v3.json").write_text(json.dumps(screening, ensure_ascii=False, indent=2), encoding="utf-8")

    # 2. F12 Layout/Guide Comparison (PTFE+Top Motor vs Preload+Side Motor)
    f12_ptfe = structural_metrics_v3(candidates["F12"], parameters={"motor_side_mounted": 0, "radial_clearance_mm": 0.08, "preload_rail": 0}, steps=51)
    f12_preload = structural_metrics_v3(candidates["F12"], steps=51)
    (RESULTS / "f12_ablation_v3.json").write_text(json.dumps({"ptfe_top_motor": f12_ptfe, "preload_side_motor": f12_preload}, ensure_ascii=False, indent=2), encoding="utf-8")

    # 3. Deep Mechanics + 10,000-sample Uncertainty Monte Carlo
    deep = []
    for idx, (cid, spec) in enumerate(candidates.items()):
        st = structural_metrics_v3(spec, steps=51)
        mc = repeatability_monte_carlo_v3(spec, samples=10000, seed=20261113 + idx)
        deep.append({**st, **mc})
    (RESULTS / "deep_v3.json").write_text(json.dumps(deep, ensure_ascii=False, indent=2), encoding="utf-8")

    # 4. Independent Cross-Checks & FEA Convergence
    crosschecks = run_independent_crosschecks(candidates)
    (RESULTS / "crosschecks_v3.json").write_text(json.dumps(crosschecks, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[CrossCheck] SymPy Jacobian err={crosschecks['sympy_jacobian_error']:.2e}")
    for cid, c in crosschecks["fea_convergence"].items():
        print(f"[FEA Conv]   {cid:4s}: 16-sub defl={c['levels'][-1]['tip_deflection_mm']:.4f}mm, rel_8_16={c['rel_change_8_to_16']:.2%}")

    # 5. F04 Expanded Audit
    f04_audit = run_f04_expanded_audit(candidates["F04"])
    (RESULTS / "f04_audit_v3.json").write_text(json.dumps(f04_audit, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[F04 Audit]  grid={f04_audit['grid_feasible']}/{f04_audit['grid_total']}, rand={f04_audit['random_feasible']}/{f04_audit['random_total']}")

    # 6. NSGA-II Optimization
    opt_results = []
    for idx, (cid, spec) in enumerate(candidates.items()):
        if not spec["bounds"]:
            continue
        opt = optimize_candidate_v3(spec, pop_size=16, generations=10, seed=20261113 + idx)
        opt_results.append(opt)
        print(f"[NSGA-II V3] {cid:4s}: feasible_pareto={len(opt['solutions'])}, min_cv={opt['least_infeasible']['max_constraint_violation']:.4f}")
    (RESULTS / "optimization_v3.json").write_text(json.dumps(opt_results, ensure_ascii=False, indent=2), encoding="utf-8")

    # 7. Weight Perturbation Ranking & 1001-state Verification
    rows = []
    for opt in opt_results:
        cid = opt["id"]
        spec = candidates[cid]
        for s_idx, sol in enumerate(opt["solutions"]):
            m = sol["metrics"]
            rows.append({
                "id": cid, "family": spec["family"], "solution_index": s_idx, "parameters": sol["parameters"],
                "storage": m["storage_ratio"], "error": sol["objectives"][1],
                "deflection": m["elastic_deflection_mm"] + m["clearance_play_mm"],
                "cost": m["estimated_incremental_cost_CNY"], "complexity": spec["complexity"],
                "drive_force": m["peak_drive_force_N"],
            })
    best_by_id = {}
    if rows:
        names = ["storage", "error", "deflection", "cost", "complexity"]
        mat = np.array([[r[k] for k in names] for r in rows], dtype=float)
        mn, mx = mat.min(axis=0), mat.max(axis=0)
        span = np.where(mx - mn > 1e-12, mx - mn, 1.0)
        norm = (mat - mn) / span
        rng = np.random.default_rng(20261113)
        w_sets = rng.uniform([0.20, 0.20, 0.15, 0.08, 0.08], [0.40, 0.45, 0.30, 0.22, 0.22], size=(100, 5))
        w_sets /= w_sets.sum(axis=1, keepdims=True)
        base_w = np.array([0.25, 0.25, 0.20, 0.15, 0.15])
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
            dense = evaluate_candidate_3d(candidates[cid], parameters=r["parameters"], steps=1001, swept_check=True)
            mc20 = repeatability_monte_carlo_v3(candidates[cid], parameters=r["parameters"], samples=20000, seed=20261200 + len(best_by_id))
            st_opt = structural_metrics_v3(candidates[cid], parameters=r["parameters"], steps=51)
            r["dense_1001_passed"] = dense["passed_screen"]
            r["dense_1001_pen_mm"] = dense["max_penetration_mm"]
            r["mc20000_p95_mm"] = mc20["p95_mm"]
            r["print_accuracy_risk"] = mc20["print_accuracy_risk"]
            r["backlash_z_mm"] = st_opt["backlash_z_mm"]
            r["elastic_deflection_mm"] = st_opt["elastic_deflection_mm"]
            r["clearance_play_mm"] = st_opt["clearance_play_mm"]
            best_by_id[cid] = r

    ranking = sorted(best_by_id.values(), key=lambda x: (-x["top3_frequency"], x["baseline_score"]))
    (RESULTS / "selection_v3.json").write_text(json.dumps({"ranking": ranking}, ensure_ascii=False, indent=2), encoding="utf-8")

    # 8. Export Parametric 3D CAD for all 5 core candidates
    for cid in ["F07", "F09", "SCZ", "F12", "F08"]:
        params = best_by_id[cid]["parameters"] if cid in best_by_id else candidates[cid]["parameters"]
        tr = build_trace_3d(candidates[cid], parameters=params, steps=31)
        cdir = CAD / cid
        cdir.mkdir(parents=True, exist_ok=True)
        export_stl_binary(tr[0]["fixed"] + tr[0]["moving"], cdir / f"{cid.lower()}_work.stl", f"{cid} work")
        export_stl_binary(tr[-1]["fixed"] + tr[-1]["moving"] + tr[-1]["extra"], cdir / f"{cid.lower()}_folded.stl", f"{cid} folded")
        export_obj(tr[-1]["fixed"] + tr[-1]["moving"] + tr[-1]["extra"], cdir / f"{cid.lower()}_folded.obj")
        render_3d_assembly(tr[-1]["fixed"] + tr[-1]["moving"] + tr[-1]["extra"], f"{cid} 第三轮终审折叠态 (含附件 3D CAD)", cdir / f"{cid.lower()}_folded_3d.png")

    # 9. Summary Figures
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.5, 4.8), dpi=180)
    core = ["F07", "F09", "SCZ", "F12", "F08"]
    deep_map = {d["id"]: d for d in deep}
    xc = np.arange(len(core))
    ax1.bar(xc - 0.18, [deep_map[c]["storage_ratio"] for c in core], width=0.36, color="#2563EB", label="名义 3D 收纳比 (含附件)")
    opt_stor = [best_by_id[c]["storage"] if c in best_by_id else deep_map[c]["storage_ratio"] for c in core]
    ax1.bar(xc + 0.18, opt_stor, width=0.36, color="#10B981", label="优化后 3D 收纳比")
    ax1.axhline(0.80, color="#DC2626", linestyle="--", label="收纳阈值 0.80")
    ax1.set_xticks(xc, core)
    ax1.set_ylabel("系统收纳体积比")
    ax1.set_title("核心五套｜统一附件包络 3D 收纳比")
    ax1.legend(fontsize=8)
    ax1.grid(axis="y", alpha=0.25)

    ax2.bar(xc - 0.18, [deep_map[c]["elastic_deflection_mm"] for c in core], width=0.36, color="#0284C7", label="3D 空间梁架 FEA 弹性挠度 (mm)")
    ax2.bar(xc + 0.18, [deep_map[c]["p95_mm"] for c in core], width=0.36, color="#F59E0B", label="公差蒙特卡洛 P95 (mm)")
    ax2.set_xticks(xc, core)
    ax2.set_ylabel("mm")
    ax2.set_title("核心五套｜同口径 3D FEA 挠度 vs 定位误差 P95")
    ax2.legend(fontsize=8)
    ax2.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIGURES / "r3_core_comparison.png", dpi=180, facecolor="white")
    plt.close(fig)

    print("ROUND 3 SIMULATION COMPLETED.")


if __name__ == "__main__":
    main()
