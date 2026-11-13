import math

import numpy as np

from .evaluate import evaluate_candidate


def flip_torque_nmm(mass_kg, horizontal_com_distance_mm, gravity=9.81):
    return mass_kg * gravity * horizontal_com_distance_mm


def _parameters(spec, parameters=None):
    return dict(spec["parameters"] if parameters is None else dict(spec["parameters"], **parameters))


def _effective_length_mm(spec, parameters=None):
    p = _parameters(spec, parameters)
    if spec["family"] == "arm_fold":
        return p["arm_length_mm"]
    if spec["family"] == "scissor":
        return p["height_work_max_mm"]
    if spec["family"] == "drawer_y":
        return 180.0
    return spec["common"]["column_top_mm"] - spec["common"]["column_bottom_mm"]


def _effective_lock_span_mm(spec, parameters=None):
    p = _parameters(spec, parameters)
    return spec["lock_span_mm"] + (p.get("overlap_mm", 0.0) if spec["family"] in {"telescope_2", "telescope_3"} else 0.0)


def _effective_clearance_mm(spec, parameters=None):
    p = _parameters(spec, parameters)
    clearance = spec["clearance_mm"]
    if spec["family"] in {"guided_single", "guided_double"}:
        slot_side = (p["slot_width_mm"] - p["roller_diameter_mm"]) / 2
        clearance += 0.01 * slot_side
    return clearance


def repeatability_surrogate(spec, parameters=None):
    p = _parameters(spec, parameters)
    length = _effective_length_mm(spec, p)
    clearance = _effective_clearance_mm(spec, p)
    value = spec["seat_error_mm"] + clearance * length / _effective_lock_span_mm(spec, p) * math.sqrt(spec["joint_count"])
    if spec["family"] == "scissor":
        height = max(p["height_fold_mm"], p["height_work_max_mm"] - 180.0)
        span = math.sqrt(max(0.0, 4 * p["arm_length_mm"] ** 2 - height**2))
        value += clearance * span / height
    return value


def _peak_torque(spec, trace):
    mass = spec["mass_kg"]
    peak = 0.0
    for state in trace:
        areas = [max(polygon.area, 1e-9) for polygon in state["moving"].values()]
        total_area = sum(areas)
        com_x = sum(
            polygon.centroid.x * area
            for polygon, area in zip(state["moving"].values(), areas)
        ) / total_area
        lever = abs(com_x - state["pivot_x_mm"])
        peak = max(peak, flip_torque_nmm(mass, lever))
    return peak


def structural_metrics(spec, parameters=None):
    evaluated = evaluate_candidate(spec, parameters=parameters, steps=31)
    common = spec["common"]
    p = _parameters(spec, parameters)
    length = _effective_length_mm(spec, p)
    joints = spec["joint_count"]
    beam_factor = 2.0 if spec["family"] in {"root_double", "guided_double"} else 1.0
    if spec["family"] in {"telescope_2", "telescope_3"}:
        stages = 2 if spec["family"] == "telescope_2" else 3
        extended = common["column_top_mm"] - common["column_bottom_mm"]
        stage_height = (extended + (stages - 1) * p["overlap_mm"]) / stages
        beam_factor *= 1.0 + 2.0 * p["overlap_mm"] / stage_height
    joint_compliance = 1.0 + 0.08 * max(0, joints - 1)
    k_beam = beam_factor * 3 * common["aluminum_E_N_mm2"] * common["extrusion_I_mm4"] / (
        length**3 * joint_compliance
    )
    k_lock = spec["lock_count"] * common["contact_k_N_mm"] * (
        _effective_lock_span_mm(spec, p) / (2 * length)
    ) ** 2
    k_equivalent = 1.0 / (1.0 / k_beam + 1.0 / k_lock)
    tip_deflection = common["lateral_load_N"] / k_equivalent
    peak_torque = _peak_torque(spec, evaluated["trace"])
    mass = spec["mass_kg"]
    if spec["family"] == "scissor":
        drive_force = mass * 9.81 * evaluated["peak_drive_gain_work"] / common["drive_efficiency"]
        drive_model = "scissor vertical load times working-range geometric gain / 0.8 efficiency"
    elif spec["family"] in {"telescope_2", "telescope_3"}:
        drive_force = mass * 9.81 * (1 + common["drawer_friction_coefficient"]) / common["drive_efficiency"]
        drive_model = "vertical telescope gravity and 0.08 friction / 0.8 efficiency"
    elif spec["family"] == "drawer_y":
        drive_force = mass * (common["drawer_friction_coefficient"] * 9.81 + common["drive_acceleration_m_s2"])
        drive_model = "horizontal drawer 0.08 rolling friction plus 0.5 m/s^2 acceleration"
    else:
        drive_force = peak_torque / common["drive_arm_mm"]
        drive_model = f"gravity torque / declared {common['drive_arm_mm']:.0f} mm drive arm"
    cost = spec["base_cost_CNY"]
    cost += 0.5 * p.get("lift_mm", 0.0) + 0.4 * abs(p.get("shift_x_mm", 0.0))
    cost += 4.0 * p.get("cabinet_clearance_mm", 0.0)
    reliability_proxy = max(
        0.0,
        100.0 - 4.0 * joints - 1.5 * spec["custom_parts"] - 3.0 * spec["complexity"]
        - (8.0 if spec["family"] in {"root_double", "guided_double", "scissor"} else 0.0),
    )
    return {
        "id": spec["id"],
        "simulation_level": "L2_reduced_order_statics_stiffness",
        "peak_torque_Nmm": peak_torque,
        "peak_drive_force_N": drive_force,
        "drive_model": drive_model,
        "beam_stiffness_N_mm": k_beam,
        "lock_stiffness_N_mm": k_lock,
        "equivalent_stiffness_N_mm": k_equivalent,
        "tip_deflection_mm": tip_deflection,
        "estimated_incremental_cost_CNY": cost,
        "reliability_proxy_score": reliability_proxy,
        "manufacturing_complexity_score": spec["complexity"],
        "storage_ratio": evaluated["storage_ratio"],
        "max_intersection_mm2": evaluated["max_intersection_mm2"],
        "workspace_coverage": evaluated["workspace_coverage"],
        "reachable_fraction": evaluated["reachable_fraction"],
        "passed_screen": evaluated["passed_screen"],
        "screen_reasons": evaluated["screen_reasons"],
        "parameters": p,
    }


def repeatability_monte_carlo(spec, parameters=None, samples=10000, seed=20261113, return_samples=False):
    if samples < 100:
        raise ValueError("At least 100 Monte Carlo samples are required")
    rng = np.random.default_rng(seed)
    p = _parameters(spec, parameters)
    length = _effective_length_mm(spec, p)
    leverage = length / _effective_lock_span_mm(spec, p)
    clearance = _effective_clearance_mm(spec, p)
    seat = spec["seat_error_mm"]
    joints = spec["joint_count"]
    x = rng.uniform(-seat, seat, samples)
    z = rng.uniform(-seat, seat, samples)
    for _ in range(joints):
        x += rng.uniform(-clearance, clearance, samples) * leverage
        z += rng.uniform(-clearance, clearance, samples) * leverage * 0.55
    if spec["family"] == "scissor":
        height = max(p["height_fold_mm"], p["height_work_max_mm"] - 180.0)
        span = math.sqrt(4 * p["arm_length_mm"] ** 2 - height**2)
        gain = span / height
        z += rng.uniform(-clearance, clearance, samples) * gain
        x += rng.uniform(-clearance, clearance, samples) * 2.0
    radial = np.hypot(x, z)
    result = {
        "id": spec["id"],
        "samples": samples,
        "seed": seed,
        "input_distribution": "independent rectangular clearance and seat errors",
        "mean_mm": float(np.mean(radial)),
        "std_mm": float(np.std(radial, ddof=1)),
        "p50_mm": float(np.percentile(radial, 50)),
        "p95_mm": float(np.percentile(radial, 95)),
        "p99_mm": float(np.percentile(radial, 99)),
        "max_mm": float(np.max(radial)),
    }
    if return_samples:
        result["samples_mm"] = radial
    return result
