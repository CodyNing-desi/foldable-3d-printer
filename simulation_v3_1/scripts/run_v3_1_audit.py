"""V3.1 complete targeted verification: F09 215mm FEA, F07/F08/SCZ swept clearance, SCZ sensitivity, F12 check."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
from matplotlib import font_manager
import matplotlib.pyplot as plt
import numpy as np
import sympy as sp

SIM_V31 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SIM_V31 / "src"))

from foldsim_v3_1.evaluate3d import evaluate_candidate_3d
from foldsim_v3_1.fea3d import evaluate_candidate_fea3d, hollow_square_props
from foldsim_v3_1.mechanisms3d import scissor_state
from foldsim_v3_1.registry import load_candidates

_cjk = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
if Path(_cjk).exists():
    font_manager.fontManager.addfont(_cjk)
    plt.rcParams["font.sans-serif"] = [font_manager.FontProperties(fname=_cjk).get_name(), "DejaVu Sans"]
else:
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

RESULTS = SIM_V31 / "results"
FIGURES = SIM_V31 / "figures"


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    cands = load_candidates(SIM_V31 / "config" / "candidates_v3_1.json")

    # 1. Unified 3D FEA (F07, F09, F08, F12, SCZ) + Ideal Rigid vs Finite Compliance + Mesh Convergence
    fea_summary = {}
    for cid in ["F07", "F09", "F08", "F12"]:
        conv_comp = [evaluate_candidate_fea3d(cid, cands[cid], n_sub=n, ideal_rigid_joints=False) for n in (4, 8, 16, 32)]
        ideal = evaluate_candidate_fea3d(cid, cands[cid], n_sub=16, ideal_rigid_joints=True)
        finest = conv_comp[-1]
        prev = conv_comp[-2]
        rel_16_32 = abs(finest["tip_y_deflection_mm"] - prev["tip_y_deflection_mm"]) / max(finest["tip_y_deflection_mm"], 1e-9)
        fea_summary[cid] = {
            "convergence": conv_comp,
            "ideal_rigid_16": ideal,
            "finest_32": finest,
            "rel_change_16_to_32": rel_16_32,
        }
        print(f"[FEA V3.1] {cid:4s}: 32-sub Y={finest['tip_y_deflection_mm']:.4f}mm X={finest['tip_x_deflection_mm']:.4f}mm Z={finest['tip_z_deflection_mm']:.4f}mm (ideal Y={ideal['tip_y_deflection_mm']:.4f}mm) DOFs={finest['dofs']} conv={rel_16_32:.3%}")

    scz_conv = [evaluate_candidate_fea3d("SCZ", cands["SCZ"], n_sub=n) for n in (1, 2, 4, 8)]
    rel_scz = abs(scz_conv[-1]["tip_y_deflection_mm"] - scz_conv[-2]["tip_y_deflection_mm"]) / max(scz_conv[-1]["tip_y_deflection_mm"], 1e-9)
    fea_summary["SCZ"] = {"convergence": scz_conv, "finest_8": scz_conv[-1], "rel_change_4_to_8": rel_scz}
    print(f"[FEA V3.1] SCZ : 8-sub Y={scz_conv[-1]['tip_y_deflection_mm']:.4f}mm DOFs={[r['dofs'] for r in scz_conv]} conv={rel_scz:.3%}")

    # Analytical Euler-Bernoulli cross-check for F07 pure column bending
    E, I_y, L_arm, L_col = 69000.0, 7000.0, 215.0, 275.0
    eb_col_only = 10.0 * (L_col**3) / (3.0 * E * I_y)
    # SymPy SCZ Jacobian cross-check
    arm_s, span_s = sp.symbols("arm span", positive=True, real=True)
    dH = sp.diff(sp.sqrt(4 * arm_s**2 - span_s**2), span_s)
    sympy_err = abs(float(dH.subs({arm_s: 160.0, span_s: 180.0})) - scissor_state(160.0, 180.0)["dH_dS"])
    fea_summary["analytical_crosschecks"] = {"eb_column_only_y_mm": eb_col_only, "sympy_scz_jacobian_err": sympy_err}
    (RESULTS / "fea_v3_1.json").write_text(json.dumps(fea_summary, ensure_ascii=False, indent=2), encoding="utf-8")

    # 2. Conservative Adaptive Swept Collision & Minimum Clearance (201 states, step_bound=1.0 mm)
    swept_tests = [
        ("F07_nom", "F07", {"lift_mm": 95.0, "shift_x_mm": 0.0}),
        ("F07_opt_safe", "F07", {"lift_mm": 80.0, "shift_x_mm": 0.0}),
        ("F07_lift75", "F07", {"lift_mm": 75.0, "shift_x_mm": 0.0}),
        ("F07_shift10", "F07", {"lift_mm": 80.0, "shift_x_mm": 10.0}),
        ("F09_opt", "F09", {"lift_mm": 85.0, "shift_x_mm": 0.0}),
        ("SCZ_opt", "SCZ", {"arm_length_mm": 154.0, "height_fold_mm": 45.0}),
        ("F08_opt", "F08", {"lift_mm": 25.0, "shift_x_mm": -75.0}),
        ("F08_safe30", "F08", {"lift_mm": 30.0, "shift_x_mm": -75.0}),
        ("F12_preload", "F12", {"overlap_mm": 52.0, "outer_size_mm": 60.0}),
    ]
    swept_out = []
    for label, cid, params in swept_tests:
        res = evaluate_candidate_3d(cands[cid], parameters=params, steps=201, swept_check=True, step_bound_mm=1.0)
        res["label"] = label
        swept_out.append(res)
        print(f"[Swept V3.1] {label:12s} | pass={str(res['passed_screen']):5s} | pen={res['max_penetration_mm']:.4f}mm | min_clr={res['min_clearance_mm']:.2f}mm (@t={res['worst_clr_t']:.2f} {res['worst_clr_pair']}) | stor={res['storage_ratio']:.3f} | substeps={res['max_swept_substeps']}")
    (RESULTS / "swept_v3_1.json").write_text(json.dumps(swept_out, ensure_ascii=False, indent=2), encoding="utf-8")

    # 3. SCZ Deep Thrust, Motor Torque, & Backlash Sensitivity Analysis
    scz = cands["SCZ"]
    W = scz["mass_kg"] * 9.81
    arm_len = 154.0
    scz_cases = []
    for label, h_mm in [("H_work_min_125", 125.0), ("H_fold_45", 45.0)]:
        span = math.sqrt(4.0 * arm_len**2 - h_mm**2)
        theta = math.atan2(h_mm, span)
        gain = span / h_mm
        for screw_name, lead_mm, eta, s_bl in [("T8_lead2_trapezoid", 2.0, 0.55, 0.04), ("SFU1204_preload_ball", 4.0, 0.85, 0.01)]:
            for pin_clr, mu_pin in [(0.06, 0.12), (0.015, 0.06)]:
                pin_f = 4.0 * mu_pin * (4.0 / arm_len) * W / max(math.sin(theta), 0.1)
                F_req = (W * gain + pin_f + 0.08 * W) / eta
                # Motor torque T = F * lead / (2 * pi)
                T_req_Nm = (F_req * (lead_mm / 1000.0)) / (2.0 * math.pi)
                bl_z = gain * s_bl + 2.0 * pin_clr / max(math.sin(theta), 0.1)
                scz_cases.append({
                    "height_case": label, "H_mm": h_mm, "screw": screw_name,
                    "pin_clearance_mm": pin_clr, "mu_pin": mu_pin,
                    "F_drive_N": F_req, "motor_torque_Nm": T_req_Nm,
                    "nema17_055Nm_safety_factor": 0.55 / max(T_req_Nm, 1e-6),
                    "backlash_z_mm": bl_z,
                })
    (RESULTS / "scz_deep_v3_1.json").write_text(json.dumps(scz_cases, ensure_ascii=False, indent=2), encoding="utf-8")
    for c in scz_cases:
        if c["height_case"] == "H_work_min_125":
            print(f"[SCZ Audit] {c['screw']:20s} pin_clr={c['pin_clearance_mm']:.3f} -> F={c['F_drive_N']:.1f}N, T={c['motor_torque_Nm']:.3f}Nm (SF={c['nema17_055Nm_safety_factor']:.2f}), bl_z={c['backlash_z_mm']:.3f}mm")

    # 4. Generate V3.1 Diagnostic Figures
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.2, 4.8), dpi=180)
    # Left: F09 V3 (0.030mm) vs V3.1 (215mm X-arm) vs F07/F08
    labels_f = ["F09 (V3误:横梁中)", "F09 (V3.1:215mm悬臂)", "F07 (单立柱)", "F08 (单立柱)"]
    vals_y = [0.0304, fea_summary["F09"]["finest_32"]["tip_y_deflection_mm"], fea_summary["F07"]["finest_32"]["tip_y_deflection_mm"], fea_summary["F08"]["finest_32"]["tip_y_deflection_mm"]]
    vals_ideal = [0.0304, fea_summary["F09"]["ideal_rigid_16"]["tip_y_deflection_mm"], fea_summary["F07"]["ideal_rigid_16"]["tip_y_deflection_mm"], fea_summary["F08"]["ideal_rigid_16"]["tip_y_deflection_mm"]]
    xf = np.arange(len(labels_f))
    ax1.bar(xf - 0.18, vals_y, width=0.36, color="#2563EB", label="有限连接柔度 (3D FEA)")
    ax1.bar(xf + 0.18, vals_ideal, width=0.36, color="#94A3B8", label="理想刚性锁紧")
    ax1.set_xticks(xf, labels_f, rotation=15)
    ax1.set_ylabel("10 N 侧载末端 Y 向挠度 (mm)")
    ax1.set_title("V3.1 纠错｜F09 补齐 215mm 悬臂后与 F07 同口径对比")
    ax1.legend(fontsize=8)
    ax1.grid(axis="y", alpha=0.25)

    # Right: SCZ & F09 true DOF mesh convergence
    scz_dofs = [r["dofs"] for r in scz_conv]
    scz_uy = [r["tip_y_deflection_mm"] for r in scz_conv]
    f09_dofs = [r["dofs"] for r in fea_summary["F09"]["convergence"]]
    f09_uy = [r["tip_y_deflection_mm"] for r in fea_summary["F09"]["convergence"]]
    ax2.plot(scz_dofs, scz_uy, marker="o", color="#DC2626", label="SCZ 真离散收敛 (60→564 DOFs)")
    ax2.plot(f09_dofs, f09_uy, marker="s", color="#0284C7", label="F09 悬臂龙门收敛")
    ax2.set_xlabel("有限元总自由度 (DOFs)")
    ax2.set_ylabel("末端侧向挠度 (mm)")
    ax2.set_title("V3.1 修复｜真实网格离散自由度收敛验证")
    ax2.legend(fontsize=8)
    ax2.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIGURES / "v3_1_fea_correction.png", dpi=180, facecolor="white")
    plt.close(fig)

    print("V3.1 TARGETED VERIFICATION COMPLETED.")


if __name__ == "__main__":
    main()
