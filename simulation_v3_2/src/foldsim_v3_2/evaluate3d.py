"""V3.2 3D evaluator using Lipschitz-certified adaptive bisection on exact continuous trajectories."""

from __future__ import annotations

from typing import Any

import numpy as np

from .geometry3d import OBB, obb_sat_distance, verify_interval_collision
from .mechanisms3d import build_state_at_t, build_trace_3d, get_phase_intervals


def _assembly_aabb(obbs: list[OBB]) -> tuple[np.ndarray, np.ndarray]:
    mins = [o.aabb()[0] for o in obbs]
    maxs = [o.aabb()[1] for o in obbs]
    return np.min(mins, axis=0), np.max(maxs, axis=0)


def _aabb_volume(mn: np.ndarray, mx: np.ndarray) -> float:
    dims = np.maximum(0.0, mx - mn)
    return float(dims[0] * dims[1] * dims[2])


def _pair_key(a: str, b: str) -> tuple[str, str]:
    return (a, b) if a <= b else (b, a)


def _get_obb(state: dict[str, Any], group_key: str, name: str) -> OBB:
    for o in state[group_key]:
        if o.name == name:
            return o
    raise KeyError(f"OBB {name} not found in {group_key}")


def evaluate_candidate_3d(
    spec: dict[str, Any],
    parameters: dict[str, Any] | None = None,
    steps: int = 31,
    max_depth: int = 12,
) -> dict[str, Any]:
    if parameters is not None:
        spec = dict(spec)
        spec["parameters"] = dict(spec["parameters"], **parameters)

    trace = build_trace_3d(spec, steps=steps)
    intervals = get_phase_intervals(spec)

    s0 = build_state_at_t(spec, 0.0, include_extra=False)
    s1 = build_state_at_t(spec, 1.0, include_extra=True)
    allow_fixed = {_pair_key(a, b) for a, b in s0.get("allow_fixed_pairs", set())}
    allow_self = {_pair_key(a, b) for a, b in s0.get("allow_self_pairs", set())}

    max_pen = 0.0
    worst_pen_pair = ""
    worst_pen_t = 0.0
    min_clr = float("inf")
    worst_clr_pair = ""
    worst_clr_t = 0.0
    max_evals = 0
    any_unresolved = False
    unresolved_pairs: list[str] = []

    mov_names = [o.name for o in s0["moving"]]
    fix_names = [o.name for o in s0["fixed"]]

    # Determine when lift begins so resting column-on-base flush datum is not flagged before lift-off
    p = spec["parameters"]
    arm_fold_enabled = bool(p.get("arm_fold_enabled", 1 if spec["family"] in {"root_single_lift", "root_double_lift", "root_single_rear", "guided_single"} else 0))
    lift_start_t = 0.20 if arm_fold_enabled else 0.0

    # 1. Continuous moving-vs-fixed interval certification
    for mn in mov_names:
        for fn in fix_names:
            if _pair_key(mn, fn) in allow_fixed:
                continue
            for ta, tb in intervals:
                is_col_base_datum = ("column" in mn and fn == "base" and tb <= lift_start_t + 1e-9)
                if is_col_base_datum:
                    # Verify static non-penetration during resting phase prior to lift-off
                    col, pen, _ = obb_sat_distance(_get_obb(s0, "moving", mn), _get_obb(s0, "fixed", fn))
                    if col and pen > max_pen:
                        max_pen = pen
                        worst_pen_pair = f"{mn} <-> {fn}"
                        worst_pen_t = ta
                    continue

                t_lo = max(ta, lift_start_t + 0.005) if ("column" in mn and fn == "base" and ta <= lift_start_t <= tb) else (max(ta, 0.005) if ("column" in mn and fn == "base" and ta == 0.0) else ta)
                if t_lo >= tb:
                    continue

                res = verify_interval_collision(
                    lambda t, _mn=mn: _get_obb(build_state_at_t(spec, t), "moving", _mn),
                    lambda t, _fn=fn: _get_obb(build_state_at_t(spec, t), "fixed", _fn),
                    t0=t_lo,
                    t1=tb,
                    max_depth=max_depth,
                )
                max_evals = max(max_evals, res["evaluations"])
                if res["status"] == "FAIL":
                    if res["penetration_mm"] > max_pen:
                        max_pen = res["penetration_mm"]
                        worst_pen_pair = f"{mn} <-> {fn} (continuous)"
                        worst_pen_t = float(res["t_collision"] or t_lo)
                elif res["status"] == "UNRESOLVED":
                    any_unresolved = True
                    unresolved_pairs.append(f"{mn}<->{fn}@{t_lo:.2f}-{tb:.2f}")
                else:
                    if res["clearance_mm"] < min_clr:
                        min_clr = res["clearance_mm"]
                        worst_clr_pair = f"{mn} <-> {fn} (continuous)"
                        worst_clr_t = 0.5 * (t_lo + tb)

    # 2. Continuous moving-vs-moving relative interval certification
    for i, na in enumerate(mov_names):
        for nb in mov_names[i + 1:]:
            if _pair_key(na, nb) in allow_self:
                continue
            for ta, tb in intervals:
                res = verify_interval_collision(
                    lambda t, _na=na: _get_obb(build_state_at_t(spec, t), "moving", _na),
                    lambda t, _nb=nb: _get_obb(build_state_at_t(spec, t), "moving", _nb),
                    t0=ta,
                    t1=tb,
                    max_depth=max_depth,
                )
                max_evals = max(max_evals, res["evaluations"])
                if res["status"] == "FAIL":
                    if res["penetration_mm"] > max_pen:
                        max_pen = res["penetration_mm"]
                        worst_pen_pair = f"{na} <-> {nb} (self-continuous)"
                        worst_pen_t = float(res["t_collision"] or ta)
                elif res["status"] == "UNRESOLVED":
                    any_unresolved = True
                    unresolved_pairs.append(f"{na}<->{nb}@{ta:.2f}-{tb:.2f}")
                else:
                    if res["clearance_mm"] < min_clr:
                        min_clr = res["clearance_mm"]
                        worst_clr_pair = f"{na} <-> {nb} (self-continuous)"
                        worst_clr_t = 0.5 * (ta + tb)

    # 3. Folded-state accessory interference check
    for ex in s1["extra"]:
        if ex.name in {"case_envelope", "cabinet"}:
            continue
        for obs in s1["fixed"] + s1["moving"]:
            col, pen, clr = obb_sat_distance(ex, obs)
            if col and pen > max_pen:
                max_pen = pen
                worst_pen_pair = f"{ex.name} <-> {obs.name} (accessory)"
                worst_pen_t = 1.0
            if not col and clr < min_clr:
                min_clr = clr
                worst_clr_pair = f"{ex.name} <-> {obs.name} (accessory)"
                worst_clr_t = 1.0

    # 4. COM stability & reachability across sampled trace
    com_stable_all = True
    for state in trace:
        all_phys = state["fixed"] + state["moving"]
        vols = [float(np.prod(o.half_extents * 2.0)) for o in all_phys]
        com_x = sum(float(o.center[0]) * v for o, v in zip(all_phys, vols)) / max(sum(vols), 1e-9)
        sx0, sx1 = state.get("support_x_range", (0.0, 315.0))
        if not (sx0 <= com_x <= sx1):
            com_stable_all = False

    w_mn, w_mx = _assembly_aabb(s0["fixed"] + s0["moving"] + s0["extra"])
    f_mn, f_mx = _assembly_aabb(s1["fixed"] + s1["moving"] + s1["extra"])
    work_vol = _aabb_volume(w_mn, w_mx)
    folded_vol = _aabb_volume(f_mn, f_mx)
    storage_ratio = folded_vol / work_vol
    folded_dims = (f_mx - f_mn).tolist()
    ws_cov = s0["workspace_coverage"]
    reachable_fraction = sum(1 for s in trace if s["reachable"]) / len(trace)

    if max_pen > 1e-4:
        collision_status = "FAIL"
    elif any_unresolved:
        collision_status = "UNRESOLVED"
    else:
        collision_status = "PASS"

    reasons = []
    if collision_status != "PASS":
        reasons.append(f"连续区间认证 {collision_status}: 穿透 {max_pen:.3f} mm @ t={worst_pen_t:.3f} ({worst_pen_pair})")
    if not com_stable_all:
        reasons.append("重心超出支撑多边形")
    if reachable_fraction < 1.0:
        reasons.append("部分姿态不可达")
    if ws_cov < 1.0 - 1e-6:
        reasons.append(f"工作空间覆盖率 {ws_cov:.2%} < 100%")
    if storage_ratio > 0.80:
        reasons.append(f"3D 收纳体积比 {storage_ratio:.3f} > 0.800")

    return {
        "id": spec["id"],
        "name": spec["name"],
        "collision_status": collision_status,
        "storage_ratio": float(storage_ratio),
        "folded_dims_mm": [round(float(x), 2) for x in folded_dims],
        "folded_max_dim_mm": round(float(max(folded_dims)), 2),
        "max_penetration_mm": float(max_pen),
        "worst_pen_pair": worst_pen_pair,
        "worst_pen_t": float(worst_pen_t),
        "min_clearance_mm": float(min_clr if min_clr < float("inf") else 0.0),
        "worst_clr_pair": worst_clr_pair,
        "worst_clr_t": float(worst_clr_t),
        "max_interval_evals": max_evals,
        "unresolved_pairs": unresolved_pairs,
        "workspace_coverage": float(ws_cov),
        "com_stable": com_stable_all,
        "passed_screen": len(reasons) == 0,
        "screen_reasons": reasons,
        "parameters": dict(spec["parameters"]),
    }
