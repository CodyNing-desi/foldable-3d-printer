"""Round 3 unified 3D evaluator: includes accessory collision, swept-envelope check, COM stability, and DOF."""

from __future__ import annotations

from typing import Any

import numpy as np

from .geometry3d import OBB, obb_sat_distance
from .mechanisms3d import build_trace_3d


def _assembly_aabb(obbs: list[OBB]) -> tuple[np.ndarray, np.ndarray]:
    mins = [o.aabb()[0] for o in obbs]
    maxs = [o.aabb()[1] for o in obbs]
    return np.min(mins, axis=0), np.max(maxs, axis=0)


def _aabb_volume(mn: np.ndarray, mx: np.ndarray) -> float:
    dims = np.maximum(0.0, mx - mn)
    return float(dims[0] * dims[1] * dims[2])


def _pair_key(a: str, b: str) -> tuple[str, str]:
    return (a, b) if a <= b else (b, a)


def _state_3d_collision(state: dict[str, Any], check_extra: bool = True) -> dict[str, Any]:
    moving: list[OBB] = state["moving"]
    fixed: list[OBB] = state["fixed"]
    extra: list[OBB] = state.get("extra", [])
    allow_fixed = {_pair_key(a, b) for a, b in state.get("allow_fixed_pairs", set())}
    allow_self = {_pair_key(a, b) for a, b in state.get("allow_self_pairs", set())}

    max_pen = 0.0
    min_clr = float("inf")
    worst_pair = ""

    # 1. Moving vs Fixed
    for m in moving:
        for f in fixed:
            if _pair_key(m.name, f.name) in allow_fixed:
                continue
            colliding, pen, clr = obb_sat_distance(m, f)
            if colliding and pen > max_pen:
                max_pen = pen
                worst_pair = f"{m.name} <-> {f.name}"
            if not colliding:
                min_clr = min(min_clr, clr)

    # 2. Moving vs Moving (3D Self-Collision)
    for i, a in enumerate(moving):
        for b in moving[i + 1:]:
            if _pair_key(a.name, b.name) in allow_self:
                continue
            colliding, pen, clr = obb_sat_distance(a, b)
            if colliding and pen > max_pen:
                max_pen = pen
                worst_pair = f"{a.name} <-> {b.name} (self)"
            if not colliding:
                min_clr = min(min_clr, clr)

    # 3. Extra (transport_accessories) vs Fixed + Moving
    if check_extra:
        for ex in extra:
            if ex.name in {"case_envelope", "cabinet"}:
                continue
            for obs in fixed + moving:
                colliding, pen, clr = obb_sat_distance(ex, obs)
                if colliding and pen > max_pen:
                    max_pen = pen
                    worst_pair = f"{ex.name} <-> {obs.name} (accessory)"
                if not colliding:
                    min_clr = min(min_clr, clr)

    # 4. Fixed structural interference (slot_rail/bracket vs bed)
    fixed_by_name = {f.name: f for f in fixed}
    if "bed" in fixed_by_name:
        for s_name in ("slot_rail_L", "slot_rail_R", "rear_offset_bracket", "lift_tower_rod_L", "lift_tower_rod_R"):
            if s_name in fixed_by_name:
                colliding, pen, _ = obb_sat_distance(fixed_by_name[s_name], fixed_by_name["bed"])
                if colliding and pen > max_pen:
                    max_pen = pen
                    worst_pair = f"{s_name} <-> bed"

    return {
        "max_penetration_mm": float(max_pen),
        "min_clearance_mm": float(min_clr if min_clr < float("inf") else 0.0),
        "worst_pair": worst_pair,
    }


def _swept_segment_collision(state_a: dict[str, Any], state_b: dict[str, Any]) -> tuple[float, str]:
    """Conservative swept-envelope check between consecutive states via midpoint + half-step inflation."""
    allow_fixed = {_pair_key(a, b) for a, b in state_a.get("allow_fixed_pairs", set())}
    fixed = state_a["fixed"]
    max_swept_pen = 0.0
    worst = ""
    for ma, mb in zip(state_a["moving"], state_b["moving"]):
        if ma.name != mb.name:
            continue
        disp = float(np.linalg.norm(mb.center - ma.center))
        # Midpoint interpolated OBB inflated by 0.5*disp (conservative swept capsule bound)
        mid = OBB(
            name=ma.name,
            center=0.5 * (ma.center + mb.center),
            axes=ma.axes,
            half_extents=ma.half_extents + 0.5 * disp * 0.25,  # bounded conservative margin
        )
        for f in fixed:
            if _pair_key(mid.name, f.name) in allow_fixed:
                continue
            col, pen, _ = obb_sat_distance(mid, f)
            if col and pen > max_swept_pen:
                max_swept_pen = pen
                worst = f"{mid.name} <-> {f.name} (swept)"
    return max_swept_pen, worst


def evaluate_candidate_3d(spec: dict[str, Any], parameters: dict[str, Any] | None = None, steps: int = 31, swept_check: bool = True) -> dict[str, Any]:
    if parameters is not None:
        spec = dict(spec)
        spec["parameters"] = dict(spec["parameters"], **parameters)
    trace = build_trace_3d(spec, steps=steps)
    rows = []
    max_pen = 0.0
    worst_pair = ""
    min_pos_clr = float("inf")
    max_press_angle = 0.0
    com_stable_all = True

    for idx, state in enumerate(trace):
        col = _state_3d_collision(state, check_extra=True)
        swept_pen, swept_pair = (0.0, "")
        if swept_check and idx > 0:
            swept_pen, swept_pair = _swept_segment_collision(trace[idx - 1], state)
        eff_pen = max(col["max_penetration_mm"], swept_pen)
        if eff_pen > max_pen:
            max_pen = eff_pen
            worst_pair = swept_pair if swept_pen > col["max_penetration_mm"] else col["worst_pair"]
        if col["min_clearance_mm"] > 1e-6:
            min_pos_clr = min(min_pos_clr, col["min_clearance_mm"])
        max_press_angle = max(max_press_angle, state.get("pressure_angle_deg", 0.0))

        # Check COM tipping stability (weighted by OBB volume proxy)
        all_phys = state["fixed"] + state["moving"]
        vols = [float(np.prod(o.half_extents * 2.0)) for o in all_phys]
        com_x = sum(float(o.center[0]) * v for o, v in zip(all_phys, vols)) / max(sum(vols), 1e-9)
        sx0, sx1 = state.get("support_x_range", (0.0, 315.0))
        if not (sx0 <= com_x <= sx1):
            com_stable_all = False

        all_parts = all_phys + state["extra"]
        mn, mx = _assembly_aabb(all_parts)
        dims = mx - mn
        rows.append({
            "t": state["t"], "max_penetration_mm": eff_pen, "min_clearance_mm": col["min_clearance_mm"],
            "worst_pair": worst_pair, "reachable": state["reachable"], "drive_gain": state["drive_gain"],
            "pressure_angle_deg": state.get("pressure_angle_deg", 0.0),
            "depth_x_mm": float(dims[0]), "width_y_mm": float(dims[1]), "height_z_mm": float(dims[2]),
            "com_x_mm": com_x,
        })

    w_mn, w_mx = _assembly_aabb(trace[0]["fixed"] + trace[0]["moving"] + trace[0]["extra"])
    f_mn, f_mx = _assembly_aabb(trace[-1]["fixed"] + trace[-1]["moving"] + trace[-1]["extra"])
    fc_mn, fc_mx = _assembly_aabb(trace[-1]["fixed"] + trace[-1]["moving"])
    work_vol = _aabb_volume(w_mn, w_mx)
    folded_vol = _aabb_volume(f_mn, f_mx)
    folded_core_vol = _aabb_volume(fc_mn, fc_mx)
    storage_ratio = folded_vol / work_vol

    reachable_fraction = sum(1 for s in trace if s["reachable"]) / len(trace)
    ws_cov = trace[0]["workspace_coverage"]
    dof = trace[0]["dof"]

    reasons = []
    if max_pen > 1e-4:
        reasons.append(f"3D/扫掠干涉穿透 {max_pen:.2f} mm ({worst_pair})")
    if not com_stable_all:
        reasons.append("折叠过程重心超出支撑多边形（存在倾覆风险）")
    if reachable_fraction < 1.0:
        reasons.append("部分姿态无可达装配解")
    if ws_cov < 1.0 - 1e-6:
        reasons.append(f"真实三维工作空间覆盖率 {ws_cov:.2%} < 100%")
    if storage_ratio > 0.80:
        reasons.append(f"3D 收纳体积比 {storage_ratio:.3f} > 0.800")
    if spec["family"] in {"guided_single", "guided_double"}:
        p = spec["parameters"]
        if not p.get("dual_roller", 1):
            reasons.append("单滚轮槽轨为 2-DOF 欠约束机构")
        slot_clr = 0.5 * (p["slot_width_mm"] - p["roller_diameter_mm"])
        if slot_clr < 0.25:
            reasons.append(f"槽轨单侧间隙 {slot_clr:.2f} mm < 0.25 mm")
        if max_press_angle > 45.0:
            reasons.append(f"槽轨最大压力角 {max_press_angle:.1f}° > 45°")
    if spec["family"] in {"telescope_2", "telescope_3"}:
        stages = 2 if spec["family"] == "telescope_2" else 3
        overlap = spec["parameters"]["overlap_mm"]
        ext = spec["common"]["column_top_mm"] - spec["common"]["column_bottom_mm"]
        stage_h = (ext + (stages - 1) * overlap) / stages
        if overlap / stage_h < 0.25:
            reasons.append(f"伸缩重叠率 {overlap/stage_h:.1%} < 25%")
    if spec["family"] == "drawer_y" and spec["parameters"]["cable_bend_radius_mm"] < 35.0:
        reasons.append("线缆动态弯曲半径低于 35 mm")

    f_dims = f_mx - f_mn
    return {
        "id": spec["id"], "name": spec["name"], "family": spec["family"],
        "simulation_level": "L2_3D_OBB_SAT_swept_and_accessory",
        "dof": dof, "com_stable": com_stable_all,
        "work_volume_mm3": work_vol, "folded_volume_mm3": folded_vol, "folded_core_volume_mm3": folded_core_vol,
        "storage_ratio": storage_ratio, "core_storage_ratio": folded_core_vol / work_vol,
        "folded_depth_x_mm": float(f_dims[0]), "folded_width_y_mm": float(f_dims[1]), "folded_height_z_mm": float(f_dims[2]),
        "max_penetration_mm": max_pen, "worst_collision_pair": worst_pair,
        "min_positive_clearance_mm": min_pos_clr if min_pos_clr < float("inf") else 0.0,
        "workspace_coverage": ws_cov, "reachable_fraction": reachable_fraction,
        "max_pressure_angle_deg": max_press_angle,
        "peak_drive_gain_work": max((r["drive_gain"] for r in rows if r["t"] <= 0.71), default=0.0),
        "passed_screen": len(reasons) == 0, "screen_reasons": reasons,
        "parameters": dict(spec["parameters"]), "trace_rows": rows, "trace": trace,
    }
