"""V3.2.1 3D mechanism kinematics with certified analytical motion bounds per phase."""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from .geometry3d import (
    BoundedTrajectory,
    IntervalBoundTrajectory,
    LipschitzTrajectory,
    OBB,
    StaticTrajectory,
    obb_sat_distance,
    rot_y,
)


def scissor_state(arm_length_mm: float, horizontal_span_mm: float) -> dict[str, float]:
    L = float(arm_length_mm)
    S = float(horizontal_span_mm)
    h_sq = max(0.0, 4.0 * L * L - S * S)
    H = math.sqrt(h_sq)
    dH_dS = -S / max(H, 1e-6)
    return {"height_mm": H, "dH_dS": dH_dS, "force_ratio": abs(dH_dS)}


def _base_obbs(common: dict[str, Any]) -> list[OBB]:
    wy = common["base_width_y_mm"] / 2.0
    return [
        OBB.from_bounds("base", 0.0, -wy, 0.0, common["base_depth_x_mm"], wy, common["base_height_mm"], group="fixed", color="#64748B"),
        OBB.from_bounds(
            "bed",
            common["bed_x0_mm"], common["bed_y0_mm"], common["bed_z0_mm"],
            common["bed_x1_mm"], common["bed_y1_mm"], common["bed_z1_mm"],
            group="fixed", color="#94A3B8",
        ),
    ]


def _x_arm_and_toolhead(
    common: dict[str, Any],
    attach_x: float,
    attach_z: float,
    arm_fold_deg: float = 0.0,
    th_x_local: float = 85.0,
) -> list[OBB]:
    arm_len = common["x_arm_length_mm"]
    wy = common["x_arm_width_y_mm"] / 2.0
    hz = common["x_arm_height_z_mm"] / 2.0
    arm = OBB.from_bounds("x_arm", attach_x, -wy, attach_z - hz, attach_x + arm_len, wy, attach_z + hz, group="moving", color="#0284C7")
    th = OBB.from_bounds(
        "toolhead",
        attach_x + th_x_local, -26.0, attach_z - 67.0,
        attach_x + th_x_local + common["toolhead_x_mm"], 26.0, attach_z - 12.0,
        group="moving", color="#0369A1",
    )
    if abs(arm_fold_deg) > 1e-6:
        hinge = np.array([attach_x, 0.0, attach_z], dtype=float)
        R_arm = rot_y(arm_fold_deg)
        arm = arm.transformed(rotation=R_arm, origin=hinge)
        th = th.transformed(rotation=R_arm, origin=hinge)
    return [arm, th]


def _phase_lift_fold(t: float, lift: float, shift: float, arm_fold_enabled: bool) -> tuple[float, float, float, float]:
    if arm_fold_enabled:
        arm_frac = min(1.0, max(0.0, t / 0.2))
        lift_t = min(1.0, max(0.0, (t - 0.2) / 0.20))
        shift_t = min(1.0, max(0.0, (t - 0.28) / 0.17))
        fold_frac = min(1.0, max(0.0, (t - 0.45) / 0.50))
        lift_frac = 0.5 - 0.5 * math.cos(math.pi * lift_t)
        shift_frac = 0.5 - 0.5 * math.cos(math.pi * shift_t)
        return lift * lift_frac, shift * shift_frac, fold_frac, arm_frac
    arm_frac = 0.0
    lift_t = min(1.0, max(0.0, t / 0.25))
    fold_frac = min(1.0, max(0.0, (t - 0.25) / 0.70))
    lift_frac = 0.5 - 0.5 * math.cos(math.pi * lift_t)
    return lift * lift_frac, shift * lift_frac, fold_frac, arm_frac


def _make_beam_obb(name: str, p0: np.ndarray, p1: np.ndarray, width_y: float, thick_in_plane: float, group: str = "moving", color: str = "#2563EB") -> OBB:
    vec = p1 - p0
    length = float(np.linalg.norm(vec))
    ex = vec / max(length, 1e-9)
    ey = np.array([0.0, 1.0, 0.0])
    ez = np.cross(ex, ey)
    ez /= max(float(np.linalg.norm(ez)), 1e-9)
    axes = np.column_stack([ex, ey, ez])
    center = 0.5 * (p0 + p1)
    half = np.array([0.5 * length, 0.5 * width_y, 0.5 * thick_in_plane], dtype=float)
    return OBB(name=name, center=center, axes=axes, half_extents=half, group=group, color=color)


def _select_optimal_accessory_obb(fixed: list[OBB], moving: list[OBB], common: dict[str, Any]) -> list[OBB]:
    ax, ay, az = common["accessory_x_mm"], common["accessory_y_mm"], common["accessory_z_mm"]
    obstacles = fixed + moving
    pts = np.vstack([o.corners() for o in obstacles])
    mn, mx = np.min(pts, axis=0), np.max(pts, axis=0)
    candidates = [
        OBB.from_bounds("transport_accessories", 65.0, -0.5 * ay, 62.0, 65.0 + ax, 0.5 * ay, 62.0 + az, group="extra", color="#F59E0B"),
        OBB.from_bounds("transport_accessories", 110.0, -0.5 * ay, 62.0, 110.0 + ax, 0.5 * ay, 62.0 + az, group="extra", color="#F59E0B"),
        OBB.from_bounds("transport_accessories", mx[0] + 2.0, -0.5 * ay, 0.0, mx[0] + 2.0 + ax, 0.5 * ay, az, group="extra", color="#F59E0B"),
        OBB.from_bounds("transport_accessories", 55.0, mx[1] + 2.0, 0.0, 55.0 + ax, mx[1] + 2.0 + ay, az, group="extra", color="#F59E0B"),
        OBB.from_bounds("transport_accessories", 55.0, mn[1] - 2.0 - ay, 0.0, 55.0 + ax, mn[1] - 2.0, az, group="extra", color="#F59E0B"),
        OBB.from_bounds("transport_accessories", mn[0] - 2.0 - ax, -0.5 * ay, 0.0, mn[0] - 2.0, 0.5 * ay, az, group="extra", color="#F59E0B"),
    ]
    best_obb = None
    best_vol = float("inf")
    for cand in candidates:
        if not any(obb_sat_distance(cand, obs)[0] for obs in obstacles):
            c_pts = np.vstack([pts, cand.corners()])
            dims = np.max(c_pts, axis=0) - np.min(c_pts, axis=0)
            vol = float(dims[0] * dims[1] * dims[2])
            if vol < best_vol:
                best_vol = vol
                best_obb = cand
    if best_obb is None:
        best_obb = OBB.from_bounds("transport_accessories", mx[0] + 5.0, -0.5 * ay, 0.0, mx[0] + 5.0 + ax, 0.5 * ay, az, group="extra", color="#F59E0B")
    return [best_obb]


def _evaluate_workspace_z(spec: dict[str, Any], p: dict[str, Any]) -> tuple[float, float, float]:
    common = spec["common"]
    family = spec["family"]
    target_h = common["target_print_height_mm"]
    bed_top = common["bed_z1_mm"]
    if family == "scissor":
        h_max = p["height_work_max_mm"]
        h_min = max(p["height_fold_mm"], 23.0)
        z_travel = max(0.0, h_max - h_min)
        return min(target_h, z_travel) / target_h, bed_top, bed_top + z_travel
    z_max_nozzle = common["column_top_mm"] - 75.0
    usable = max(0.0, min(target_h, z_max_nozzle - bed_top))
    return usable / target_h, bed_top, z_max_nozzle


def get_phase_intervals(spec: dict[str, Any], parameters: dict[str, Any] | None = None) -> list[tuple[float, float]]:
    p = dict(spec["parameters"], **(parameters or {}))
    family = spec["family"]
    if family in {"root_single", "root_single_lift", "root_single_rear", "root_double", "root_double_lift", "guided_single", "guided_double", "case_linked", "external_combo"}:
        arm_fold_enabled = bool(p.get("arm_fold_enabled", 1 if family in {"root_single_lift", "root_double_lift", "root_single_rear", "guided_single"} else 0))
        if arm_fold_enabled:
            return [(0.0, 0.20), (0.20, 0.28), (0.28, 0.45), (0.45, 0.95), (0.95, 1.0)]
        return [(0.0, 0.25), (0.25, 0.95), (0.95, 1.0)]
    if family == "scissor":
        return [(0.0, 0.15), (0.15, 1.0)]
    return [(0.0, 1.0)]


def build_state_at_t(
    spec: dict[str, Any],
    t: float,
    parameters: dict[str, Any] | None = None,
    include_extra: bool = False,
) -> dict[str, Any]:
    if parameters is not None:
        spec = dict(spec)
        spec["parameters"] = dict(spec["parameters"], **parameters)
    common = spec["common"]
    p = spec["parameters"]
    family = spec["family"]
    ws_cov, z_min_n, z_max_n = _evaluate_workspace_z(spec, p)
    t = float(min(1.0, max(0.0, t)))

    if family in {"root_single", "root_single_lift", "root_single_rear", "root_double", "root_double_lift", "guided_single", "guided_double", "case_linked", "external_combo"}:
        is_double = family in {"root_double", "root_double_lift", "guided_double", "external_combo"}
        is_lift_tower = family in {"root_single_lift", "root_double_lift"}
        arm_fold_enabled = bool(p.get("arm_fold_enabled", 1 if family in {"root_single_lift", "root_double_lift", "root_single_rear", "guided_single"} else 0))

        lift_val = p.get("lift_mm", 0.0)
        shift_val = p.get("shift_x_mm", 0.0)
        pivot0 = np.array([40.0, 0.0, 20.0], dtype=float)
        direction = 1.0 if family == "root_single_rear" else -1.0

        lift, shift, fold_frac, arm_frac = _phase_lift_fold(t, lift_val, shift_val, arm_fold_enabled)
        angle_deg = p["fold_angle_deg"] * fold_frac
        arm_fold_deg = 90.0 * arm_frac if arm_fold_enabled else 0.0
        R_col = rot_y(angle_deg if direction < 0 else -angle_deg)
        trans_col = np.array([shift, 0.0, lift], dtype=float)

        fixed = _base_obbs(common)
        moving: list[OBB] = []
        extra: list[OBB] = []
        allow_self_pairs: set[tuple[str, str]] = set()
        allow_fixed_pairs: set[tuple[str, str]] = set()

        if is_double:
            col_l = OBB.from_bounds("column_left", 25.0, -150.0, 20.0, 55.0, -110.0, 365.0, group="moving", color="#2563EB")
            col_r = OBB.from_bounds("column_right", 25.0, 110.0, 20.0, 55.0, 150.0, 365.0, group="moving", color="#2563EB")
            cross = OBB.from_bounds("crossbar", 25.0, -150.0, 335.0, 55.0, 150.0, 365.0, group="moving", color="#1D4ED8")
            bridge = OBB.from_bounds("bridge_beam", 25.0, -110.0, 280.0, 55.0, 110.0, 310.0, group="moving", color="#1D4ED8")
            arm_parts = _x_arm_and_toolhead(common, attach_x=55.0, attach_z=295.0, arm_fold_deg=arm_fold_deg)
            base_moving = [col_l, col_r, cross, bridge] + arm_parts
            allow_self_pairs.update({
                ("column_left", "crossbar"), ("column_right", "crossbar"),
                ("column_left", "bridge_beam"), ("column_right", "bridge_beam"),
                ("bridge_beam", "x_arm"), ("x_arm", "toolhead"),
            })
        else:
            col = OBB.from_bounds("column", 25.0, -20.0, 20.0, 55.0, 20.0, 365.0, group="moving", color="#2563EB")
            arm_parts = _x_arm_and_toolhead(common, attach_x=55.0, attach_z=295.0, arm_fold_deg=arm_fold_deg)
            base_moving = [col] + arm_parts
            allow_self_pairs.update({("column", "x_arm"), ("x_arm", "toolhead"), ("column", "toolhead")})

        for m in base_moving:
            moving.append(m.transformed(rotation=R_col, origin=pivot0, translation=trans_col))

        if is_lift_tower:
            tower_top = 20.0 + lift_val + 28.0
            y_positions = [-130.0, 130.0] if is_double else [0.0]
            for idx_y, yc in enumerate(y_positions):
                suf = f"_{idx_y}" if is_double else ""
                fixed.append(OBB.from_bounds(f"lift_tower_rod_L{suf}", 16.0, yc - 34.0, 20.0, 24.0, yc - 26.0, tower_top, group="fixed", color="#475569"))
                fixed.append(OBB.from_bounds(f"lift_tower_rod_R{suf}", 16.0, yc + 26.0, 20.0, 24.0, yc + 34.0, tower_top, group="fixed", color="#475569"))
                fixed.append(OBB.from_bounds(f"lift_leadscrew{suf}", 12.0, yc - 4.0, 20.0, 20.0, yc + 4.0, tower_top, group="fixed", color="#334155"))
                carriage = OBB.from_bounds(f"lift_carriage{suf}", 12.0, yc - 38.0, 20.0 + lift - 10.0, 42.0, yc + 38.0, 20.0 + lift + 18.0, group="moving", color="#F59E0B")
                moving.append(carriage)
                allow_fixed_pairs.update({
                    (f"lift_carriage{suf}", f"lift_tower_rod_L{suf}"),
                    (f"lift_carriage{suf}", f"lift_tower_rod_R{suf}"),
                    (f"lift_carriage{suf}", f"lift_leadscrew{suf}"),
                    (f"lift_carriage{suf}", "base"),
                })
                allow_self_pairs.update({
                    (f"lift_carriage{suf}", "column"),
                    (f"lift_carriage{suf}", "column_left"),
                    (f"lift_carriage{suf}", "column_right"),
                    (f"lift_carriage{suf}", "x_arm"),
                })

        if include_extra:
            extra = _select_optimal_accessory_obb(fixed, moving, common)

        support_x = (min(0.0, shift_val - 45.0) if family == "root_single_rear" else 0.0, 315.0)
        return {
            "t": t, "fixed": fixed, "moving": moving, "extra": extra,
            "allow_self_pairs": allow_self_pairs, "allow_fixed_pairs": allow_fixed_pairs,
            "pivot_x_mm": 40.0 + shift, "pivot_z_mm": 20.0 + lift, "angle_deg": angle_deg,
            "reachable": True, "dof": 2 if is_lift_tower else 1, "pressure_angle_deg": 0.0,
            "drive_gain": 0.0, "workspace_coverage": ws_cov, "z_nozzle_range_mm": (z_min_n, z_max_n),
            "support_x_range": support_x,
        }

    if family == "scissor":
        arm_len = p["arm_length_mm"]
        arm_w = p.get("arm_width_mm", 20.0)
        arm_t = p.get("arm_thick_mm", 6.0)
        center_x = 157.5
        low_z = 24.0
        park_frac = min(1.0, max(0.0, t / 0.15))
        fold_frac = max(0.0, (t - 0.15) / 0.85)
        th_cx = center_x + (38.0 - center_x) * park_frac
        height = p["height_work_max_mm"] + (p["height_fold_mm"] - p["height_work_max_mm"]) * fold_frac
        reachable = (height <= 2.0 * arm_len - 1.0) and (height > 0.0)
        span = math.sqrt(max(0.0, 4.0 * arm_len**2 - height**2))
        left_x = center_x - 0.5 * span
        right_x = center_x + 0.5 * span
        high_z = low_z + height

        fixed = _base_obbs(common)
        fixed.append(OBB.from_bounds("rail_L", 10.0, -145.0, 20.0, 305.0, -125.0, 28.0, group="fixed", color="#475569"))
        fixed.append(OBB.from_bounds("rail_R", 10.0, 125.0, 20.0, 305.0, 145.0, 28.0, group="fixed", color="#475569"))
        fixed.append(OBB.from_bounds("leadscrew_center", 15.0, -4.0, 20.0, 300.0, 4.0, 28.0, group="fixed", color="#334155"))

        moving = []
        for side, y_in, y_out in (("L", -125.0, -135.0), ("R", 125.0, 135.0)):
            moving.append(_make_beam_obb(f"scissor_a_{side}", np.array([left_x, y_in, low_z]), np.array([right_x, y_in, high_z]), arm_t, arm_w, color="#2563EB"))
            moving.append(_make_beam_obb(f"scissor_b_{side}", np.array([right_x, y_out, low_z]), np.array([left_x, y_out, high_z]), arm_t, arm_w, color="#0EA5E9"))
        moving.append(OBB.from_bounds("top_frame", center_x - 150.0, -145.0, high_z, center_x + 150.0, 145.0, high_z + p["frame_offset_mm"] - 4.0, group="moving", color="#1D4ED8"))
        moving.append(OBB.from_bounds("toolhead", th_cx - 25.0, -26.0, high_z - 35.0, th_cx + 25.0, 26.0, high_z, group="moving", color="#0369A1"))

        allow_self = {
            ("scissor_a_L", "top_frame"), ("scissor_b_L", "top_frame"),
            ("scissor_a_R", "top_frame"), ("scissor_b_R", "top_frame"),
            ("top_frame", "toolhead"),
        }
        allow_fixed = {
            ("scissor_a_L", "rail_L"), ("scissor_b_L", "rail_L"),
            ("scissor_a_R", "rail_R"), ("scissor_b_R", "rail_R"),
            ("scissor_a_L", "base"), ("scissor_b_L", "base"),
            ("scissor_a_R", "base"), ("scissor_b_R", "base"),
        }
        gain = abs(scissor_state(arm_len, span)["dH_dS"]) if reachable and span > 1e-6 else math.inf
        extra = _select_optimal_accessory_obb(fixed, moving, common) if include_extra else []
        return {
            "t": t, "fixed": fixed, "moving": moving, "extra": extra,
            "allow_self_pairs": allow_self, "allow_fixed_pairs": allow_fixed,
            "pivot_x_mm": center_x, "pivot_z_mm": high_z,
            "angle_deg": math.degrees(math.atan2(height, max(span, 1e-6))),
            "reachable": reachable, "dof": 1, "pressure_angle_deg": 0.0,
            "drive_gain": gain, "workspace_coverage": ws_cov, "z_nozzle_range_mm": (z_min_n, z_max_n),
            "support_x_range": (0.0, 315.0),
        }

    if family in {"telescope_2", "telescope_3"}:
        stages = 2 if family == "telescope_2" else 3
        overlap = p["overlap_mm"]
        outer_sz = p.get("outer_size_mm", 60.0 if stages == 3 else 52.0)
        wall = p.get("wall_mm", 3.0)
        clr = p.get("radial_clearance_mm", 0.08)
        pad = p.get("pad_thickness_mm", 2.92)
        side_motor = bool(p.get("motor_side_mounted", 1))
        step_size = 2.0 * (wall + clr + pad)
        extended = common["column_top_mm"] - common["column_bottom_mm"]
        stage_h = (extended + (stages - 1) * overlap) / stages
        cx = 40.0
        fixed = _base_obbs(common)
        moving = []
        s1_half = 0.5 * outer_sz
        fixed.append(OBB.from_bounds("stage_1_outer", cx - s1_half, -s1_half, 20.0, cx + s1_half, s1_half, 20.0 + stage_h, group="fixed", color="#475569"))
        if side_motor:
            fixed.append(OBB.from_bounds("z_motor_side", cx - 21.0, s1_half + 2.0, 20.0, cx + 21.0, s1_half + 44.0, 62.0, group="fixed", color="#334155"))
        top_z = 20.0 + stage_h
        for s in range(1, stages):
            sz = outer_sz - s * step_size
            sh = 0.5 * sz
            bottom = 20.0 + s * (stage_h - overlap) * (1.0 - t)
            top_z = bottom + stage_h
            moving.append(OBB.from_bounds(f"stage_{s+1}", cx - sh, -sh, bottom, cx + sh, sh, top_z, group="moving", color="#2563EB" if s == 1 else "#0EA5E9"))
        moving.extend(_x_arm_and_toolhead(common, attach_x=cx + s1_half + 2.0, attach_z=top_z - 35.0))
        if not side_motor:
            moving.append(OBB.from_bounds("z_motor_cap", cx - 21.0, -21.0, top_z, cx + 21.0, 21.0, top_z + 34.0, group="moving", color="#334155"))
        allow_fixed = {("stage_2", "stage_1_outer"), ("stage_3", "stage_1_outer"), ("stage_2", "base"), ("stage_3", "base")}
        allow_self = {("stage_2", "stage_3"), ("stage_3", "x_arm"), ("stage_3", "z_motor_cap"), ("x_arm", "toolhead")}
        extra = _select_optimal_accessory_obb(fixed, moving, common) if include_extra else []
        return {
            "t": t, "fixed": fixed, "moving": moving, "extra": extra,
            "allow_self_pairs": allow_self, "allow_fixed_pairs": allow_fixed,
            "pivot_x_mm": cx, "pivot_z_mm": 20.0, "angle_deg": 0.0,
            "reachable": True, "dof": 1, "pressure_angle_deg": 0.0,
            "drive_gain": 0.0, "workspace_coverage": ws_cov, "z_nozzle_range_mm": (z_min_n, z_max_n),
            "support_x_range": (0.0, 315.0),
        }

    raise ValueError(f"Unsupported family: {family}")


def _get_obb(state: dict[str, Any], group_key: str, name: str) -> OBB:
    for o in state[group_key]:
        if o.name == name:
            return o
    raise KeyError(f"OBB {name} not found in {group_key}")


def get_certified_trajectory(
    spec: dict[str, Any],
    part_name: str,
    group_key: str,
    ta: float,
    tb: float,
    parameters: dict[str, Any] | None = None,
) -> BoundedTrajectory:
    """Return a mathematically certified BoundedTrajectory for part_name over phase interval [ta, tb]."""
    if parameters is not None:
        spec = dict(spec)
        spec["parameters"] = dict(spec["parameters"], **parameters)
    p = spec["parameters"]
    family = spec["family"]
    s0 = build_state_at_t(spec, 0.0, include_extra=False)
    obb0 = _get_obb(s0, group_key, part_name)

    if group_key == "fixed":
        return StaticTrajectory(obb0)

    def pose_fn(t: float) -> OBB:
        return _get_obb(build_state_at_t(spec, t, include_extra=False), group_key, part_name)

    if family in {"root_single_lift", "root_double_lift", "root_single_rear"}:
        lift_val = abs(float(p.get("lift_mm", 0.0)))
        shift_val = abs(float(p.get("shift_x_mm", 0.0)))
        fold_rad = abs(math.radians(float(p["fold_angle_deg"])))
        arm_fold_enabled = bool(p.get("arm_fold_enabled", 1))
        r_obb = obb0.bounding_radius

        if arm_fold_enabled:
            if tb <= 0.20 + 1e-9:
                if part_name in {"x_arm", "toolhead"}:
                    hinge = np.array([55.0, 0.0, 295.0], dtype=float)
                    d_hinge = float(np.linalg.norm(obb0.center - hinge))
                    omega = (0.5 * math.pi) / 0.20
                    return LipschitzTrajectory(pose_fn, d_hinge * omega, omega, r_obb, "ArmFold(0..0.20)")
                return LipschitzTrajectory(pose_fn, 0.0, 0.0, r_obb, "Resting(0..0.20)")
            if tb <= 0.45 + 1e-9:
                if "lift_carriage" in part_name:
                    v_lift = (0.5 * math.pi / 0.20) * lift_val
                    return LipschitzTrajectory(pose_fn, v_lift, 0.0, r_obb, "CarriageLift(0.20..0.45)")
                v_lift = (0.5 * math.pi / 0.20) * lift_val
                v_shift = (0.5 * math.pi / 0.17) * shift_val if tb > 0.28 + 1e-9 else 0.0
                return LipschitzTrajectory(pose_fn, math.hypot(v_lift, v_shift), 0.0, r_obb, "LiftShift(0.20..0.45)")
            if tb <= 0.95 + 1e-9:
                if "lift_carriage" in part_name:
                    return LipschitzTrajectory(pose_fn, 0.0, 0.0, r_obb, "CarriageHold(0.45..0.95)")
                pivot0 = np.array([40.0, 0.0, 20.0], dtype=float)
                s_pre = build_state_at_t(spec, 0.45, include_extra=False)
                obb_pre = _get_obb(s_pre, group_key, part_name)
                d_piv = float(np.linalg.norm(obb_pre.center - (pivot0 + np.array([p.get("shift_x_mm", 0.0), 0.0, p.get("lift_mm", 0.0)]))))
                omega = fold_rad / 0.50
                return LipschitzTrajectory(pose_fn, d_piv * omega, omega, r_obb, "RootFold(0.45..0.95)")
            return LipschitzTrajectory(pose_fn, 0.0, 0.0, r_obb, "FoldedHold(0.95..1.0)")

    if family == "scissor":
        arm_len = float(p["arm_length_mm"])
        h_max = float(p["height_work_max_mm"])
        h_fold = float(p["height_fold_mm"])
        r_obb = obb0.bounding_radius
        if tb <= 0.15 + 1e-9:
            if part_name == "toolhead":
                v_park = abs(38.0 - 157.5) / 0.15
                return LipschitzTrajectory(pose_fn, v_park, 0.0, r_obb, "ToolheadPark(0..0.15)")
            return LipschitzTrajectory(pose_fn, 0.0, 0.0, r_obb, "ScissorHold(0..0.15)")
        dH_dt = abs(h_max - h_fold) / 0.85
        if part_name in {"top_frame", "toolhead"}:
            return LipschitzTrajectory(pose_fn, dH_dt, 0.0, r_obb, "ScissorTopZ(0.15..1.0)")

        def scissor_arm_bound(sub_a: float, sub_b: float) -> float:
            frac_a = max(0.0, (sub_a - 0.15) / 0.85)
            h_a = h_max + (h_fold - h_max) * frac_a
            s_a = max(1e-3, math.sqrt(max(1e-6, 4.0 * arm_len**2 - h_a**2)))
            omega_max = dH_dt / s_a
            v_center_max = 0.5 * dH_dt
            return (v_center_max + r_obb * omega_max) * 0.5 * abs(sub_b - sub_a)

        return IntervalBoundTrajectory(pose_fn, scissor_arm_bound, "ScissorArmAnalytical(0.15..1.0)")

    if family in {"telescope_2", "telescope_3"}:
        stages = 2 if family == "telescope_2" else 3
        overlap = float(p["overlap_mm"])
        extended = float(spec["common"]["column_top_mm"] - spec["common"]["column_bottom_mm"])
        stage_h = (extended + (stages - 1) * overlap) / stages
        v_max = (stages - 1) * abs(stage_h - overlap)
        return LipschitzTrajectory(pose_fn, v_max, 0.0, obb0.bounding_radius, "TelescopicZ(0..1)")

    raise ValueError(f"No certified analytical trajectory defined for {family}/{part_name}")


def build_trace_3d(spec: dict[str, Any], parameters: dict[str, Any] | None = None, steps: int = 31) -> list[dict[str, Any]]:
    return [build_state_at_t(spec, i / (steps - 1), parameters=parameters, include_extra=(i == steps - 1)) for i in range(steps)]
