import math

from shapely.affinity import rotate, translate
from shapely.geometry import LineString, Point, box


def scissor_state(arm_length_mm, horizontal_span_mm):
    height_squared = 4 * arm_length_mm**2 - horizontal_span_mm**2
    if height_squared <= 0:
        raise ValueError("Scissor geometry is outside its reachable range")
    height = math.sqrt(height_squared)
    return {"height_mm": height, "dH_dS": -horizontal_span_mm / height}


def _base_parts(common):
    return {
        "base": box(0, 0, common["base_depth_x_mm"], common["base_height_mm"]),
        "bed": box(
            common["bed_x0_mm"], common["bed_z0_mm"],
            common["bed_x1_mm"], common["bed_z1_mm"],
        ),
    }


def _column(common):
    return box(
        common["column_x0_mm"], common["column_bottom_mm"],
        common["column_x1_mm"], common["column_top_mm"],
    )


def _gantry(common):
    return {
        "column_left": _column(common),
        "column_right": box(275, 20, 295, common["column_top_mm"]),
        "crossbar": box(30, 345, 295, common["column_top_mm"]),
    }


def _phase(t, lift, shift):
    phase = min(1.0, t / 0.2)
    lift_fraction = 0.5 - 0.5 * math.cos(math.pi * phase)
    fold_fraction = max(0.0, (t - 0.2) / 0.8)
    return lift * lift_fraction, shift * lift_fraction, fold_fraction


def _folded_parts(parts, pivot, lift, shift, angle, direction=-1):
    posed = {}
    for name, polygon in parts.items():
        turned = rotate(polygon, direction * angle, origin=pivot)
        posed[name] = translate(turned, xoff=shift, yoff=lift)
    return posed


def _state(
    t, moving, fixed, pivot, angle=0.0, reachable=True, extra=None, drive_gain=0.0,
    slot_side_clearance_mm=0.0, stow_angle_deg=0.0, check_self_collision=False,
):
    return {
        "t": t,
        "pivot_x_mm": pivot[0],
        "pivot_z_mm": pivot[1],
        "angle_deg": angle,
        "moving": moving,
        "fixed": fixed,
        "reachable": reachable,
        "extra": extra or {},
        "drive_gain": drive_gain,
        "slot_side_clearance_mm": slot_side_clearance_mm,
        "stow_angle_deg": stow_angle_deg,
        "check_self_collision": check_self_collision,
    }


def _pivot_trace(spec, steps, double=False, guided=False, case=False, external_combo=False):
    common = spec["common"]
    p = spec["parameters"]
    parts = _gantry(common) if double else {"column": _column(common)}
    pivot0 = (40.0, 20.0)
    pivot_path = []
    for i in range(steps):
        t = i / (steps - 1)
        lift, shift, _ = _phase(t, p.get("lift_mm", 0.0), p.get("shift_x_mm", 0.0))
        pivot_path.append((pivot0[0] + shift, pivot0[1] + lift))
    trace = []
    for i in range(steps):
        t = i / (steps - 1)
        lift, shift, fold_fraction = _phase(t, p.get("lift_mm", 0.0), p.get("shift_x_mm", 0.0))
        angle = p["fold_angle_deg"] * fold_fraction
        direction = 1 if spec["id"] == "F08" else -1
        moving = _folded_parts(parts, pivot0, lift, shift, angle, direction)
        fixed = _base_parts(common)
        pivot = pivot_path[i]
        slot_clearance = 0.0
        if guided:
            fixed["slot_rail"] = LineString(pivot_path).buffer(p["slot_width_mm"] / 2, cap_style=2)
            moving["roller"] = Point(pivot).buffer(p["roller_diameter_mm"] / 2)
            slot_clearance = (p["slot_width_mm"] - p["roller_diameter_mm"]) / 2
        extra = {}
        check_self = False
        if case:
            wall = p["case_wall_mm"]
            top = max(polygon.bounds[3] for polygon in moving.values()) + wall
            lid = box(-wall, top - 365, 0, top)
            moving["lid"] = rotate(lid, -90 * fold_fraction, origin=(-wall, top))
            moving["lid_link"] = LineString([(-wall, top), pivot]).buffer(2.0)
            extra["case_envelope"] = box(-wall, -wall, 315 + wall, top)
            check_self = True
        stow_angle = 0.0
        if external_combo and t > 0.7:
            stow_fraction = (t - 0.7) / 0.3
            stow_angle = -p["stow_angle_deg"] * stow_fraction
            stow_shift = p["stow_shift_x_mm"] * stow_fraction
            external_pivot = (-40.0, 20.0)
            printer = list(moving.values()) + list(fixed.values())
            moving = {
                f"printer_{index}": translate(rotate(polygon, stow_angle, origin=external_pivot), xoff=stow_shift)
                for index, polygon in enumerate(printer)
            }
            fixed = {"wall": box(-80, -40, -70, 450)}
        if external_combo and i == steps - 1:
            clearance = p["cabinet_clearance_mm"]
            all_parts = list(moving.values()) + list(fixed.values())
            min_x = min(polygon.bounds[0] for polygon in all_parts) - clearance
            max_x = max(polygon.bounds[2] for polygon in all_parts) + clearance
            min_z = min(polygon.bounds[1] for polygon in all_parts) - clearance
            max_z = max(polygon.bounds[3] for polygon in all_parts) + clearance
            extra["cabinet"] = box(min_x, min_z, max_x, max_z)
        trace.append(_state(
            t, moving, fixed, pivot, direction * angle + stow_angle, extra=extra,
            slot_side_clearance_mm=slot_clearance, stow_angle_deg=abs(stow_angle),
            check_self_collision=check_self,
        ))
    return trace


def _arm_trace(spec, steps):
    common = spec["common"]
    p = spec["parameters"]
    fixed = _base_parts(common)
    fixed["column"] = _column(common)
    arm = box(50, 300, 50 + p["arm_length_mm"], 320)
    toolhead = box(150, 250, 200, 300)
    pivot = (50.0, 310.0)
    trace = []
    for i in range(steps):
        t = i / (steps - 1)
        angle = -p["fold_angle_deg"] * t
        moving = {
            "arm": rotate(arm, angle, origin=pivot),
            "toolhead": rotate(toolhead, angle, origin=pivot),
        }
        trace.append(_state(t, moving, fixed, pivot, angle))
    return trace


def _telescope_trace(spec, steps, stages):
    common = spec["common"]
    overlap = spec["parameters"]["overlap_mm"]
    extended = common["column_top_mm"] - common["column_bottom_mm"]
    stage_height = (extended + (stages - 1) * overlap) / stages
    fixed = _base_parts(common)
    trace = []
    for i in range(steps):
        t = i / (steps - 1)
        moving = {}
        for stage in range(stages):
            bottom = 20 + stage * (stage_height - overlap) * (1 - t)
            moving[f"stage_{stage + 1}"] = box(30, bottom, 50, bottom + stage_height)
        trace.append(_state(t, moving, fixed, (40.0, 20.0)))
    return trace


def _external_flip_trace(spec, steps):
    common = spec["common"]
    fixed = {"wall": box(-70, -30, -60, 430)}
    moving = _base_parts(common)
    moving["column"] = _column(common)
    pivot = (-40.0, 20.0)
    trace = []
    for i in range(steps):
        t = i / (steps - 1)
        angle = -spec["parameters"]["fold_angle_deg"] * t
        posed = {name: rotate(polygon, angle, origin=pivot) for name, polygon in moving.items()}
        extra = {}
        if i == steps - 1:
            clearance = spec["parameters"]["cabinet_clearance_mm"]
            min_x = min(polygon.bounds[0] for polygon in posed.values()) - clearance
            max_x = max(polygon.bounds[2] for polygon in posed.values()) + clearance
            min_z = min(polygon.bounds[1] for polygon in posed.values()) - clearance
            max_z = max(polygon.bounds[3] for polygon in posed.values()) + clearance
            extra["cabinet"] = box(min_x, min_z, max_x, max_z)
        trace.append(_state(t, posed, fixed, pivot, angle, extra=extra))
    return trace


def _drawer_trace(spec, steps):
    common = spec["common"]
    fixed = {"base": box(0, 0, 315, 20), "column": _column(common)}
    stroke = spec["parameters"]["drawer_stroke_mm"]
    trace = []
    for i in range(steps):
        t = i / (steps - 1)
        offset = stroke * (1 - t)
        moving = {
            "y_module": box(70 + offset, 40, 250 + offset, 60),
            "y_rail": box(60 + offset, 25, 270 + offset, 40),
        }
        radius = spec["parameters"]["cable_bend_radius_mm"]
        extra = {"cable_chain_envelope": box(250, 0, 315, 2 * radius)}
        trace.append(_state(t, moving, fixed, (160 + offset, 40.0), extra=extra))
    return trace


def _scissor_trace(spec, steps):
    common = spec["common"]
    p = spec["parameters"]
    fixed = {"base": box(0, 0, 315, 20)}
    center = 157.5
    trace = []
    for i in range(steps):
        t = i / (steps - 1)
        height = p["height_work_max_mm"] + (p["height_fold_mm"] - p["height_work_max_mm"]) * t
        span_squared = max(0.0, 4 * p["arm_length_mm"] ** 2 - height**2)
        span = math.sqrt(span_squared)
        reachable = height <= 2 * p["arm_length_mm"] and height > 0
        left = center - span / 2
        right = center + span / 2
        low = 23.0
        high = low + height
        link_a = LineString([(left, low), (right, high)]).buffer(3.0, cap_style=2)
        link_b = LineString([(right, low), (left, high)]).buffer(3.0, cap_style=2)
        moving = {
            "scissor_a": link_a,
            "scissor_b": link_b,
            "top_frame": box(center - 150, high, center + 150, high + p["frame_offset_mm"] - 3.0),
        }
        gain = abs(scissor_state(p["arm_length_mm"], span)["dH_dS"]) if reachable else math.inf
        trace.append(_state(t, moving, fixed, (center, high), reachable=reachable, drive_gain=gain))
    return trace


def _build_family_trace(spec, parameters=None, steps=31):
    if steps < 2:
        raise ValueError("A trace needs at least two states")
    if parameters is not None:
        spec = dict(spec)
        spec["parameters"] = dict(spec["parameters"], **parameters)
    family = spec["family"]
    if family == "root_single":
        return _pivot_trace(spec, steps)
    if family == "root_double":
        return _pivot_trace(spec, steps, double=True)
    if family == "guided_single":
        return _pivot_trace(spec, steps, guided=True)
    if family == "guided_double":
        return _pivot_trace(spec, steps, double=True, guided=True)
    if family == "case_linked":
        return _pivot_trace(spec, steps, case=True)
    if family == "external_combo":
        return _pivot_trace(spec, steps, double=True, external_combo=True)
    if family == "arm_fold":
        return _arm_trace(spec, steps)
    if family == "telescope_2":
        return _telescope_trace(spec, steps, 2)
    if family == "telescope_3":
        return _telescope_trace(spec, steps, 3)
    if family == "external_flip":
        return _external_flip_trace(spec, steps)
    if family == "drawer_y":
        return _drawer_trace(spec, steps)
    if family == "scissor":
        return _scissor_trace(spec, steps)
    raise ValueError(f"Unknown mechanism family: {family}")


def build_trace(spec, parameters=None, steps=31):
    trace = _build_family_trace(spec, parameters=parameters, steps=steps)
    if spec["family"] not in {"case_linked", "external_flip", "external_combo"}:
        trace[-1]["extra"]["transport_accessories"] = box(315, 0, 515, 70)
    return trace
