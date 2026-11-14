"""Round 3 high-fidelity 3D mechanism kinematics, continuous trajectories, and optimal accessory placement."""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from .geometry3d import OBB, obb_sat_distance, rot_y


def scissor_state(arm_length_mm: float, horizontal_span_mm: float) -> dict[str, float]:
    height_squared = 4.0 * arm_length_mm**2 - horizontal_span_mm**2
    if height_squared <= 0.0:
        raise ValueError("Scissor geometry is outside its reachable range")
    height = math.sqrt(height_squared)
    theta = math.atan2(height, horizontal_span_mm)
    return {
        "height_mm": height,
        "dH_dS": -horizontal_span_mm / height,
        "theta_rad": theta,
        "theta_deg": math.degrees(theta),
    }


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


def _x_arm_and_toolhead(common: dict[str, Any], attach_x: float, attach_z: float, arm_fold_deg: float = 0.0, th_x_local: float = 85.0) -> list[OBB]:
    arm_len = common["x_arm_length_mm"]
    wy = common["x_arm_width_y_mm"] / 2.0
    hz = common["x_arm_height_z_mm"] / 2.0
    arm = OBB.from_bounds(
        "x_arm", attach_x, -wy, attach_z - hz, attach_x + arm_len, wy, attach_z + hz,
        group="moving", color="#0284C7",
    )
    th_x0 = attach_x + th_x_local
    th_x1 = th_x0 + common["toolhead_x_mm"]
    th_y = common["toolhead_y_mm"] / 2.0
    th = OBB.from_bounds(
        "toolhead", th_x0, -th_y, attach_z - common["toolhead_z_mm"], th_x1, th_y, attach_z,
        group="moving", color="#0369A1",
    )
    if abs(arm_fold_deg) > 1e-6:
        R = rot_y(-arm_fold_deg)
        origin = np.array([attach_x, 0.0, attach_z], dtype=float)
        arm = arm.transformed(rotation=R, origin=origin)
        th = th.transformed(rotation=R, origin=origin)
    return [arm, th]


def _phase_lift_fold(t: float, lift: float, shift: float, arm_fold_enabled: bool) -> tuple[float, float, float, float]:
    if arm_fold_enabled:
        arm_frac = min(1.0, t / 0.2)
        lift_t = min(1.0, max(0.0, (t - 0.2) / 0.20))
        shift_t = min(1.0, max(0.0, (t - 0.28) / 0.17))
        fold_frac = min(1.0, max(0.0, (t - 0.45) / 0.50))
        lift_frac = 0.5 - 0.5 * math.cos(math.pi * lift_t)
        shift_frac = 0.5 - 0.5 * math.cos(math.pi * shift_t)
        return lift * lift_frac, shift * shift_frac, fold_frac, arm_frac
    else:
        arm_frac = 0.0
        lift_t = min(1.0, t / 0.25)
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
    """Find collision-free 200x200x70 mm accessory placement minimizing total 3D transport AABB volume."""
    ax, ay, az = common["accessory_x_mm"], common["accessory_y_mm"], common["accessory_z_mm"]
    obstacles = fixed + moving
    # Compute base+moving AABB to propose smart candidate zones
    pts = np.vstack([o.corners() for o in obstacles])
    mn, mx = np.min(pts, axis=0), np.max(pts, axis=0)

    candidates = [
        # 1. Above bed (between bed top z=62 and folded column, or beside column)
        OBB.from_bounds("transport_accessories", 65.0, -0.5 * ay, 62.0, 65.0 + ax, 0.5 * ay, 62.0 + az, group="extra", color="#F59E0B"),
        # 2. Above base front-right
        OBB.from_bounds("transport_accessories", 110.0, -0.5 * ay, 62.0, 110.0 + ax, 0.5 * ay, 62.0 + az, group="extra", color="#F59E0B"),
        # 3. Right of base (Round 1/2 default)
        OBB.from_bounds("transport_accessories", mx[0] + 2.0, -0.5 * ay, 0.0, mx[0] + 2.0 + ax, 0.5 * ay, az, group="extra", color="#F59E0B"),
        # 4. Beside base in +Y
        OBB.from_bounds("transport_accessories", 55.0, mx[1] + 2.0, 0.0, 55.0 + ax, mx[1] + 2.0 + ay, az, group="extra", color="#F59E0B"),
        # 5. Beside base in -Y
        OBB.from_bounds("transport_accessories", 55.0, mn[1] - 2.0 - ay, 0.0, 55.0 + ax, mn[1] - 2.0, az, group="extra", color="#F59E0B"),
        # 6. Rear of base
        OBB.from_bounds("transport_accessories", mn[0] - 2.0 - ax, -0.5 * ay, 0.0, mn[0] - 2.0, 0.5 * ay, az, group="extra", color="#F59E0B"),
    ]

    best_obb = None
    best_vol = float("inf")
    for cand in candidates:
        collides = any(obb_sat_distance(cand, obs)[0] for obs in obstacles)
        if not collides:
            c_pts = np.vstack([pts, cand.corners()])
            dims = np.max(c_pts, axis=0) - np.min(c_pts, axis=0)
            vol = float(dims[0] * dims[1] * dims[2])
            if vol < best_vol:
                best_vol = vol
                best_obb = cand
    if best_obb is None:
        # Fallback: right of max_x guaranteed non-overlapping
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
    if family == "arm_fold":
        arm_len = p["arm_length_mm"]
        xy_cov = min(1.0, max(0.0, (arm_len - 20.0) / common["target_print_x_mm"]))
        z_travel = (common["column_top_mm"] - 75.0) - bed_top
        return xy_cov * min(1.0, max(0.0, z_travel / target_h)), bed_top, bed_top + z_travel
    z_max_nozzle = common["column_top_mm"] - 75.0
    usable = max(0.0, min(target_h, z_max_nozzle - bed_top))
    return usable / target_h, bed_top, z_max_nozzle


def build_trace_3d(spec: dict[str, Any], parameters: dict[str, Any] | None = None, steps: int = 31) -> list[dict[str, Any]]:
    if parameters is not None:
        spec = dict(spec)
        spec["parameters"] = dict(spec["parameters"], **parameters)
    common = spec["common"]
    p = spec["parameters"]
    family = spec["family"]
    ws_cov, z_min_n, z_max_n = _evaluate_workspace_z(spec, p)
    trace: list[dict[str, Any]] = []

    if family in {"root_single", "root_single_lift", "root_single_rear", "root_double", "root_double_lift", "guided_single", "guided_double", "case_linked", "external_combo"}:
        is_double = family in {"root_double", "root_double_lift", "guided_double", "external_combo"}
        is_guided = family in {"guided_single", "guided_double"}
        is_lift_tower = family in {"root_single_lift", "root_double_lift"}
        is_rear = family == "root_single_rear"
        is_case = family == "case_linked"
        is_ext_combo = family == "external_combo"
        arm_fold_enabled = bool(p.get("arm_fold_enabled", 1 if family in {"root_single_lift", "root_single_rear", "guided_single"} else 0))

        lift_val = p.get("lift_mm", 0.0)
        shift_val = p.get("shift_x_mm", 0.0)
        pivot0 = np.array([40.0, 0.0, 20.0], dtype=float)
        direction = 1.0 if is_rear else -1.0

        pivot_path = []
        for i in range(steps):
            t = i / (steps - 1)
            lf, sf, _, _ = _phase_lift_fold(t, lift_val, shift_val, arm_fold_enabled)
            pivot_path.append((40.0 + sf, 20.0 + lf))

        for i in range(steps):
            t = i / (steps - 1)
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
                # Toolhead parks continuously in Y to side (-105) if double lift
                th_y_ctr = -105.0 * min(1.0, t / 0.2) if is_lift_tower else 0.0
                th = OBB.from_bounds("toolhead", 55.0, th_y_ctr - 26.0, 275.0, 105.0, th_y_ctr + 26.0, 335.0, group="moving", color="#0369A1")
                base_moving = [col_l, col_r, cross, th]
                allow_self_pairs.update({("column_left", "crossbar"), ("column_right", "crossbar"), ("crossbar", "toolhead"), ("column_left", "toolhead")})
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

            if is_rear:
                bx0 = min(0.0, shift_val - 20.0)
                fixed.append(OBB.from_bounds("rear_offset_bracket", bx0, -32.0, 0.0, 25.0, 32.0, 20.0 + lift_val + 12.0, group="fixed", color="#475569"))
                fixed.append(OBB.from_bounds("rear_support_foot", bx0 - 25.0, -45.0, 0.0, bx0, 45.0, 15.0, group="fixed", color="#334155"))
                allow_fixed_pairs.update({("column", "rear_offset_bracket"), ("x_arm", "rear_offset_bracket")})

            pressure_angle_deg = 0.0
            dof = 2 if is_lift_tower else 1
            if is_guided:
                dual = bool(p.get("dual_roller", 1))
                dof = 1 if dual else 2
                slot_w = p["slot_width_mm"]
                r_dia = p["roller_diameter_mm"]
                r_space = p.get("roller_spacing_mm", 40.0)
                slot_x0 = min(x for x, _ in pivot_path) - slot_w / 2.0
                slot_x1 = max(x for x, _ in pivot_path) + slot_w / 2.0
                slot_z0 = min(z for _, z in pivot_path) - slot_w / 2.0
                slot_z1 = max(z for _, z in pivot_path) + slot_w / 2.0
                fixed.append(OBB.from_bounds("slot_rail_L", slot_x0, -32.0, slot_z0, slot_x1, -22.0, slot_z1, group="fixed", color="#D97706"))
                fixed.append(OBB.from_bounds("slot_rail_R", slot_x0, 22.0, slot_z0, slot_x1, 32.0, slot_z1, group="fixed", color="#D97706"))
                px, pz = pivot_path[i]
                moving.append(OBB.from_bounds("roller_1", px - r_dia / 2, -33.0, pz - r_dia / 2, px + r_dia / 2, 33.0, pz + r_dia / 2, group="moving", color="#B45309"))
                allow_fixed_pairs.update({("roller_1", "slot_rail_L"), ("roller_1", "slot_rail_R"), ("column", "slot_rail_L"), ("column", "slot_rail_R")})
                allow_self_pairs.update({("roller_1", "column")})
                if dual:
                    p2 = np.array([40.0, 0.0, 20.0 + r_space])
                    p2_w = np.array([40.0, 0.0, 20.0]) + R_col @ (p2 - np.array([40.0, 0.0, 20.0])) + trans_col
                    moving.append(OBB.from_bounds("roller_2", p2_w[0] - r_dia / 2, -33.0, p2_w[2] - r_dia / 2, p2_w[0] + r_dia / 2, 33.0, p2_w[2] + r_dia / 2, group="moving", color="#B45309"))
                    allow_fixed_pairs.update({("roller_2", "slot_rail_L"), ("roller_2", "slot_rail_R")})
                    allow_self_pairs.update({("roller_2", "column")})
                if i > 0:
                    dx = pivot_path[i][0] - pivot_path[i - 1][0]
                    dz = pivot_path[i][1] - pivot_path[i - 1][1]
                    if abs(dx) + abs(dz) > 1e-6:
                        pressure_angle_deg = math.degrees(math.atan2(abs(dx), abs(dz)))

            if is_case:
                wall = p["case_wall_mm"]
                wy = common["base_width_y_mm"] / 2.0 + wall
                extra.append(OBB.from_bounds("case_envelope", -wall, -wy, -wall, 315.0 + wall, wy, 365.0 + wall, group="extra", color="#F59E0B"))
            elif is_ext_combo and i == steps - 1:
                clr = p["cabinet_clearance_mm"]
                wy = common["base_width_y_mm"] / 2.0 + clr
                extra.append(OBB.from_bounds("cabinet", -100.0, -wy, -clr, 350.0, wy, 450.0, group="extra", color="#F59E0B"))
            elif i == steps - 1:
                extra = _select_optimal_accessory_obb(fixed, moving, common)

            support_x = (min(0.0, shift_val - 45.0) if is_rear else 0.0, 315.0)
            trace.append({
                "t": t, "fixed": fixed, "moving": moving, "extra": extra,
                "allow_self_pairs": allow_self_pairs, "allow_fixed_pairs": allow_fixed_pairs,
                "pivot_x_mm": pivot_path[i][0], "pivot_z_mm": pivot_path[i][1], "angle_deg": angle_deg,
                "reachable": True, "dof": dof, "pressure_angle_deg": pressure_angle_deg,
                "drive_gain": 0.0, "workspace_coverage": ws_cov, "z_nozzle_range_mm": (z_min_n, z_max_n),
                "support_x_range": support_x,
            })

    elif family in {"telescope_2", "telescope_3"}:
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
        for i in range(steps):
            t = i / (steps - 1)
            fixed = _base_obbs(common)
            moving: list[OBB] = []
            extra: list[OBB] = []
            s1_half = 0.5 * outer_sz
            s1_in = s1_half - wall
            fixed.append(OBB.from_bounds(
                "stage_1_outer", cx - s1_half, -s1_half, 20.0, cx + s1_half, s1_half, 20.0 + stage_h,
                group="fixed", color="#475569", hollow_inner_half=(s1_in, s1_in),
            ))
            if side_motor:
                fixed.append(OBB.from_bounds("z_motor_side", cx - 21.0, s1_half + 2.0, 20.0, cx + 21.0, s1_half + 44.0, 62.0, group="fixed", color="#334155"))
            top_z = 20.0 + stage_h
            for s in range(1, stages):
                sz = outer_sz - s * step_size
                sh = 0.5 * sz
                s_in = sh - wall
                bottom = 20.0 + s * (stage_h - overlap) * (1.0 - t)
                top_z = bottom + stage_h
                moving.append(OBB.from_bounds(
                    f"stage_{s+1}", cx - sh, -sh, bottom, cx + sh, sh, top_z,
                    group="moving", color="#2563EB" if s == 1 else "#0EA5E9",
                    hollow_inner_half=(s_in, s_in),
                ))
            arm_z = top_z - 35.0
            arm_parts = _x_arm_and_toolhead(common, attach_x=cx + s1_half + 2.0, attach_z=arm_z)
            moving.extend(arm_parts)
            if not side_motor:
                moving.append(OBB.from_bounds("z_motor_cap", cx - 21.0, -21.0, top_z, cx + 21.0, 21.0, top_z + 34.0, group="moving", color="#334155"))
            allow_fixed = {("stage_2", "stage_1_outer"), ("stage_3", "stage_1_outer"), ("stage_2", "base"), ("stage_3", "base")}
            allow_self = {("stage_2", "stage_3"), ("stage_3", "x_arm"), ("stage_3", "z_motor_cap"), ("x_arm", "toolhead")}
            if i == steps - 1:
                extra = _select_optimal_accessory_obb(fixed, moving, common)
            trace.append({
                "t": t, "fixed": fixed, "moving": moving, "extra": extra,
                "allow_self_pairs": allow_self, "allow_fixed_pairs": allow_fixed,
                "pivot_x_mm": cx, "pivot_z_mm": 20.0, "angle_deg": 0.0,
                "reachable": True, "dof": 1, "pressure_angle_deg": 0.0,
                "drive_gain": 0.0, "workspace_coverage": ws_cov, "z_nozzle_range_mm": (z_min_n, z_max_n),
                "support_x_range": (0.0, 315.0),
            })

    elif family == "scissor":
        arm_len = p["arm_length_mm"]
        arm_w = p.get("arm_width_mm", 20.0)
        arm_t = p.get("arm_thick_mm", 6.0)
        center_x = 157.5
        low_z = 24.0
        for i in range(steps):
            t = i / (steps - 1)
            # Continuous 2-phase trajectory:
            # Phase 1 (t in [0, 0.15]): toolhead slides continuously from center_x (157.5) to off-bed park (38.0)
            # Phase 2 (t in [0.15, 1.0]): scissor lowers continuously from height_work_max to height_fold
            park_frac = min(1.0, t / 0.15)
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
            extra = _select_optimal_accessory_obb(fixed, moving, common) if i == steps - 1 else []
            trace.append({
                "t": t, "fixed": fixed, "moving": moving, "extra": extra,
                "allow_self_pairs": allow_self, "allow_fixed_pairs": allow_fixed,
                "pivot_x_mm": center_x, "pivot_z_mm": high_z,
                "angle_deg": math.degrees(math.atan2(height, max(span, 1e-6))),
                "reachable": reachable, "dof": 1, "pressure_angle_deg": 0.0,
                "drive_gain": gain, "workspace_coverage": ws_cov, "z_nozzle_range_mm": (z_min_n, z_max_n),
                "support_x_range": (0.0, 315.0),
            })

    elif family == "arm_fold":
        arm_len = p["arm_length_mm"]
        for i in range(steps):
            t = i / (steps - 1)
            angle = p["fold_angle_deg"] * t
            fixed = _base_obbs(common) + [OBB.from_bounds("column", 25.0, -20.0, 20.0, 55.0, 20.0, 365.0, group="fixed", color="#475569")]
            origin = np.array([55.0, 0.0, 300.0])
            R = rot_y(angle)
            arm = OBB.from_bounds("x_arm", 55.0, -16.0, 288.0, 55.0 + arm_len, 16.0, 312.0, group="moving", color="#0284C7").transformed(rotation=R, origin=origin)
            th = OBB.from_bounds("toolhead", 140.0, -26.0, 233.0, 190.0, 26.0, 288.0, group="moving", color="#0369A1").transformed(rotation=R, origin=origin)
            extra = _select_optimal_accessory_obb(fixed, [arm, th], common) if i == steps - 1 else []
            trace.append({
                "t": t, "fixed": fixed, "moving": [arm, th], "extra": extra,
                "allow_self_pairs": {("x_arm", "toolhead")}, "allow_fixed_pairs": {("x_arm", "column")},
                "pivot_x_mm": 55.0, "pivot_z_mm": 300.0, "angle_deg": -angle,
                "reachable": True, "dof": 1, "pressure_angle_deg": 0.0, "drive_gain": 0.0,
                "workspace_coverage": ws_cov, "z_nozzle_range_mm": (z_min_n, z_max_n),
                "support_x_range": (0.0, 315.0),
            })

    elif family == "external_flip":
        origin = np.array([-40.0, 0.0, 20.0])
        for i in range(steps):
            t = i / (steps - 1)
            angle = p["fold_angle_deg"] * t
            R = rot_y(angle)
            fixed = [OBB.from_bounds("wall", -70.0, -180.0, -30.0, -60.0, 180.0, 430.0, group="fixed", color="#475569")]
            parts = _base_obbs(common) + [OBB.from_bounds("column", 25.0, -20.0, 20.0, 55.0, 20.0, 365.0, group="moving", color="#2563EB")] + _x_arm_and_toolhead(common, 55.0, 295.0)
            moving = [m.transformed(rotation=R, origin=origin) for m in parts]
            for m in moving:
                m.group = "moving"
            extra = []
            if i == steps - 1:
                clr = p["cabinet_clearance_mm"]
                wy = common["base_width_y_mm"] / 2.0 + clr
                extra.append(OBB.from_bounds("cabinet", -70.0, -wy, -365.0 - clr, 350.0, wy, 100.0, group="extra", color="#F59E0B"))
            trace.append({
                "t": t, "fixed": fixed, "moving": moving, "extra": extra,
                "allow_self_pairs": {("base", "column"), ("column", "x_arm"), ("x_arm", "toolhead")}, "allow_fixed_pairs": set(),
                "pivot_x_mm": -40.0, "pivot_z_mm": 20.0, "angle_deg": -angle,
                "reachable": True, "dof": 1, "pressure_angle_deg": 0.0, "drive_gain": 0.0,
                "workspace_coverage": ws_cov, "z_nozzle_range_mm": (z_min_n, z_max_n),
                "support_x_range": (-70.0, 315.0),
            })

    elif family == "drawer_y":
        stroke = p["drawer_stroke_mm"]
        for i in range(steps):
            t = i / (steps - 1)
            offset = stroke * (1.0 - t)
            fixed = [
                OBB.from_bounds("base", 0.0, -173.5, 0.0, 315.0, 173.5, 20.0, group="fixed", color="#64748B"),
                OBB.from_bounds("column", 25.0, -20.0, 20.0, 55.0, 20.0, 365.0, group="fixed", color="#475569"),
            ] + _x_arm_and_toolhead(common, 55.0, 295.0)
            for f in fixed:
                f.group = "fixed"
            moving = [
                OBB.from_bounds("y_module", 70.0 + offset, -90.0, 40.0, 250.0 + offset, 90.0, 60.0, group="moving", color="#2563EB"),
                OBB.from_bounds("y_rail", 60.0 + offset, -60.0, 22.0, 270.0 + offset, 60.0, 40.0, group="moving", color="#0EA5E9"),
            ]
            extra = _select_optimal_accessory_obb(fixed, moving, common) if i == steps - 1 else []
            trace.append({
                "t": t, "fixed": fixed, "moving": moving, "extra": extra,
                "allow_self_pairs": {("y_module", "y_rail")}, "allow_fixed_pairs": {("y_rail", "base")},
                "pivot_x_mm": 160.0 + offset, "pivot_z_mm": 40.0, "angle_deg": 0.0,
                "reachable": True, "dof": 1, "pressure_angle_deg": 0.0, "drive_gain": 0.0,
                "workspace_coverage": ws_cov, "z_nozzle_range_mm": (z_min_n, z_max_n),
                "support_x_range": (0.0, 315.0),
            })

    return trace
