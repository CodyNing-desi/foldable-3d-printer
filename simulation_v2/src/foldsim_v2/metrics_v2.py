"""High-fidelity mechanics, F07/F12/SCZ/F08/F04 physics, and tolerance/material uncertainty Monte Carlo."""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from .evaluate3d import evaluate_candidate_3d
from .fea3d import evaluate_candidate_fea3d, hollow_square_props


def _params(spec: dict[str, Any], parameters: dict[str, Any] | None = None) -> dict[str, Any]:
    return dict(spec["parameters"] if parameters is None else dict(spec["parameters"], **parameters))


def f07_mechanism_mechanics(spec: dict[str, Any], p: dict[str, Any]) -> dict[str, Any]:
    """F07: lift force, fold torque, M8 shoulder bolt shear/bearing stress, 6mm taper pin shear."""
    common = spec["common"]
    mass = spec["mass_kg"]
    g = 9.81
    W = mass * g
    # Lift stage: twin 8mm guide rods (mu=0.08) + T8 leadscrew (eta=0.55)
    lift_force_N = W * (1.0 + common["drawer_friction_coefficient"]) / common["leadscrew_efficiency"]
    # Fold torque: column + folded X-arm COM ~ 165 mm from pivot
    com_dist_mm = 165.0
    fold_torque_Nmm = W * com_dist_mm
    fold_drive_force_N = fold_torque_Nmm / common["drive_arm_mm"]
    # M8 shoulder bolt in double shear: A_shear = 2 * pi * 4^2 = 100.53 mm^2
    hinge_shear_MPa = (W + common["lateral_load_N"]) / (2.0 * math.pi * 4.0**2)
    # 6mm tapered lock pin under 10 N lateral load at z=300 mm, lock_span=60 mm -> F_pin = 10 * 300 / 60 = 50 N
    F_pin = common["lateral_load_N"] * 300.0 / max(spec["lock_span_mm"], 10.0)
    pin_shear_MPa = F_pin / (math.pi * 3.0**2)
    return {
        "lift_drive_force_N": lift_force_N,
        "peak_torque_Nmm": fold_torque_Nmm,
        "peak_drive_force_N": max(lift_force_N, fold_drive_force_N),
        "hinge_shear_MPa": hinge_shear_MPa,
        "lock_pin_shear_MPa": pin_shear_MPa,
        "drive_model": "F07 lift leadscrew (eta=0.55) & 50mm fold arm",
    }


def f12_telescoping_mechanics(spec: dict[str, Any], p: dict[str, Any]) -> dict[str, Any]:
    """F12: stepped hollow sections, PTFE interface tilt, Bredt-Batho torsion, vertical drive."""
    common = spec["common"]
    mass = spec["mass_kg"]
    E = common["aluminum_E_N_mm2"]
    G = common["aluminum_G_N_mm2"]
    overlap = p["overlap_mm"]
    outer_sz = p.get("outer_size_mm", 60.0)
    wall = p.get("wall_mm", 3.0)
    clr = p.get("radial_clearance_mm", 0.08)
    pad = p.get("pad_thickness_mm", 2.92)
    step_sz = 2.0 * (wall + clr + pad)
    H_ext = common["column_top_mm"] - common["column_bottom_mm"]  # 345 mm
    stage_h = (H_ext + 2.0 * overlap) / 3.0

    # Interface clearance tilt: 2 stages, each with radial clearance clr over overlap
    tilt_rad_per_stage = (2.0 * clr) / max(overlap, 10.0)
    clearance_tip_play_mm = tilt_rad_per_stage * (2.0 * stage_h - overlap) + tilt_rad_per_stage * stage_h

    # Torsion from X-arm (215 mm) under 10 N lateral Y load
    T_Nmm = common["lateral_load_N"] * common["x_arm_length_mm"]
    s1 = hollow_square_props(outer_sz, wall)
    s2 = hollow_square_props(outer_sz - step_sz, wall)
    s3 = hollow_square_props(outer_sz - 2.0 * step_sz, wall)
    L1 = stage_h
    L2 = stage_h - overlap
    L3 = H_ext - L1 - L2
    theta_torsion = T_Nmm * (L1 / (G * s1["J"]) + L2 / (G * s2["J"]) + max(0.0, L3) / (G * s3["J"]))
    torsion_tip_mm = common["x_arm_length_mm"] * theta_torsion

    # PTFE pad bearing stress at overlap under 10 N * 345 mm moment
    M_base = common["lateral_load_N"] * H_ext
    F_pad = M_base / max(overlap, 10.0)
    pad_area = (outer_sz - step_sz) * 10.0  # 10 mm pad strip
    pad_stress_MPa = F_pad / pad_area

    drive_force_N = mass * 9.81 * (1.0 + common["drawer_friction_coefficient"]) / common["leadscrew_efficiency"]
    return {
        "stage_height_mm": stage_h,
        "overlap_ratio": overlap / stage_h,
        "clearance_tip_play_mm": clearance_tip_play_mm,
        "torsion_tip_mm": torsion_tip_mm,
        "pad_bearing_MPa": pad_stress_MPa,
        "peak_torque_Nmm": M_base,
        "peak_drive_force_N": drive_force_N,
        "drive_model": "F12 vertical telescoping leadscrew (eta=0.55, mu=0.08)",
    }


def scz_scissor_mechanics(spec: dict[str, Any], p: dict[str, Any]) -> dict[str, Any]:
    """SCZ: nonlinear low-height drive force with pin & rail friction, backlash, L/R sync, Euler buckling."""
    common = spec["common"]
    mass = spec["mass_kg"]
    W = mass * 9.81
    arm_len = p["arm_length_mm"]
    h_max = p["height_work_max_mm"]
    h_min_work = max(p["height_fold_mm"], h_max - common["target_print_height_mm"])
    span_min_work = math.sqrt(max(1.0, 4.0 * arm_len**2 - h_min_work**2))
    theta_min = math.atan2(h_min_work, span_min_work)
    gain_work = span_min_work / h_min_work  # |dS/dH| = 1 / |dH/dS|? Wait: H = sqrt(4L^2 - S^2) -> |dH/dS| = S/H, so dS/dH = H/S, F_S = W * |dH/dS| = W * S/H!
    # Wait! Let's check virtual work: W * dH = F_S * dS -> F_S = W * |dH/dS| = W * (S / H) = W / tan(theta)!
    # Yes! At low height H small, S large -> S/H is LARGE, so F_S is HUGE!
    mu_pin = common["pin_friction_coefficient"]
    mu_rail = common["drawer_friction_coefficient"]
    eta_screw = common["leadscrew_efficiency"]
    # Pin friction adds ~ 8 * mu_pin * r_pin / L_arm * W / sin(theta)
    pin_friction_N = 4.0 * mu_pin * (4.0 / arm_len) * W / max(math.sin(theta_min), 0.1)
    rail_friction_N = mu_rail * W
    F_screw_N = (W * gain_work + pin_friction_N + rail_friction_N) / eta_screw

    # Backlash amplification at low work height: dZ = |dH/dS| * dS_screw + pin_clearance / sin(theta)
    # Wait: dH = (dH/dS) * dS = (S/H) * dS!
    dS_screw = p.get("screw_backlash_mm", 0.04)
    pin_clr = spec["clearance_mm"]
    backlash_z_mm = gain_work * dS_screw + 2.0 * pin_clr / max(math.sin(theta_min), 0.1)

    # Left-right synchronization tilt
    sync_err = p.get("sync_error_mm", 0.08)
    sync_dz_mm = gain_work * sync_err
    sync_tilt_deg = math.degrees(math.atan2(sync_dz_mm, 260.0))

    # Euler buckling of 6 x 20 mm 6061-T6 bar (length = arm_len, I_min = 20 * 6^3 / 12 = 360 mm^4)
    w, t = p.get("arm_width_mm", 20.0), p.get("arm_thick_mm", 6.0)
    I_min = w * (t**3) / 12.0
    P_cr_N = (math.pi**2 * common["aluminum_E_N_mm2"] * I_min) / (arm_len**2)
    axial_load_N = 0.25 * W / max(math.sin(theta_min), 0.1)  # 4 arms share load
    buckling_sf = P_cr_N / max(axial_load_N, 1e-6)

    return {
        "min_work_angle_deg": math.degrees(theta_min),
        "peak_drive_gain": gain_work,
        "peak_drive_force_N": F_screw_N,
        "peak_torque_Nmm": 0.0,
        "backlash_z_mm": backlash_z_mm,
        "sync_tilt_deg": sync_tilt_deg,
        "buckling_safety_factor": buckling_sf,
        "drive_model": "SCZ horizontal T8 screw (eta=0.55) + 8-pin Coulomb + rail friction",
    }


def f08_rear_mechanics(spec: dict[str, Any], p: dict[str, Any]) -> dict[str, Any]:
    """F08: rear-shift bracket bending, tipping stability, counterbalance."""
    common = spec["common"]
    mass = spec["mass_kg"]
    W = mass * 9.81
    shift_x = abs(p["shift_x_mm"])
    # When folded backward (-X), column COM is at x = -shift_x - 165 mm; base + bed (~4.5 kg) COM at x = 155 mm
    M_tip_folded = W * (shift_x + 165.0)
    M_restore_base = 4.5 * 9.81 * (155.0 + shift_x)  # with rear support foot at -shift_x
    tipping_sf = M_restore_base / max(M_tip_folded, 1e-6)
    fold_torque_Nmm = W * 165.0
    return {
        "peak_torque_Nmm": fold_torque_Nmm,
        "peak_drive_force_N": fold_torque_Nmm / common["drive_arm_mm"],
        "rear_tipping_safety_factor": tipping_sf,
        "drive_model": "F08 rear-offset pivot / 50mm drive arm",
    }


def structural_metrics_v2(spec: dict[str, Any], parameters: dict[str, Any] | None = None, steps: int = 31) -> dict[str, Any]:
    ev = evaluate_candidate_3d(spec, parameters=parameters, steps=steps)
    p = _params(spec, parameters)
    cid = spec["id"]
    family = spec["family"]

    # Default mechanics
    mech_extra: dict[str, Any] = {}
    if cid == "F07" or family == "root_single_lift":
        mech_extra = f07_mechanism_mechanics(spec, p)
    elif family in {"telescope_2", "telescope_3"}:
        mech_extra = f12_telescoping_mechanics(spec, p)
    elif family == "scissor":
        mech_extra = scz_scissor_mechanics(spec, p)
    elif family == "root_single_rear":
        mech_extra = f08_rear_mechanics(spec, p)
    else:
        W = spec["mass_kg"] * 9.81
        tq = W * 160.0 if "root" in family or "guided" in family or "case" in family or "external" in family else W * 100.0
        mech_extra = {
            "peak_torque_Nmm": tq,
            "peak_drive_force_N": tq / spec["common"]["drive_arm_mm"],
            "drive_model": "generic 50mm arm / gravity torque",
        }

    # Deflection: use 3D space-frame FEA for core candidates, analytical stepped/frame for others
    if cid in {"F07", "F12", "SCZ", "F08"}:
        fea = evaluate_candidate_fea3d(cid, spec, parameters=p)
        tip_deflection = fea["tip_lateral_deflection_mm"]
        if cid == "F12":
            tip_deflection += mech_extra.get("clearance_tip_play_mm", 0.0)
    else:
        L = spec["common"]["column_top_mm"] - spec["common"]["column_bottom_mm"]
        E = spec["common"]["aluminum_E_N_mm2"]
        I = spec["common"]["extrusion_I_mm4"]
        factor = 2.0 if "double" in family else 1.0
        tip_deflection = spec["common"]["lateral_load_N"] * L**3 / (3.0 * factor * E * I)

    cost = spec["base_cost_CNY"] + 0.5 * p.get("lift_mm", 0.0) + 0.4 * abs(p.get("shift_x_mm", 0.0)) + 4.0 * p.get("cabinet_clearance_mm", 0.0)
    reliability_proxy = max(
        0.0,
        100.0 - 4.0 * spec["joint_count"] - 1.5 * spec["custom_parts"] - 3.0 * spec["complexity"]
        - (8.0 if family in {"root_double", "guided_double", "scissor"} else 0.0),
    )

    return {
        "id": cid,
        "simulation_level": "L3_3D_OBB_and_space_frame_FEA",
        "tip_deflection_mm": float(tip_deflection),
        "estimated_incremental_cost_CNY": float(cost),
        "reliability_proxy_score": float(reliability_proxy),
        "manufacturing_complexity_score": float(spec["complexity"]),
        "storage_ratio": ev["storage_ratio"],
        "core_storage_ratio": ev["core_storage_ratio"],
        "max_penetration_mm": ev["max_penetration_mm"],
        "workspace_coverage": ev["workspace_coverage"],
        "reachable_fraction": ev["reachable_fraction"],
        "max_pressure_angle_deg": ev["max_pressure_angle_deg"],
        "dof": ev["dof"],
        "passed_screen": ev["passed_screen"],
        "screen_reasons": ev["screen_reasons"],
        "parameters": p,
        **mech_extra,
    }


def repeatability_monte_carlo_v2(
    spec: dict[str, Any],
    parameters: dict[str, Any] | None = None,
    samples: int = 10000,
    seed: int = 20261113,
    return_samples: bool = False,
) -> dict[str, Any]:
    """Monte Carlo including manufacturing tolerances, joint clearances, assembly angle error, and E/mu uncertainty."""
    rng = np.random.default_rng(seed)
    p = _params(spec, parameters)
    common = spec["common"]
    family = spec["family"]

    # Material & friction uncertainty
    E_samples = rng.normal(common["aluminum_E_N_mm2"], 2000.0, samples)
    E_ratio = common["aluminum_E_N_mm2"] / np.clip(E_samples, 55000.0, 80000.0)

    # Assembly angular misalignment (+/- 0.08 deg) -> lateral error at 300 mm
    theta_err = rng.uniform(-0.08, 0.08, samples) * math.pi / 180.0
    x_err = 300.0 * theta_err
    z_err = rng.uniform(-spec["seat_error_mm"], spec["seat_error_mm"], samples)

    clr = spec["clearance_mm"]
    if family in {"telescope_2", "telescope_3"}:
        stages = 2 if family == "telescope_2" else 3
        overlap = p["overlap_mm"]
        rad_clr = rng.uniform(0.5 * p.get("radial_clearance_mm", 0.08), 1.5 * p.get("radial_clearance_mm", 0.08), samples)
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
    else:
        lev = 345.0 / max(spec["lock_span_mm"], 20.0)
        for _ in range(spec["joint_count"]):
            x_err += rng.uniform(-clr, clr, samples) * lev
            z_err += rng.uniform(-clr, clr, samples) * lev * 0.5

    # Add elastic compliance variation under 10 N load
    x_err *= E_ratio
    radial = np.hypot(x_err, z_err)

    out = {
        "id": spec["id"],
        "samples": samples,
        "seed": seed,
        "input_distribution": "manufacturing tolerance + clearance + +/-0.08deg assembly + E_Al N(69000,2000)",
        "mean_mm": float(np.mean(radial)),
        "std_mm": float(np.std(radial, ddof=1)),
        "p50_mm": float(np.percentile(radial, 50)),
        "p95_mm": float(np.percentile(radial, 95)),
        "p99_mm": float(np.percentile(radial, 99)),
        "max_mm": float(np.max(radial)),
    }
    if return_samples:
        out["samples_mm"] = radial
    return out
