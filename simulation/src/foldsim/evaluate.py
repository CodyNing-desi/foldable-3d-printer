from shapely.ops import unary_union

from .mechanisms import build_trace


def _bounds(state, include_extra=True):
    parts = list(state["moving"].values()) + list(state["fixed"].values())
    if include_extra:
        parts += list(state["extra"].values())
    merged = unary_union(parts)
    return merged.bounds


def _volume(bounds, width_y_mm):
    min_x, min_z, max_x, max_z = bounds
    return (max_x - min_x) * (max_z - min_z) * width_y_mm


def _width_y(spec, folded=False):
    common = spec["common"]
    width = common["base_width_y_mm"]
    if spec["family"] == "case_linked":
        width += 2 * spec["parameters"]["case_wall_mm"]
    if folded and spec["family"] in {"external_flip", "external_combo"}:
        width += 2 * spec["parameters"]["cabinet_clearance_mm"]
    return width


def _intersection(state):
    total = 0.0
    minimum_clearance = float("inf")
    for moving_name, moving in state["moving"].items():
        for fixed_name, fixed in state["fixed"].items():
            if fixed_name == "slot_rail":
                continue
            intersection = moving.intersection(fixed).area
            total += intersection
            if intersection <= 1e-9:
                minimum_clearance = min(minimum_clearance, moving.distance(fixed))
    if "slot_rail" in state["fixed"] and "bed" in state["fixed"]:
        total += state["fixed"]["slot_rail"].intersection(state["fixed"]["bed"]).area
    if state["check_self_collision"]:
        items = list(state["moving"].items())
        for index, (name_a, polygon_a) in enumerate(items):
            if name_a == "lid_link":
                continue
            for name_b, polygon_b in items[index + 1:]:
                if name_b == "lid_link":
                    continue
                total += polygon_a.intersection(polygon_b).area
    return total, minimum_clearance


def evaluate_candidate(spec, parameters=None, steps=31):
    if parameters is not None:
        spec = dict(spec)
        spec["parameters"] = dict(spec["parameters"], **parameters)
    trace = build_trace(spec, steps=steps)
    rows = []
    for state in trace:
        intersection, clearance = _intersection(state)
        bounds = _bounds(state)
        rows.append({
            "t": state["t"],
            "pivot_x_mm": state["pivot_x_mm"],
            "pivot_z_mm": state["pivot_z_mm"],
            "angle_deg": state["angle_deg"],
            "intersection_area_mm2": intersection,
            "clearance_mm": clearance,
            "reachable": state["reachable"],
            "drive_gain": state["drive_gain"],
            "slot_side_clearance_mm": state["slot_side_clearance_mm"],
            "stow_angle_deg": state["stow_angle_deg"],
            "depth_mm": bounds[2] - bounds[0],
            "height_mm": bounds[3] - bounds[1],
        })
    work_bounds = _bounds(trace[0])
    folded_bounds = _bounds(trace[-1])
    folded_core_bounds = _bounds(trace[-1], include_extra=False)
    work_volume = _volume(work_bounds, _width_y(spec))
    folded_volume = _volume(folded_bounds, _width_y(spec, folded=True))
    folded_core_volume = _volume(folded_core_bounds, _width_y(spec))
    storage_ratio = folded_volume / work_volume
    reachable_fraction = sum(state["reachable"] for state in trace) / len(trace)
    workspace_coverage = 1.0
    if spec["family"] == "scissor":
        p = spec["parameters"]
        workspace_coverage = min(
            1.0,
            (p["height_work_max_mm"] - max(p["height_fold_mm"], p["height_work_max_mm"] - 180.0))
            / spec["common"]["target_print_height_mm"],
        )
    reasons = []
    max_intersection = max(row["intersection_area_mm2"] for row in rows)
    if max_intersection > 1e-6:
        reasons.append(f"轨迹最大穿透面积 {max_intersection:.3f} mm²")
    if reachable_fraction < 1.0:
        reasons.append("部分姿态无可达装配解")
    if workspace_coverage < 1.0 - 1e-9:
        reasons.append("有效工作空间不足 180 mm")
    if storage_ratio > 0.8:
        reasons.append(f"收纳体积比 {storage_ratio:.3f} 未达到 ≤0.800 初筛阈值")
    if spec["family"] in {"telescope_2", "telescope_3"}:
        stages = 2 if spec["family"] == "telescope_2" else 3
        overlap = spec["parameters"]["overlap_mm"]
        extended = spec["common"]["column_top_mm"] - spec["common"]["column_bottom_mm"]
        stage_height = (extended + (stages - 1) * overlap) / stages
        if overlap / stage_height < 0.25:
            reasons.append("伸缩重叠率低于 25%")
    if spec["family"] in {"guided_single", "guided_double"}:
        if min(state["slot_side_clearance_mm"] for state in trace) < 0.25:
            reasons.append("槽轨与滚轮单侧间隙低于 0.25 mm")
    if spec["family"] == "drawer_y" and spec["parameters"]["cable_bend_radius_mm"] < 35.0:
        reasons.append("线缆动态弯曲半径低于 35 mm")
    positive_clearances = [row["clearance_mm"] for row in rows if row["clearance_mm"] > 1e-6]
    result = {
        "id": spec["id"],
        "name": spec["name"],
        "family": spec["family"],
        "simulation_level": "L1_2.5D_rigid_geometry",
        "work_volume_mm3": work_volume,
        "folded_volume_mm3": folded_volume,
        "folded_core_volume_mm3": folded_core_volume,
        "storage_ratio": storage_ratio,
        "core_storage_ratio": folded_core_volume / work_volume,
        "folded_depth_mm": folded_bounds[2] - folded_bounds[0],
        "folded_height_mm": folded_bounds[3] - folded_bounds[1],
        "max_intersection_mm2": max_intersection,
        "min_positive_clearance_mm": min(positive_clearances, default=0.0),
        "workspace_coverage": workspace_coverage,
        "reachable_fraction": reachable_fraction,
        "peak_drive_gain_work": max(
            (row["drive_gain"] for row in rows if row["t"] <= 0.71), default=0.0,
        ),
        "passed_screen": not reasons,
        "screen_reasons": reasons,
        "parameters": dict(spec["parameters"] if parameters is None else dict(spec["parameters"], **parameters)),
        "trace_rows": rows,
        "trace": trace,
    }
    return result
