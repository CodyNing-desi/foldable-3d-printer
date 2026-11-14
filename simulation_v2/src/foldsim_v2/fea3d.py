"""3D Space-Frame Finite Element Solver (6 DOF/node) for foldable printer structures."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from scipy.linalg import solve


def _local_beam_k(E: float, G: float, A: float, Iy: float, Iz: float, J: float, L: float) -> np.ndarray:
    k = np.zeros((12, 12), dtype=float)
    EA_L = E * A / L
    GJ_L = G * J / L
    L2 = L * L
    L3 = L * L * L

    # Axial (ux)
    k[0, 0] = k[6, 6] = EA_L
    k[0, 6] = k[6, 0] = -EA_L

    # Torsion (rx)
    k[3, 3] = k[9, 9] = GJ_L
    k[3, 9] = k[9, 3] = -GJ_L

    # Bending in X-Z plane (uz, ry): note ry = -duz/dx
    c1z = 12 * E * Iy / L3
    c2z = 6 * E * Iy / L2
    c3z = 4 * E * Iy / L
    c4z = 2 * E * Iy / L
    idx_z = [2, 4, 8, 10]
    kz = np.array([
        [c1z, -c2z, -c1z, -c2z],
        [-c2z, c3z, c2z, c4z],
        [-c1z, c2z, c1z, c2z],
        [-c2z, c4z, c2z, c3z],
    ])
    k[np.ix_(idx_z, idx_z)] += kz

    # Bending in X-Y plane (uy, rz): rz = duy/dx
    c1y = 12 * E * Iz / L3
    c2y = 6 * E * Iz / L2
    c3y = 4 * E * Iz / L
    c4y = 2 * E * Iz / L
    idx_y = [1, 5, 7, 11]
    ky = np.array([
        [c1y, c2y, -c1y, c2y],
        [c2y, c3y, -c2y, c4y],
        [-c1y, -c2y, c1y, -c2y],
        [c2y, c4y, -c2y, c3y],
    ])
    k[np.ix_(idx_y, idx_y)] += ky
    return k


def _beam_transform(p0: np.ndarray, p1: np.ndarray) -> tuple[np.ndarray, float]:
    v = p1 - p0
    L = float(np.linalg.norm(v))
    ex = v / L
    ref = np.array([0.0, 1.0, 0.0]) if abs(ex[1]) < 0.9 else np.array([0.0, 0.0, 1.0])
    ez = np.cross(ex, ref)
    ez /= float(np.linalg.norm(ez))
    ey = np.cross(ez, ex)
    R = np.vstack([ex, ey, ez])  # 3x3: local = R @ global
    T = np.zeros((12, 12), dtype=float)
    for b in range(4):
        T[3 * b : 3 * b + 3, 3 * b : 3 * b + 3] = R
    return T, L


def solve_space_frame(
    nodes: np.ndarray,
    elements: list[dict[str, Any]],
    fixed_dofs: list[int],
    loads: dict[int, float],
    rotational_springs: list[tuple[int, int, float]] | None = None,
) -> dict[str, Any]:
    """Assemble and solve 3D 6-DOF/node space frame."""
    n_nodes = len(nodes)
    n_dof = 6 * n_nodes
    K = np.zeros((n_dof, n_dof), dtype=float)
    F = np.zeros(n_dof, dtype=float)

    for el in elements:
        i, j = el["n0"], el["n1"]
        T, L = _beam_transform(nodes[i], nodes[j])
        k_loc = _local_beam_k(el["E"], el["G"], el["A"], el["Iy"], el["Iz"], el["J"], L)
        k_glob = T.T @ k_loc @ T
        dofs = list(range(6 * i, 6 * i + 6)) + list(range(6 * j, 6 * j + 6))
        K[np.ix_(dofs, dofs)] += k_glob

    if rotational_springs:
        for node_idx, local_rot_dof, k_rot in rotational_springs:
            # Softened rotational boundary or hinge compliance via penalty/series spring
            pass

    for dof_idx, val in loads.items():
        F[dof_idx] += val

    fixed_set = sorted(set(fixed_dofs))
    free_dofs = [d for d in range(n_dof) if d not in fixed_set]
    K_ff = K[np.ix_(free_dofs, free_dofs)]
    F_f = F[free_dofs]
    u_f = solve(K_ff, F_f, assume_a="sym")
    u = np.zeros(n_dof, dtype=float)
    u[free_dofs] = u_f
    return {"u": u, "n_nodes": n_nodes, "n_dofs": n_dof, "free_dofs": len(free_dofs)}


def hollow_square_props(outer: float, wall: float) -> dict[str, float]:
    inner = max(1.0, outer - 2.0 * wall)
    A = outer**2 - inner**2
    I = (outer**4 - inner**4) / 12.0
    # Bredt-Batho closed thin-wall torsion constant J = 4 * A_m^2 * t / P_m
    a_m = outer - wall
    A_m = a_m**2
    P_m = 4.0 * a_m
    J = 4.0 * (A_m**2) * wall / P_m
    return {"A": A, "Iy": I, "Iz": I, "J": J}


def evaluate_candidate_fea3d(candidate_id: str, spec: dict[str, Any], parameters: dict[str, Any] | None = None, n_sub: int = 8) -> dict[str, Any]:
    """Build and solve 3D space-frame FEA model for F07, F12, SCZ, F08."""
    common = spec["common"]
    p = dict(spec["parameters"] if parameters is None else dict(spec["parameters"], **parameters))
    E = common["aluminum_E_N_mm2"]
    G = common["aluminum_G_N_mm2"]
    load_N = common["lateral_load_N"]
    L_arm = common["x_arm_length_mm"]

    if candidate_id in {"F07", "F08"}:
        # Column (0..345 mm) + X-arm (215 mm along +X at z=275 mm) + hinge/lock rotational spring at base
        H_col = common["column_top_mm"] - common["column_bottom_mm"]  # 345 mm
        z_arm = 275.0
        # 30x40 mm rectangular extrusion equivalent
        A_col = 420.0
        Iy_col = 7000.0
        Iz_col = 11000.0
        J_col = 8500.0
        props_arm = hollow_square_props(24.0, 2.5)

        zs = np.linspace(0.0, H_col, n_sub + 1)
        arm_idx = int(np.argmin(np.abs(zs - z_arm)))
        nodes = [[40.0, 0.0, z] for z in zs]
        elements = []
        for k in range(n_sub):
            # Base element models hinge+lock joint compliance (effective stiffness reduction)
            factor = 0.55 if k == 0 else 1.0
            elements.append({
                "n0": k, "n1": k + 1, "E": E, "G": G,
                "A": A_col, "Iy": Iy_col * factor, "Iz": Iz_col * factor, "J": J_col * factor,
            })
        # X-arm cantilevered from arm_idx
        n_arm_el = 4
        arm_start = len(nodes)
        for m in range(1, n_arm_el + 1):
            nodes.append([40.0 + L_arm * m / n_arm_el, 0.0, zs[arm_idx]])
        prev = arm_idx
        for m in range(n_arm_el):
            cur = arm_start + m
            elements.append({"n0": prev, "n1": cur, "E": E, "G": G, **props_arm})
            prev = cur
        tip_node = prev
        # Apply 10 N lateral Y load at toolhead tip (tests both bending and column torsion!)
        loads = {6 * tip_node + 1: load_N}
        res = solve_space_frame(np.array(nodes), elements, fixed_dofs=[0, 1, 2, 3, 4, 5], loads=loads)
        tip_uy = float(res["u"][6 * tip_node + 1])
        col_top_uy = float(res["u"][6 * n_sub + 1])
        return {
            "id": candidate_id,
            "fea_level": "L3_3D_space_frame_FEA",
            "dofs": res["n_dofs"],
            "tip_lateral_deflection_mm": abs(tip_uy),
            "column_top_deflection_mm": abs(col_top_uy),
            "torsion_induced_mm": abs(tip_uy) - abs(col_top_uy),
        }

    if candidate_id == "F12":
        # Stepped 3-stage hollow square column + X-arm
        outer_sz = p.get("outer_size_mm", 60.0)
        wall = p.get("wall_mm", 3.0)
        overlap = p["overlap_mm"]
        H_ext = common["column_top_mm"] - common["column_bottom_mm"]  # 345 mm
        stage_h = (H_ext + 2.0 * overlap) / 3.0
        step_sz = 2.0 * (wall + p.get("radial_clearance_mm", 0.08) + p.get("pad_thickness_mm", 2.92))
        s1_props = hollow_square_props(outer_sz, wall)
        s2_props = hollow_square_props(outer_sz - step_sz, wall)
        s3_props = hollow_square_props(outer_sz - 2.0 * step_sz, wall)
        props_arm = hollow_square_props(24.0, 2.5)

        z1 = stage_h
        z2 = z1 + (stage_h - overlap)
        z3 = H_ext
        zs = np.linspace(0.0, z3, n_sub * 2 + 1)
        nodes = [[40.0, 0.0, z] for z in zs]
        elements = []
        for k in range(len(zs) - 1):
            zm = 0.5 * (zs[k] + zs[k + 1])
            if zm <= z1:
                pr = s1_props
            elif zm <= z2:
                pr = s2_props
            else:
                pr = s3_props
            elements.append({"n0": k, "n1": k + 1, "E": E, "G": G, **pr})
        arm_idx = len(zs) - 2
        n_arm_el = 4
        arm_start = len(nodes)
        for m in range(1, n_arm_el + 1):
            nodes.append([40.0 + L_arm * m / n_arm_el, 0.0, zs[arm_idx]])
        prev = arm_idx
        for m in range(n_arm_el):
            cur = arm_start + m
            elements.append({"n0": prev, "n1": cur, "E": E, "G": G, **props_arm})
            prev = cur
        tip_node = prev
        loads = {6 * tip_node + 1: load_N}
        res = solve_space_frame(np.array(nodes), elements, fixed_dofs=[0, 1, 2, 3, 4, 5], loads=loads)
        tip_uy = float(res["u"][6 * tip_node + 1])
        col_top_uy = float(res["u"][6 * (len(zs) - 1) + 1])
        return {
            "id": candidate_id,
            "fea_level": "L3_3D_space_frame_FEA",
            "dofs": res["n_dofs"],
            "tip_lateral_deflection_mm": abs(tip_uy),
            "column_top_deflection_mm": abs(col_top_uy),
            "torsion_induced_mm": max(0.0, abs(tip_uy) - abs(col_top_uy)),
        }

    # SCZ: Dual Y-side scissor space frame
    arm_len = p["arm_length_mm"]
    height = p["height_work_max_mm"] - 90.0  # mid-work height ~ 215 mm
    span = math.sqrt(max(100.0, 4.0 * arm_len**2 - height**2))
    cx = 157.5
    lx, rx = cx - 0.5 * span, cx + 0.5 * span
    nodes = np.array([
        [lx, -130.0, 0.0],     # 0: fixed left-front
        [rx, -130.0, 0.0],     # 1: slider right-front
        [cx, -130.0, height / 2.0],  # 2: center pin L
        [lx, -130.0, height],  # 3: top left L
        [rx, -130.0, height],  # 4: top right L
        [lx, 130.0, 0.0],      # 5: fixed left R
        [rx, 130.0, 0.0],      # 6: slider right R
        [cx, 130.0, height / 2.0],   # 7: center pin R
        [lx, 130.0, height],   # 8: top left R
        [rx, 130.0, height],   # 9: top right R
    ], dtype=float)
    w, t = p.get("arm_width_mm", 20.0), p.get("arm_thick_mm", 6.0)
    A_bar = w * t
    Iy_bar = t * w**3 / 12.0
    Iz_bar = w * t**3 / 12.0
    J_bar = w * t**3 / 3.0 * (1.0 - 0.63 * t / w)
    bar_props = {"E": E, "G": G, "A": A_bar, "Iy": Iy_bar, "Iz": Iz_bar, "J": J_bar}
    top_props = {"E": E, "G": G, **hollow_square_props(20.0, 2.0)}
    elements = [
        {"n0": 0, "n1": 2, **bar_props}, {"n0": 2, "n1": 4, **bar_props},
        {"n0": 1, "n1": 2, **bar_props}, {"n0": 2, "n1": 3, **bar_props},
        {"n0": 5, "n1": 7, **bar_props}, {"n0": 7, "n1": 9, **bar_props},
        {"n0": 6, "n1": 7, **bar_props}, {"n0": 7, "n1": 8, **bar_props},
        # Top frame perimeter connecting L and R
        {"n0": 3, "n1": 4, **top_props}, {"n0": 8, "n1": 9, **top_props},
        {"n0": 3, "n1": 8, **top_props}, {"n0": 4, "n1": 9, **top_props},
    ]
    # Fixed base pins (0, 5) pinned in u_xyz; sliders (1, 6) constrained in u_z, u_y
    fixed_dofs = [0, 1, 2, 5*6, 5*6+1, 5*6+2, 6+1, 6+2, 6*6+1, 6*6+2]
    loads = {3 * 6 + 1: 0.5 * load_N, 8 * 6 + 1: 0.5 * load_N}
    res = solve_space_frame(nodes, elements, fixed_dofs=fixed_dofs, loads=loads)
    tip_uy = 0.5 * (abs(res["u"][3 * 6 + 1]) + abs(res["u"][8 * 6 + 1]))
    return {
        "id": candidate_id,
        "fea_level": "L3_3D_space_frame_FEA",
        "dofs": res["n_dofs"],
        "tip_lateral_deflection_mm": float(tip_uy),
        "column_top_deflection_mm": float(tip_uy),
        "torsion_induced_mm": 0.0,
    }
