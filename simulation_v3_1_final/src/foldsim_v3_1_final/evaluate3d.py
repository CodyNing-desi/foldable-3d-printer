"""V3.1 Final 3D evaluator: Chasles rotational + moving-vs-moving swept collision with PASS/FAIL/UNRESOLVED."""

from __future__ import annotations

from typing import Any

import numpy as np

from .geometry3d import OBB, obb_sat_distance, swept_obb_vs_obb
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


def evaluate_candidate_3d(
    spec: dict[str, Any],
    parameters: dict[str, Any] | None = None,
    steps: int = 101,
    swept_check: bool = True,
    step_bound_mm: float = 2.0,
    angle_bound_deg: float = 3.0,
) -> dict[str, Any]:
    if parameters is not None:
        spec = dict(spec)
        spec["parameters"] = dict(spec["parameters"], **parameters)
    trace = build_trace_3d(spec, steps=steps)

    max_pen = 0.0
    worst_pen_pair = ""
    worst_pen_t = 0.0
    min_clr = float("inf")
    worst_clr_pair = ""
    worst_clr_t = 0.0
    max_substeps = 1
    any_unresolved = False
    com_stable_all = True

    for idx, state in enumerate(trace):
        t_val = state["t"]
        moving: list[OBB] = state["moving"]
        fixed: list[OBB] = state["fixed"]
        extra: list[OBB] = state.get("extra", [])
        allow_fixed = {_pair_key(a, b) for a, b in state.get("allow_fixed_pairs", set())}
        allow_self = {_pair_key(a, b) for a, b in state.get("allow_self_pairs", set())}

        # Static checks at state t
        for m in moving:
            for f in fixed:
                if _pair_key(m.name, f.name) in allow_fixed:
                    continue
                col, pen, clr = obb_sat_distance(m, f)
                if col and pen > max_pen:
                    max_pen = pen
                    worst_pen_pair = f"{m.name} <-> {f.name}"
                    worst_pen_t = t_val
                if not col and t_val > 0.05 and clr < min_clr:
                    min_clr = clr
                    worst_clr_pair = f"{m.name} <-> {f.name}"
                    worst_clr_t = t_val

        for i, a in enumerate(moving):
            for b in moving[i + 1:]:
                if _pair_key(a.name, b.name) in allow_self:
                    continue
                col, pen, clr = obb_sat_distance(a, b)
                if col and pen > max_pen:
                    max_pen = pen
                    worst_pen_pair = f"{a.name} <-> {b.name} (self)"
                    worst_pen_t = t_val
                if not col and t_val > 0.05 and clr < min_clr:
                    min_clr = clr
                    worst_clr_pair = f"{a.name} <-> {b.name} (self)"
                    worst_clr_t = t_val

        for ex in extra:
            if ex.name in {"case_envelope", "cabinet"}:
                continue
            for obs in fixed + moving:
                col, pen, clr = obb_sat_distance(ex, obs)
                if col and pen > max_pen:
                    max_pen = pen
                    worst_pen_pair = f"{ex.name} <-> {obs.name} (accessory)"
                    worst_pen_t = t_val
                if not col and clr < min_clr:
                    min_clr = clr
                    worst_clr_pair = f"{ex.name} <-> {obs.name} (accessory)"
                    worst_clr_t = t_val

        # Swept checks over [t_{idx-1}, t_{idx}] for BOTH moving-vs-fixed AND moving-vs-moving!
        if swept_check and idx > 0:
            prev = trace[idx - 1]
            p_mov = {o.name: o for o in prev["moving"]}
            c_mov = {o.name: o for o in moving}
            # Moving vs Fixed swept
            for name, m1 in c_mov.items():
                m0 = p_mov.get(name)
                if m0 is None:
                    continue
                for f in fixed:
                    if _pair_key(name, f.name) in allow_fixed:
                        continue
                    sw = swept_obb_vs_obb(m0, m1, f, f, step_bound_mm=step_bound_mm, angle_bound_deg=angle_bound_deg)
                    max_substeps = max(max_substeps, sw["n_substeps"])
                    if sw["status"] == "UNRESOLVED":
                        any_unresolved = True
                    is_flush_datum = (t_val <= 0.05 and sw["penetration_mm"] < 0.005 and "column" in name and f.name == "base")
                    if not is_flush_datum and sw["colliding"] and sw["penetration_mm"] > max_pen:
                        max_pen = sw["penetration_mm"]
                        worst_pen_pair = f"{name} <-> {f.name} (swept)"
                        worst_pen_t = t_val
                    if not sw["colliding"] and t_val > 0.05 and sw["clearance_mm"] < min_clr:
                        min_clr = sw["clearance_mm"]
                        worst_clr_pair = f"{name} <-> {f.name} (swept)"
                        worst_clr_t = t_val

            # Moving vs Moving relative swept
            names = list(c_mov.keys())
            for i, na in enumerate(names):
                for nb in names[i + 1:]:
                    if _pair_key(na, nb) in allow_self:
                        continue
                    a0, a1 = p_mov.get(na), c_mov[na]
                    b0, b1 = p_mov.get(nb), c_mov[nb]
                    if a0 is None or b0 is None:
                        continue
                    sw = swept_obb_vs_obb(a0, a1, b0, b1, step_bound_mm=step_bound_mm, angle_bound_deg=angle_bound_deg)
                    max_substeps = max(max_substeps, sw["n_substeps"])
                    if sw["status"] == "UNRESOLVED":
                        any_unresolved = True
                    if sw["colliding"] and sw["penetration_mm"] > max_pen:
                        max_pen = sw["penetration_mm"]
                        worst_pen_pair = f"{na} <-> {nb} (self-swept)"
                        worst_pen_t = t_val
                    if not sw["colliding"] and t_val > 0.05 and sw["clearance_mm"] < min_clr:
                        min_clr = sw["clearance_mm"]
                        worst_clr_pair = f"{na} <-> {nb} (self-swept)"
                        worst_clr_t = t_val

        # COM tipping check
        all_phys = fixed + moving
        vols = [float(np.prod(o.half_extents * 2.0)) for o in all_phys]
        com_x = sum(float(o.center[0]) * v for o, v in zip(all_phys, vols)) / max(sum(vols), 1e-9)
        sx0, sx1 = state.get("support_x_range", (0.0, 315.0))
        if not (sx0 <= com_x <= sx1):
            com_stable_all = False

    w_mn, w_mx = _assembly_aabb(trace[0]["fixed"] + trace[0]["moving"] + trace[0]["extra"])
    f_mn, f_mx = _assembly_aabb(trace[-1]["fixed"] + trace[-1]["moving"] + trace[-1]["extra"])
    work_vol = _aabb_volume(w_mn, w_mx)
    folded_vol = _aabb_volume(f_mn, f_mx)
    storage_ratio = folded_vol / work_vol
    ws_cov = trace[0]["workspace_coverage"]
    reachable_fraction = sum(1 for s in trace if s["reachable"]) / len(trace)

    if max_pen > 1e-4:
        collision_status = "FAIL"
    elif any_unresolved:
        collision_status = "UNRESOLVED"
    else:
        collision_status = "PASS"

    reasons = []
    if collision_status != "PASS":
        reasons.append(f"连续扫掠 {collision_status}: 穿透 {max_pen:.3f} mm @ t={worst_pen_t:.3f} ({worst_pen_pair})")
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
        "storage_ratio": storage_ratio,
        "max_penetration_mm": float(max_pen),
        "worst_pen_pair": worst_pen_pair,
        "worst_pen_t": float(worst_pen_t),
        "min_clearance_mm": float(min_clr if min_clr < float("inf") else 0.0),
        "worst_clr_pair": worst_clr_pair,
        "worst_clr_t": float(worst_clr_t),
        "max_swept_substeps": max_substeps,
        "workspace_coverage": ws_cov,
        "com_stable": com_stable_all,
        "passed_screen": len(reasons) == 0,
        "screen_reasons": reasons,
        "parameters": dict(spec["parameters"]),
    }
