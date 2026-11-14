"""Pure-NumPy seeded NSGA-II multi-objective optimizer for Round 3."""

from __future__ import annotations

from typing import Any

import numpy as np

from .metrics_v3 import repeatability_monte_carlo_v3, structural_metrics_v3


def _fast_non_dominated_sort(F: np.ndarray, cv: np.ndarray) -> list[list[int]]:
    n = len(F)
    S = [[] for _ in range(n)]
    n_dom = np.zeros(n, dtype=int)
    fronts: list[list[int]] = [[]]
    for p in range(n):
        for q in range(n):
            if p == q:
                continue
            if cv[p] <= 0.0 and cv[q] > 0.0:
                p_dom_q = True
            elif cv[p] > 0.0 and cv[q] <= 0.0:
                p_dom_q = False
            elif cv[p] > 0.0 and cv[q] > 0.0:
                p_dom_q = cv[p] < cv[q]
            else:
                p_dom_q = bool(np.all(F[p] <= F[q]) and np.any(F[p] < F[q]))
            if p_dom_q:
                S[p].append(q)
            else:
                if cv[q] <= 0.0 and cv[p] > 0.0:
                    q_dom_p = True
                elif cv[q] > 0.0 and cv[p] <= 0.0:
                    q_dom_p = False
                elif cv[q] > 0.0 and cv[p] > 0.0:
                    q_dom_p = cv[q] < cv[p]
                else:
                    q_dom_p = bool(np.all(F[q] <= F[p]) and np.any(F[q] < F[p]))
                if q_dom_p:
                    n_dom[p] += 1
        if n_dom[p] == 0:
            fronts[0].append(p)
    i = 0
    while fronts[i]:
        nxt = []
        for p in fronts[i]:
            for q in S[p]:
                n_dom[q] -= 1
                if n_dom[q] == 0:
                    nxt.append(q)
        i += 1
        fronts.append(nxt)
    return fronts[:-1]


def _crowding_distance(F: np.ndarray, front: list[int]) -> np.ndarray:
    m, k = F.shape[1], len(front)
    dist = np.zeros(k, dtype=float)
    if k <= 2:
        dist[:] = float("inf")
        return dist
    sub = F[front]
    for obj in range(m):
        order = np.argsort(sub[:, obj])
        dist[order[0]] = dist[order[-1]] = float("inf")
        span = sub[order[-1], obj] - sub[order[0], obj]
        if span > 1e-12:
            for idx in range(1, k - 1):
                dist[order[idx]] += (sub[order[idx + 1], obj] - sub[order[idx - 1], obj]) / span
    return dist


def evaluate_design_v3(spec: dict[str, Any], x: np.ndarray, names: list[str]) -> dict[str, Any]:
    params = {name: float(val) for name, val in zip(names, x)}
    m = structural_metrics_v3(spec, parameters=params, steps=11, swept_check=False)
    mc = repeatability_monte_carlo_v3(spec, parameters=params, samples=500, seed=spec["seed"])
    F = np.array([
        m["storage_ratio"],
        mc["p95_mm"],
        m["elastic_deflection_mm"] + m["clearance_play_mm"],
        m["estimated_incremental_cost_CNY"] / 1000.0,
    ], dtype=float)
    special = m["peak_drive_force_N"] - 350.0
    if spec["family"] in {"telescope_2", "telescope_3"}:
        H_ext = spec["common"]["column_top_mm"] - spec["common"]["column_bottom_mm"]
        stages = 2 if spec["family"] == "telescope_2" else 3
        stage_h = (H_ext + (stages - 1) * params["overlap_mm"]) / stages
        special = 0.25 - params["overlap_mm"] / stage_h
    elif spec["family"] in {"guided_single", "guided_double"}:
        slot_clr = 0.5 * (params["slot_width_mm"] - spec["parameters"]["roller_diameter_mm"])
        special = max(0.25 - slot_clr, m["max_pressure_angle_deg"] - 45.0)
    elif spec["family"] == "drawer_y":
        special = 35.0 - params["cable_bend_radius_mm"]

    G = np.array([
        m["max_penetration_mm"] - 1e-4,
        m["storage_ratio"] - 0.80,
        1.0 - m["workspace_coverage"],
        special,
        1.0 - m["reachable_fraction"],
    ], dtype=float)
    return {"F": F, "G": G, "metrics": m, "p95_mm": mc["p95_mm"], "parameters": params}


def optimize_candidate_v3(spec: dict[str, Any], pop_size: int = 20, generations: int = 12, seed: int = 20261113) -> dict[str, Any]:
    names = list(spec["bounds"])
    xl = np.array([spec["bounds"][n][0] for n in names], dtype=float)
    xu = np.array([spec["bounds"][n][1] for n in names], dtype=float)
    rng = np.random.default_rng(seed)

    X = rng.uniform(xl, xu, size=(pop_size, len(names)))
    X[0] = np.clip([spec["parameters"][n] for n in names], xl, xu)
    evals = [evaluate_design_v3(spec, x, names) for x in X]
    F = np.array([e["F"] for e in evals])
    G = np.array([e["G"] for e in evals])
    cv = np.sum(np.maximum(0.0, G), axis=1)

    for _ in range(generations):
        off_X = []
        for _ in range(pop_size // 2):
            i1, i2 = rng.integers(0, pop_size, size=2)
            p1 = X[i1] if cv[i1] <= cv[i2] else X[i2]
            j1, j2 = rng.integers(0, pop_size, size=2)
            p2 = X[j1] if cv[j1] <= cv[j2] else X[j2]
            alpha = rng.uniform(-0.1, 1.1, size=len(names))
            c1 = np.clip(alpha * p1 + (1.0 - alpha) * p2, xl, xu)
            c2 = np.clip((1.0 - alpha) * p1 + alpha * p2, xl, xu)
            for c in (c1, c2):
                if rng.random() < 0.35:
                    idx = rng.integers(0, len(names))
                    c[idx] = np.clip(c[idx] + rng.normal(0.0, 0.12 * (xu[idx] - xl[idx])), xl[idx], xu[idx])
                off_X.append(c)
        off_arr = np.array(off_X)
        off_evals = [evaluate_design_v3(spec, x, names) for x in off_arr]
        comb_X = np.vstack([X, off_arr])
        comb_evals = evals + off_evals
        comb_F = np.array([e["F"] for e in comb_evals])
        comb_G = np.array([e["G"] for e in comb_evals])
        comb_cv = np.sum(np.maximum(0.0, comb_G), axis=1)

        fronts = _fast_non_dominated_sort(comb_F, comb_cv)
        selected = []
        for front in fronts:
            if len(selected) + len(front) <= pop_size:
                selected.extend(front)
            else:
                cd = _crowding_distance(comb_F, front)
                order = np.argsort(-cd)
                selected.extend([front[idx] for idx in order[: pop_size - len(selected)]])
                break
        X = comb_X[selected]
        evals = [comb_evals[idx] for idx in selected]
        F = np.array([e["F"] for e in evals])
        G = np.array([e["G"] for e in evals])
        cv = np.sum(np.maximum(0.0, G), axis=1)

    fronts = _fast_non_dominated_sort(F, cv)
    solutions = [
        {"parameters": evals[idx]["parameters"], "objectives": F[idx].tolist(), "constraints": G[idx].tolist(), "metrics": evals[idx]["metrics"]}
        for idx in fronts[0] if cv[idx] <= 1e-8
    ]
    least_idx = int(np.argmin(cv))
    return {
        "id": spec["id"], "algorithm": "NSGA-II (pure-NumPy seeded)", "seed": seed,
        "solutions": solutions,
        "least_infeasible": {
            "parameters": evals[least_idx]["parameters"],
            "constraints": G[least_idx].tolist(),
            "max_constraint_violation": float(np.max(G[least_idx])),
        },
    }
