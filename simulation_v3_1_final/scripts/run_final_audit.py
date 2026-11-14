"""V3.1 Final targeted verification script (P0-1 F09 consistency, P0-2 swept collision, F07/SCZ/F08/F12)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

FINAL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(FINAL_DIR / "src"))

from foldsim_v3_1_final.evaluate3d import evaluate_candidate_3d
from foldsim_v3_1_final.fea3d import evaluate_candidate_fea3d
from foldsim_v3_1_final.registry import load_candidates


def main() -> None:
    results_dir = FINAL_DIR / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    cands = load_candidates(FINAL_DIR / "config" / "candidates_v3_1_final.json")

    # 1. P0-1: F09 FEA (with arm-hinge compliance vs ideal rigid) + F07/F08/F12/SCZ
    fea = {}
    for cid in ["F09", "F07", "F08", "F12"]:
        r_comp = evaluate_candidate_fea3d(cid, cands[cid], n_sub=32, ideal_rigid_joints=False)
        r_ideal = evaluate_candidate_fea3d(cid, cands[cid], n_sub=32, ideal_rigid_joints=True)
        fea[cid] = {"compliant_32": r_comp, "ideal_32": r_ideal}
        print(f"[FEA Final] {cid:4s}: Y={r_comp['tip_y_deflection_mm']:.4f}mm (ideal {r_ideal['tip_y_deflection_mm']:.4f}mm), X={r_comp['tip_x_deflection_mm']:.4f}mm, Z={r_comp['tip_z_deflection_mm']:.4f}mm, DOFs={r_comp['dofs']}")
    fea["SCZ"] = {"compliant_8": evaluate_candidate_fea3d("SCZ", cands["SCZ"], n_sub=8)}
    print(f"[FEA Final] SCZ : Y={fea['SCZ']['compliant_8']['tip_y_deflection_mm']:.4f}mm, DOFs={fea['SCZ']['compliant_8']['dofs']}")
    (results_dir / "fea_final.json").write_text(json.dumps(fea, ensure_ascii=False, indent=2), encoding="utf-8")

    # 2. P0-1 & P0-2: Continuous swept collision (steps=101, step_bound=2.0mm, angle_bound=3.0deg)
    cases = [
        ("F09_with_215mm_arm_lift85", "F09", {"lift_mm": 85.0, "shift_x_mm": 0.0, "arm_fold_enabled": 1}),
        ("F09_with_215mm_arm_lift105", "F09", {"lift_mm": 105.0, "shift_x_mm": 0.0, "arm_fold_enabled": 1}),
        ("F09_with_215mm_arm_lift115", "F09", {"lift_mm": 115.0, "shift_x_mm": 0.0, "arm_fold_enabled": 1}),
        ("F09_with_215mm_arm_no_fold", "F09", {"lift_mm": 85.0, "shift_x_mm": 0.0, "arm_fold_enabled": 0}),
        ("F07_lift75_shift0", "F07", {"lift_mm": 75.0, "shift_x_mm": 0.0}),
        ("SCZ_continuous_park", "SCZ", {"arm_length_mm": 154.0, "height_fold_mm": 45.0}),
        ("F08_lift25_shift_n75", "F08", {"lift_mm": 25.0, "shift_x_mm": -75.0}),
        ("F08_lift30_shift_n75", "F08", {"lift_mm": 30.0, "shift_x_mm": -75.0}),
        ("F12_preload_recheck", "F12", {"overlap_mm": 52.0, "outer_size_mm": 60.0}),
    ]
    swept = []
    for label, cid, params in cases:
        res = evaluate_candidate_3d(cands[cid], parameters=params, steps=101, swept_check=True, step_bound_mm=2.0, angle_bound_deg=3.0)
        res["label"] = label
        swept.append(res)
        print(f"[Swept Final] {label:28s} | status={res['collision_status']:10s} | pass={str(res['passed_screen']):5s} | pen={res['max_penetration_mm']:.4f}mm | min_clr={res['min_clearance_mm']:.2f}mm ({res['worst_clr_pair']} @t={res['worst_clr_t']:.2f}) | stor={res['storage_ratio']:.3f}")
    (results_dir / "swept_final.json").write_text(json.dumps(swept, ensure_ascii=False, indent=2), encoding="utf-8")
    print("FINAL VERIFICATION COMPLETED.")


if __name__ == "__main__":
    main()
