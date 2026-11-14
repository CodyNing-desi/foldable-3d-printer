"""Round 3 unified mechanics, separate deflection/error/backlash/risk reporting, and Monte Carlo."""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from .evaluate3d import evaluate_candidate_3d
from .fea3d import evaluate_candidate_fea3d, hollow_square_props


def _params(spec: dict[str, Any], parameters: dict[str, Any] | None = None) -> dict[str, Any]:
    return dict(spec["parameters"] if parameters is None else dict(spec["parameters"], **parameters))


def structural_metrics_v3(spec: dict[str, Any], parameters: dict[str, Any] | None = None, steps: int = 31, swept_check: bool = True) -> dict[str, Any]:
    ev = evaluate_candidate_3d(spec, parameters=parameters, steps=steps, swept_check=swept_check)
    p = _params(spec, parameters)
    common = spec["common"]
    cid = spec["id"]
    family = spec["family"]

    clearance_play_mm = 0.0
    backlash_z_mm = 0.0
    buckling_sf = None
    tipping_sf = None
    sync_tilt_deg = 0.0
    peak_torque_Nmm = 0.0
    peak_drive_force_N = 0.0
    drive_model = ""

    W = spec["mass_kg"] * 9.81
    if family in {"root_single_lift", "root_double_lift"}:
        lift_force = W * (1.0 + common["drawer_friction_coefficient"]) / common["leadscrew_efficiency"]
        peak_torque_Nmm = W * 165.0
        peak_drive_force_N = max(lift_force, peak_torque_Nmm / common["drive_arm_mm"])
        drive_model = "Twin-rod lift leadscrew (eta=0.55) + 50mm fold arm"
        if family == "root_double_lift":
            sync_err = p.get("sync_error_mm", 0.10)
            sync_tilt_deg = math.degrees(math.atan2(sync_err, 260.0))
            backlash_z_mm = 0.06
    elif family == "root_single_rear":
        shift_x = abs(p["shift_x_mm"])
        M_tip = W * (shift_x + 165.0)
        M_rest = 4.5 * 9.81 * (155.0 + shift_x)
        tipping_sf = M_rest / max(M_tip, 1e-6)
        peak_torque_Nmm = W * 165.0
        peak_drive_force_N = peak_torque_Nmm / common["drive_arm_mm"]
        drive_model = "Rear-offset pivot / 50mm drive arm"
    elif family in {"telescope_2", "telescope_3"}:
        stages = 2 if family == "telescope_2" else 3
        overlap = p["overlap_mm"]
        H_ext = common["column_top_mm"] - common["column_bottom_mm"]
        stage_h = (H_ext + (stages - 1) * overlap) / stages
        rad_clr = p.get("radial_clearance_mm", 0.015)
        tilt_per_stage = (2.0 * rad_clr) / max(overlap, 10.0)
        clearance_play_mm = tilt_per_stage * (2.0 * stage_h - overlap) + tilt_per_stage * stage_h
        peak_drive_force_N = W * (1.0 + common["drawer_friction_coefficient"]) / common["leadscrew_efficiency"]
        peak_torque_Nmm = common["lateral_load_N"] * H_ext
        backlash_z_mm = 0.05
        drive_model = "Vertical telescoping leadscrew (eta=0.55, mu=0.08)"
    elif family == "scissor":
        arm_len = p["arm_length_mm"]
        h_min = max(p["height_fold_mm"], p["height_work_max_mm"] - 180.0)
        span = math.sqrt(max(1.0, 4.0 * arm_len**2 - h_min**2))
        theta = math.atan2(h_min, span)
        gain = span / h_min
        pin_f = 4.0 * common["pin_friction_coefficient"] * (4.0 / arm_len) * W / max(math.sin(theta), 0.1)
        peak_drive_force_N = (W * gain + pin_f + common["drawer_friction_coefficient"] * W) / common["leadscrew_efficiency"]
        backlash_z_mm = gain * p.get("screw_backlash_mm", 0.04) + 2.0 * spec["clearance_mm"] / max(math.sin(theta), 0.1)
        sync_tilt_deg = math.degrees(math.atan2(gain * p.get("sync_error_mm", 0.08), 260.0))
        I_min = p.get("arm_width_mm", 20.0) * (p.get("arm_thick_mm", 6.0) ** 3) / 12.0
        P_cr = (math.pi**2 * common["aluminum_E_N_mm2"] * I_min) / (arm_len**2)
        buckling_sf = P_cr / max(0.25 * W / max(math.sin(theta), 0.1), 1e-6)
        drive_model = "SCZ horizontal T8 screw (eta=0.55) + 8-pin Coulomb + rail friction"
    else:
        peak_torque_Nmm = W * 150.0
        peak_drive_force_N = peak_torque_Nmm / common["drive_arm_mm"]
        drive_model = "Generic 50mm arm / gravity torque"

    if cid in {"F07", "F09", "F12", "SCZ", "F08"}:
        fea = evaluate_candidate_fea3d(cid, spec, parameters=p, n_sub=10)
        elastic_deflection_mm = fea["tip_lateral_deflection_mm"]
        torsion_induced_mm = fea["torsion_induced_mm"]
    else:
        L = common["column_top_mm"] - common["column_bottom_mm"]
        factor = 2.0 if "double" in family else 1.0
        elastic_deflection_mm = common["lateral_load_N"] * L**3 / (3.0 * factor * common["aluminum_E_N_mm2"] * common["extrusion_I_mm4"])
        torsion_induced_mm = 0.0

    cost = spec["base_cost_CNY"] + 0.5 * p.get("lift_mm", 0.0) + 0.4 * abs(p.get("shift_x_mm", 0.0)) + 4.0 * p.get("cabinet_clearance_mm", 0.0)
    return {
        "id": cid,
        "simulation_level": "L3_3D_OBB_swept_and_space_frame_FEA",
        "elastic_deflection_mm": float(elastic_deflection_mm),
        "torsion_induced_mm": float(torsion_induced_mm),
        "clearance_play_mm": float(clearance_play_mm),
        "backlash_z_mm": float(backlash_z_mm),
        "sync_tilt_deg": float(sync_tilt_deg),
        "buckling_safety_factor": buckling_sf,
        "tipping_safety_factor": tipping_sf,
        "peak_torque_Nmm": float(peak_torque_Nmm),
        "peak_drive_force_N": float(peak_drive_force_N),
        "drive_model": drive_model,
        "estimated_incremental_cost_CNY": float(cost),
        "storage_ratio": ev["storage_ratio"],
        "core_storage_ratio": ev["core_storage_ratio"],
        "max_penetration_mm": ev["max_penetration_mm"],
        "workspace_coverage": ev["workspace_coverage"],
        "reachable_fraction": ev["reachable_fraction"],
        "max_pressure_angle_deg": ev["max_pressure_angle_deg"],
        "dof": ev["dof"],
        "com_stable": ev["com_stable"],
        "passed_screen": ev["passed_screen"],
        "screen_reasons": ev["screen_reasons"],
        "parameters": p,
        "fatigue_and_thermal_drift": "未知（需实体台架与温升实测）",
    }


def repeatability_monte_carlo_v3(
    spec: dict[str, Any],
    parameters: dict[str, Any] | None = None,
    samples: int = 10000,
    seed: int = 20261113,
) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    p = _params(spec, parameters)
    common = spec["common"]
    family = spec["family"]

    E_samples = rng.normal(common["aluminum_E_N_mm2"], 2000.0, samples)
    E_ratio = common["aluminum_E_N_mm2"] / np.clip(E_samples, 55000.0, 80000.0)
    theta_err = rng.uniform(-0.08, 0.08, samples) * math.pi / 180.0
    x_err = 300.0 * theta_err
    z_err = rng.uniform(-spec["seat_error_mm"], spec["seat_error_mm"], samples)

    clr = spec["clearance_mm"]
    if family in {"telescope_2", "telescope_3"}:
        stages = 2 if family == "telescope_2" else 3
        overlap = p["overlap_mm"]
        rad_clr = rng.uniform(0.5 * p.get("radial_clearance_mm", 0.015), 1.5 * p.get("radial_clearance_mm", 0.015), samples)
        tilt = (2.0 * rad_clr) / max(overlap, 10.0)
        x_err += (stages - 1) * tilt * 240.0 * rng.choice([-1.0, 1.0], samples)
        z_err += rng.uniform(-0.04, 0.04, samples) * (stages - 1)
    elif family == "scissor":
        arm_len = p["arm_length_mm"]
        h_min = max(p["height_fold_mm"], p["height_work_max_mm"] - 180.0)
        span = math.sqrt(max(1.0, 4.0 * arm_len**2 - h_min**2))
        gain = span / h_min
        screw_bl = rng.uniform(-p.get("screw_backlash_mm", 0.04), p.get("screw_backlash_mm", 0.04), samples)
        pin_play = rng.uniform(-clr, clr, samples) * 2.0
        sync_play = rng.uniform(-p.get("sync_error_mm", 0.08), p.get("sync_error_mm", 0.08), samples) * 0.5
        z_err += gain * (screw_bl + sync_play) + pin_play * gain
        x_err += rng.uniform(-clr, clr, samples) * 2.5
    elif family == "root_double_lift":
        lev = 345.0 / max(spec["lock_span_mm"], 20.0)
        sync_err = rng.uniform(-p.get("sync_error_mm", 0.10), p.get("sync_error_mm", 0.10), samples)
        x_err += rng.uniform(-clr, clr, samples) * lev * 1.5 + sync_err
        z_err += rng.uniform(-clr, clr, samples) * lev * 0.5 + sync_err * 0.5
    else:
        lev = 345.0 / max(spec["lock_span_mm"], 20.0)
        for _ in range(spec["joint_count"]):
            x_err += rng.uniform(-clr, clr, samples) * lev
            z_err += rng.uniform(-clr, clr, samples) * lev * 0.5

    x_err *= E_ratio
    radial = np.hypot(x_err, z_err)
    p95 = float(np.percentile(radial, 95))
    risk = "低" if p95 < 0.50 else ("中" if p95 < 0.80 else "高")
    return {
        "id": spec["id"],
        "samples": samples,
        "seed": seed,
        "p50_mm": float(np.percentile(radial, 50)),
        "p95_mm": p95,
        "p99_mm": float(np.percentile(radial, 99)),
        "print_accuracy_risk": risk,
    }
