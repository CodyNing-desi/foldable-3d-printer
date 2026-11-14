"""Unified 3D 6-DOF Space-Frame FEA for F07, F09, F12, SCZ, and F08 with mesh convergence."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from scipy.linalg import solve


def _local_beam_k(E: float, G: float, A: float, Iy: float, Iz: float, J: float, L: float) -> np.ndarray:
    k = np.zeros((12, 12), dtype=float)
    EA_L = E * A / L
    GJ_L = G * J / L
    L2, L3 = L * L, L * L * L
    k[0, 0] = k[6, 6] = EA_L
    k[0, 6] = k[6, 0] = -EA_L
    k[3, 3] = k[9, 9] = GJ_L
    k[3, 9] = k[9, 3] = -GJ_L

    c1z, c2z, c3z, c4z = 12 * E * Iy / L3, 6 * E * Iy / L2, 4 * E * Iy / L, 2 * E * Iy / L
    idx_z = [2, 4, 8, 10]
    k[np.ix_(idx_z, idx_z)] += np.array([
        [c1z, -c2z, -c1z, -c2z], [-c2z, c3z, c2z, c4z],
        [-c1z, c2z, c1z, c2z], [-c2z, c4z, c2z, c3z],
    ])

    c1y, c2y, c3y, c4y = 12 * E * Iz / L3, 6 * E * Iz / L2, 4 * E * Iz / L, 2 * E * Iz / L
    idx_y = [1, 5, 7, 11]
    k[np.ix_(idx_y, idx_y)] += np.array([
        [c1y, c2y, -c1y, c2y], [c2y, c3y, -c2y, c4y],
        [-c1y, -c2y, c1y, -c2y], [c2y, c4y, -c2y, c3y],
    ])
    return k


def _beam_transform(p0: np.ndarray, p1: np.ndarray) -> tuple[np.ndarray, float]:
    v = p1 - p0
    L = float(np.linalg.norm(v))
    ex = v / L
    ref = np.array([0.0, 1.0, 0.0]) if abs(ex[1]) < 0.9 else np.array([0.0, 0.0, 1.0])
    ez = np.cross(ex, ref)
    ez /= float(np.linalg.norm(ez))
    ey = np.cross(ez, ex)
    R = np.vstack([ex, ey, ez])
    T = np.zeros((12, 12), dtype=float)
    for b in range(4):
        T[3 * b : 3 * b + 3, 3 * b : 3 * b + 3] = R
    return T, L


def solve_space_frame(nodes: np.ndarray, elements: list[dict[str, Any]], fixed_dofs: list[int], loads: dict[int, float]) -> dict[str, Any]:
    n_nodes = len(nodes)
    n_dof = 6 * n_nodes
    K = np.zeros((n_dof, n_dof), dtype=float)
    F = np.zeros(n_dof, dtype=float)
    for el in elements:
        i, j = el["n0"], el["n1"]
        T, L = _beam_transform(nodes[i], nodes[j])
        k_loc = _local_beam_k(el["E"], el["G"], el["A"], el["Iy"], el["Iz"], el["J"], L)
        dofs = list(range(6 * i, 6 * i + 6)) + list(range(6 * j, 6 * j + 6))
        K[np.ix_(dofs, dofs)] += T.T @ k_loc @ T
    for dof_idx, val in loads.items():
        F[dof_idx] += val
    fixed_set = sorted(set(fixed_dofs))
    free_dofs = [d for d in range(n_dof) if d not in fixed_set]
    u = np.zeros(n_dof, dtype=float)
    u[free_dofs] = solve(K[np.ix_(free_dofs, free_dofs)], F[free_dofs], assume_a="sym")
    return {"u": u, "n_nodes": n_nodes, "n_dofs": n_dof}


def hollow_square_props(outer: float, wall: float) -> dict[str, float]:
    inner = max(1.0, outer - 2.0 * wall)
    A = outer**2 - inner**2
    I = (outer**4 - inner**4) / 12.0
    a_m = outer - wall
    J = 4.0 * ((a_m**2)**2) * wall / (4.0 * a_m)
    return {"A": A, "Iy": I, "Iz": I, "J": J}


def evaluate_candidate_fea3d(candidate_id: str, spec: dict[str, Any], parameters: dict[str, Any] | None = None, n_sub: int = 10) -> dict[str, Any]:
    common = spec["common"]
    p = dict(spec["parameters"] if parameters is None else dict(spec["parameters"], **parameters))
    E, G = common["aluminum_E_N_mm2"], common["aluminum_G_N_mm2"]
    load_N = common["lateral_load_N"]
    L_arm = common["x_arm_length_mm"]

    if candidate_id in {"F07", "F08"}:
        H_col = common["column_top_mm"] - common["column_bottom_mm"]
        z_arm = 275.0
        A_col, Iy_col, Iz_col, J_col = 420.0, 7000.0, 11000.0, 8500.0
        props_arm = hollow_square_props(24.0, 2.5)
        zs = np.linspace(0.0, H_col, n_sub + 1)
        arm_idx = int(np.argmin(np.abs(zs - z_arm)))
        nodes = [[40.0, 0.0, z] for z in zs]
        elements = []
        for k in range(n_sub):
            # Base element includes hinge+lock rotational compliance
            zm = 0.5 * (zs[k] + zs[k + 1])
            factor = 0.55 if zm <= 45.0 else 1.0
            elements.append({"n0": k, "n1": k + 1, "E": E, "G": G, "A": A_col, "Iy": Iy_col * factor, "Iz": Iz_col * factor, "J": J_col * factor})
        arm_start = len(nodes)
        for m in range(1, 5):
            nodes.append([40.0 + L_arm * m / 4, 0.0, zs[arm_idx]])
        prev = arm_idx
        for m in range(4):
            cur = arm_start + m
            elements.append({"n0": prev, "n1": cur, "E": E, "G": G, **props_arm})
            prev = cur
        tip_node = prev
        res = solve_space_frame(np.array(nodes), elements, fixed_dofs=[0, 1, 2, 3, 4, 5], loads={6 * tip_node + 1: load_N})
        tip_uy = float(res["u"][6 * tip_node + 1])
        col_uy = float(res["u"][6 * n_sub + 1])
        return {"id": candidate_id, "fea_level": "L3_3D_space_frame_FEA", "dofs": res["n_dofs"], "tip_lateral_deflection_mm": abs(tip_uy), "column_top_deflection_mm": abs(col_uy), "torsion_induced_mm": abs(tip_uy) - abs(col_uy)}

    if candidate_id == "F09":
        # Real 3D Twin-Column Gantry + Crossbar + Joint Compliance!
        H_col = common["column_top_mm"] - common["column_bottom_mm"]
        A_col, Iy_col, Iz_col, J_col = 420.0, 7000.0, 11000.0, 8500.0
        props_cross = hollow_square_props(30.0, 3.0)
        zs = np.linspace(0.0, H_col, n_sub + 1)
        nodes = []
        elements = []
        # Left column at y=-130 (indices 0..n_sub), Right column at y=+130 (indices n_sub+1..2*n_sub+1)
        for z in zs:
            nodes.append([40.0, -130.0, z])
        for z in zs:
            nodes.append([40.0, 130.0, z])
        off_r = n_sub + 1
        for k in range(n_sub):
            # Base hinge+lock compliance on both columns
            zm = 0.5 * (zs[k] + zs[k + 1])
            factor = 0.55 if zm <= 45.0 else 1.0
            elements.append({"n0": k, "n1": k + 1, "E": E, "G": G, "A": A_col, "Iy": Iy_col * factor, "Iz": Iz_col * factor, "J": J_col * factor})
            elements.append({"n0": off_r + k, "n1": off_r + k + 1, "E": E, "G": G, "A": A_col, "Iy": Iy_col * factor, "Iz": Iz_col * factor, "J": J_col * factor})
        # Crossbar at z=H_col split into 4 segments with center toolhead node
        c_start = len(nodes)
        for y in [-65.0, 0.0, 65.0]:
            nodes.append([40.0, y, H_col])
        cross_chain = [n_sub, c_start, c_start + 1, c_start + 2, off_r + n_sub]
        for idx_c in range(len(cross_chain) - 1):
            # Corner gusset compliance at ends
            f_c = 0.70 if idx_c in {0, 3} else 1.0
            elements.append({"n0": cross_chain[idx_c], "n1": cross_chain[idx_c + 1], "E": E, "G": G, "A": props_cross["A"], "Iy": props_cross["Iy"] * f_c, "Iz": props_cross["Iz"] * f_c, "J": props_cross["J"] * f_c})
        th_node = c_start + 1
        fixed_dofs = [0, 1, 2, 3, 4, 5] + [6 * off_r + d for d in range(6)]
        res = solve_space_frame(np.array(nodes), elements, fixed_dofs=fixed_dofs, loads={6 * th_node + 1: load_N})
        tip_uy = float(res["u"][6 * th_node + 1])
        return {"id": candidate_id, "fea_level": "L3_3D_space_frame_FEA", "dofs": res["n_dofs"], "tip_lateral_deflection_mm": abs(tip_uy), "column_top_deflection_mm": abs(tip_uy), "torsion_induced_mm": 0.0}

    if candidate_id == "F12":
        outer_sz = p.get("outer_size_mm", 60.0)
        wall = p.get("wall_mm", 3.0)
        overlap = p["overlap_mm"]
        H_ext = common["column_top_mm"] - common["column_bottom_mm"]
        stage_h = (H_ext + 2.0 * overlap) / 3.0
        step_sz = 2.0 * (wall + p.get("radial_clearance_mm", 0.015) + p.get("pad_thickness_mm", 2.985))
        s1_props = hollow_square_props(outer_sz, wall)
        s2_props = hollow_square_props(outer_sz - step_sz, wall)
        s3_props = hollow_square_props(outer_sz - 2.0 * step_sz, wall)
        props_arm = hollow_square_props(24.0, 2.5)
        z1, z2, z3 = stage_h, stage_h + (stage_h - overlap), H_ext
        zs = np.linspace(0.0, z3, n_sub * 2 + 1)
        nodes = [[40.0, 0.0, z] for z in zs]
        elements = []
        for k in range(len(zs) - 1):
            zm = 0.5 * (zs[k] + zs[k + 1])
            pr = s1_props if zm <= z1 else (s2_props if zm <= z2 else s3_props)
            elements.append({"n0": k, "n1": k + 1, "E": E, "G": G, **pr})
        arm_idx = len(zs) - 2
        arm_start = len(nodes)
        for m in range(1, 5):
            nodes.append([40.0 + L_arm * m / 4, 0.0, zs[arm_idx]])
        prev = arm_idx
        for m in range(4):
            cur = arm_start + m
            elements.append({"n0": prev, "n1": cur, "E": E, "G": G, **props_arm})
            prev = cur
        tip_node = prev
        res = solve_space_frame(np.array(nodes), elements, fixed_dofs=[0, 1, 2, 3, 4, 5], loads={6 * tip_node + 1: load_N})
        tip_uy = float(res["u"][6 * tip_node + 1])
        col_uy = float(res["u"][6 * (len(zs) - 1) + 1])
        return {"id": candidate_id, "fea_level": "L3_3D_space_frame_FEA", "dofs": res["n_dofs"], "tip_lateral_deflection_mm": abs(tip_uy), "column_top_deflection_mm": abs(col_uy), "torsion_induced_mm": max(0.0, abs(tip_uy) - abs(col_uy))}

    # SCZ: Dual Y-side scissor space frame
    arm_len = p["arm_length_mm"]
    height = p["height_work_max_mm"] - 90.0
    span = math.sqrt(max(100.0, 4.0 * arm_len**2 - height**2))
    cx = 157.5
    lx, rx = cx - 0.5 * span, cx + 0.5 * span
    nodes = np.array([
        [lx, -130.0, 0.0], [rx, -130.0, 0.0], [cx, -130.0, height / 2.0], [lx, -130.0, height], [rx, -130.0, height],
        [lx, 130.0, 0.0], [rx, 130.0, 0.0], [cx, 130.0, height / 2.0], [lx, 130.0, height], [rx, 130.0, height],
    ], dtype=float)
    w, t = p.get("arm_width_mm", 20.0), p.get("arm_thick_mm", 6.0)
    bar_props = {"E": E, "G": G, "A": w * t, "Iy": t * w**3 / 12.0, "Iz": w * t**3 / 12.0, "J": w * t**3 / 3.0 * (1.0 - 0.63 * t / w)}
    top_props = {"E": E, "G": G, **hollow_square_props(20.0, 2.0)}
    elements = [
        {"n0": 0, "n1": 2, **bar_props}, {"n0": 2, "n1": 4, **bar_props},
        {"n0": 1, "n1": 2, **bar_props}, {"n0": 2, "n1": 3, **bar_props},
        {"n0": 5, "n1": 7, **bar_props}, {"n0": 7, "n1": 9, **bar_props},
        {"n0": 6, "n1": 7, **bar_props}, {"n0": 7, "n1": 8, **bar_props},
        {"n0": 3, "n1": 4, **top_props}, {"n0": 8, "n1": 9, **top_props},
        {"n0": 3, "n1": 8, **top_props}, {"n0": 4, "n1": 9, **top_props},
    ]
    fixed_dofs = [0, 1, 2, 30, 31, 32, 7, 8, 37, 38]
    res = solve_space_frame(nodes, elements, fixed_dofs=fixed_dofs, loads={19: 0.5 * load_N, 49: 0.5 * load_N})
    tip_uy = 0.5 * (abs(res["u"][19]) + abs(res["u"][49]))
    return {"id": candidate_id, "fea_level": "L3_3D_space_frame_FEA", "dofs": res["n_dofs"], "tip_lateral_deflection_mm": float(tip_uy), "column_top_deflection_mm": float(tip_uy), "torsion_induced_mm": 0.0}
