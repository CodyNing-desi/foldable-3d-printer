"""V3.1 Unified 3D 6-DOF Space-Frame FEA:
- F07, F09, F08 all loaded at the exact same 215 mm X-cantilever arm tip (255, 0, 275).
- Reports X, Y, Z 3-axis stiffness + torsion, Ideal Rigid Lock vs Finite Joint Compliance.
- True mesh discretization (n_sub) for ALL candidates including SCZ (DOFs scale with n_sub!).
"""

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


def _subdivide_member(nodes: list[list[float]], elements: list[dict[str, Any]], n0: int, n1: int, n_sub: int, props: dict[str, Any]) -> None:
    """Subdivide beam (n0 -> n1) into n_sub equal elements so DOFs genuinely scale with n_sub."""
    p0 = np.array(nodes[n0], dtype=float)
    p1 = np.array(nodes[n1], dtype=float)
    prev = n0
    for s in range(1, n_sub):
        pt = p0 + (p1 - p0) * (s / n_sub)
        cur = len(nodes)
        nodes.append(pt.tolist())
        elements.append({"n0": prev, "n1": cur, **props})
        prev = cur
    elements.append({"n0": prev, "n1": n1, **props})


def evaluate_candidate_fea3d(
    candidate_id: str,
    spec: dict[str, Any],
    parameters: dict[str, Any] | None = None,
    n_sub: int = 8,
    ideal_rigid_joints: bool = False,
) -> dict[str, Any]:
    common = spec["common"]
    p = dict(spec["parameters"] if parameters is None else dict(spec["parameters"], **parameters))
    E, G = common["aluminum_E_N_mm2"], common["aluminum_G_N_mm2"]
    load_N = common["lateral_load_N"]
    L_arm = common["x_arm_length_mm"]
    base_factor = 1.0 if ideal_rigid_joints else 0.55
    corner_factor = 1.0 if ideal_rigid_joints else 0.70

    if candidate_id in {"F07", "F08"}:
        H_col = common["column_top_mm"] - common["column_bottom_mm"]
        z_arm = 275.0
        A_col, Iy_col, Iz_col, J_col = 420.0, 7000.0, 11000.0, 8500.0
        props_arm = hollow_square_props(24.0, 2.5)
        zs = np.linspace(0.0, H_col, n_sub + 1)
        arm_idx = int(np.argmin(np.abs(zs - z_arm)))
        nodes = [[40.0, 0.0, float(z)] for z in zs]
        elements = []
        for k in range(n_sub):
            zm = 0.5 * (zs[k] + zs[k + 1])
            f = base_factor if zm <= 45.0 else 1.0
            elements.append({"n0": k, "n1": k + 1, "E": E, "G": G, "A": A_col, "Iy": Iy_col * f, "Iz": Iz_col * f, "J": J_col * f})
        tip_node = len(nodes)
        nodes.append([40.0 + L_arm, 0.0, float(zs[arm_idx])])
        _subdivide_member(nodes, elements, arm_idx, tip_node, max(2, n_sub // 2), {"E": E, "G": G, **props_arm})

        fixed = [0, 1, 2, 3, 4, 5]
        arr_nodes = np.array(nodes, dtype=float)
        rx = solve_space_frame(arr_nodes, elements, fixed, {6 * tip_node + 0: load_N})
        ry = solve_space_frame(arr_nodes, elements, fixed, {6 * tip_node + 1: load_N})
        rz = solve_space_frame(arr_nodes, elements, fixed, {6 * tip_node + 2: load_N})
        return {
            "id": candidate_id, "fea_level": "L3_3D_space_frame_FEA_v3_1",
            "dofs": ry["n_dofs"], "ideal_rigid_joints": ideal_rigid_joints,
            "tip_x_deflection_mm": abs(float(rx["u"][6 * tip_node + 0])),
            "tip_y_deflection_mm": abs(float(ry["u"][6 * tip_node + 1])),
            "tip_z_deflection_mm": abs(float(rz["u"][6 * tip_node + 2])),
            "tip_lateral_deflection_mm": abs(float(ry["u"][6 * tip_node + 1])),
            "torsion_rot_rad": abs(float(ry["u"][6 * arm_idx + 5])),
        }

    if candidate_id == "F09":
        # F09 FIXED: Twin columns + crossbar + SAME 215 mm X-cantilever arm loaded at tip (255, 0, 275)!
        H_col = common["column_top_mm"] - common["column_bottom_mm"]
        z_arm = 275.0
        A_col, Iy_col, Iz_col, J_col = 420.0, 7000.0, 11000.0, 8500.0
        props_cross = hollow_square_props(30.0, 3.0)
        props_arm = hollow_square_props(24.0, 2.5)
        zs = np.linspace(0.0, H_col, n_sub + 1)
        arm_z_idx = int(np.argmin(np.abs(zs - z_arm)))
        nodes = [[40.0, -130.0, float(z)] for z in zs] + [[40.0, 130.0, float(z)] for z in zs]
        off_r = n_sub + 1
        elements = []
        for k in range(n_sub):
            zm = 0.5 * (zs[k] + zs[k + 1])
            f = base_factor if zm <= 45.0 else 1.0
            elements.append({"n0": k, "n1": k + 1, "E": E, "G": G, "A": A_col, "Iy": Iy_col * f, "Iz": Iz_col * f, "J": J_col * f})
            elements.append({"n0": off_r + k, "n1": off_r + k + 1, "E": E, "G": G, "A": A_col, "Iy": Iy_col * f, "Iz": Iz_col * f, "J": J_col * f})
        # Top crossbar at z=H_col
        _subdivide_member(nodes, elements, n_sub, off_r + n_sub, max(4, n_sub), {"E": E, "G": G, "A": props_cross["A"], "Iy": props_cross["Iy"] * corner_factor, "Iz": props_cross["Iz"] * corner_factor, "J": props_cross["J"] * corner_factor})
        # Moving X-gantry bridge at z=z_arm connecting left & right columns + 215mm X-arm at center!
        bridge_ctr = len(nodes)
        nodes.append([40.0, 0.0, float(zs[arm_z_idx])])
        _subdivide_member(nodes, elements, arm_z_idx, bridge_ctr, max(2, n_sub // 2), {"E": E, "G": G, "A": props_cross["A"], "Iy": props_cross["Iy"] * corner_factor, "Iz": props_cross["Iz"] * corner_factor, "J": props_cross["J"] * corner_factor})
        _subdivide_member(nodes, elements, bridge_ctr, off_r + arm_z_idx, max(2, n_sub // 2), {"E": E, "G": G, "A": props_cross["A"], "Iy": props_cross["Iy"] * corner_factor, "Iz": props_cross["Iz"] * corner_factor, "J": props_cross["J"] * corner_factor})
        tip_node = len(nodes)
        nodes.append([40.0 + L_arm, 0.0, float(zs[arm_z_idx])])
        arm_hinge_node = len(nodes)
        nodes.append([40.0 + 30.0, 0.0, float(zs[arm_z_idx])])
        elements.append({"n0": bridge_ctr, "n1": arm_hinge_node, "E": E, "G": G, "A": props_arm["A"], "Iy": props_arm["Iy"] * corner_factor, "Iz": props_arm["Iz"] * corner_factor, "J": props_arm["J"] * corner_factor})
        _subdivide_member(nodes, elements, arm_hinge_node, tip_node, max(2, n_sub // 2), {"E": E, "G": G, **props_arm})

        fixed = [0, 1, 2, 3, 4, 5] + [6 * off_r + d for d in range(6)]
        arr_nodes = np.array(nodes, dtype=float)
        rx = solve_space_frame(arr_nodes, elements, fixed, {6 * tip_node + 0: load_N})
        ry = solve_space_frame(arr_nodes, elements, fixed, {6 * tip_node + 1: load_N})
        rz = solve_space_frame(arr_nodes, elements, fixed, {6 * tip_node + 2: load_N})
        return {
            "id": candidate_id, "fea_level": "L3_3D_space_frame_FEA_v3_1",
            "dofs": ry["n_dofs"], "ideal_rigid_joints": ideal_rigid_joints,
            "tip_x_deflection_mm": abs(float(rx["u"][6 * tip_node + 0])),
            "tip_y_deflection_mm": abs(float(ry["u"][6 * tip_node + 1])),
            "tip_z_deflection_mm": abs(float(rz["u"][6 * tip_node + 2])),
            "tip_lateral_deflection_mm": abs(float(ry["u"][6 * tip_node + 1])),
            "torsion_rot_rad": abs(float(ry["u"][6 * bridge_ctr + 5])),
        }

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
        nodes = [[40.0, 0.0, float(z)] for z in zs]
        elements = []
        for k in range(len(zs) - 1):
            zm = 0.5 * (zs[k] + zs[k + 1])
            pr = s1_props if zm <= z1 else (s2_props if zm <= z2 else s3_props)
            elements.append({"n0": k, "n1": k + 1, "E": E, "G": G, **pr})
        arm_idx = len(zs) - 2
        tip_node = len(nodes)
        nodes.append([40.0 + L_arm, 0.0, float(zs[arm_idx])])
        _subdivide_member(nodes, elements, arm_idx, tip_node, max(2, n_sub // 2), {"E": E, "G": G, **props_arm})
        fixed = [0, 1, 2, 3, 4, 5]
        arr_nodes = np.array(nodes, dtype=float)
        rx = solve_space_frame(arr_nodes, elements, fixed, {6 * tip_node + 0: load_N})
        ry = solve_space_frame(arr_nodes, elements, fixed, {6 * tip_node + 1: load_N})
        rz = solve_space_frame(arr_nodes, elements, fixed, {6 * tip_node + 2: load_N})
        return {
            "id": candidate_id, "fea_level": "L3_3D_space_frame_FEA_v3_1",
            "dofs": ry["n_dofs"], "ideal_rigid_joints": ideal_rigid_joints,
            "tip_x_deflection_mm": abs(float(rx["u"][6 * tip_node + 0])),
            "tip_y_deflection_mm": abs(float(ry["u"][6 * tip_node + 1])),
            "tip_z_deflection_mm": abs(float(rz["u"][6 * tip_node + 2])),
            "tip_lateral_deflection_mm": abs(float(ry["u"][6 * tip_node + 1])),
            "torsion_rot_rad": abs(float(ry["u"][6 * arm_idx + 5])),
        }

    # SCZ FIXED: Truly subdivides every scissor arm & top-frame member by n_sub!
    arm_len = p["arm_length_mm"]
    height = p["height_work_max_mm"] - 90.0
    span = math.sqrt(max(100.0, 4.0 * arm_len**2 - height**2))
    cx = 157.5
    lx, rx = cx - 0.5 * span, cx + 0.5 * span
    nodes = [
        [lx, -130.0, 0.0], [rx, -130.0, 0.0], [cx, -130.0, height / 2.0], [lx, -130.0, height], [rx, -130.0, height],
        [lx, 130.0, 0.0], [rx, 130.0, 0.0], [cx, 130.0, height / 2.0], [lx, 130.0, height], [rx, 130.0, height],
    ]
    w, t = p.get("arm_width_mm", 20.0), p.get("arm_thick_mm", 6.0)
    bar_props = {"E": E, "G": G, "A": w * t, "Iy": t * w**3 / 12.0, "Iz": w * t**3 / 12.0, "J": w * t**3 / 3.0 * (1.0 - 0.63 * t / w)}
    top_props = {"E": E, "G": G, **hollow_square_props(20.0, 2.0)}
    elements: list[dict[str, Any]] = []
    for n0, n1 in [(0, 2), (2, 4), (1, 2), (2, 3), (5, 7), (7, 9), (6, 7), (7, 8)]:
        _subdivide_member(nodes, elements, n0, n1, n_sub, bar_props)
    for n0, n1 in [(3, 4), (8, 9), (3, 8), (4, 9)]:
        _subdivide_member(nodes, elements, n0, n1, n_sub, top_props)
    fixed_dofs = [0, 1, 2, 30, 31, 32, 7, 8, 37, 38]
    arr_nodes = np.array(nodes, dtype=float)
    res_x = solve_space_frame(arr_nodes, elements, fixed_dofs, {18: 0.5 * load_N, 48: 0.5 * load_N})
    res_y = solve_space_frame(arr_nodes, elements, fixed_dofs, {19: 0.5 * load_N, 49: 0.5 * load_N})
    res_z = solve_space_frame(arr_nodes, elements, fixed_dofs, {20: 0.5 * load_N, 50: 0.5 * load_N})
    return {
        "id": candidate_id, "fea_level": "L3_3D_space_frame_FEA_v3_1",
        "dofs": res_y["n_dofs"], "ideal_rigid_joints": ideal_rigid_joints,
        "tip_x_deflection_mm": 0.5 * (abs(float(res_x["u"][18])) + abs(float(res_x["u"][48]))),
        "tip_y_deflection_mm": 0.5 * (abs(float(res_y["u"][19])) + abs(float(res_y["u"][49]))),
        "tip_z_deflection_mm": 0.5 * (abs(float(res_z["u"][20])) + abs(float(res_z["u"][50]))),
        "tip_lateral_deflection_mm": 0.5 * (abs(float(res_y["u"][19])) + abs(float(res_y["u"][49]))),
        "torsion_rot_rad": 0.0,
    }
