"""V3.1 Final 3D OBB geometry, 15-axis SAT, and conservative rotational + moving-vs-moving swept collision."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

SAT_TOL = 1e-9


def rot_x(deg: float) -> np.ndarray:
    r = math.radians(deg)
    c, s = math.cos(r), math.sin(r)
    return np.array([[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]], dtype=float)


def rot_y(deg: float) -> np.ndarray:
    r = math.radians(deg)
    c, s = math.cos(r), math.sin(r)
    return np.array([[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]], dtype=float)


def rot_z(deg: float) -> np.ndarray:
    r = math.radians(deg)
    c, s = math.cos(r), math.sin(r)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]], dtype=float)


def _rotation_angle(Ra: np.ndarray, Rb: np.ndarray) -> float:
    dR = Ra.T @ Rb
    tr = float(np.clip(0.5 * (np.trace(dR) - 1.0), -1.0, 1.0))
    return math.acos(tr)


def _screw_interp_pose(ca: np.ndarray, Ra: np.ndarray, cb: np.ndarray, Rb: np.ndarray, u: float) -> tuple[np.ndarray, np.ndarray]:
    """Exact Chasles screw / circular-arc rigid-body pose interpolation from (ca, Ra) to (cb, Rb)."""
    dR = Rb @ Ra.T
    tr = float(np.clip(0.5 * (np.trace(dR) - 1.0), -1.0, 1.0))
    angle = math.acos(tr)
    if angle < 1e-7:
        return (1.0 - u) * ca + u * cb, Ra
    axis = np.array([dR[2, 1] - dR[1, 2], dR[0, 2] - dR[2, 0], dR[1, 0] - dR[0, 1]], dtype=float)
    norm = float(np.linalg.norm(axis))
    if norm < 1e-12:
        return (1.0 - u) * ca + u * cb, Ra
    w = axis / norm
    dc = cb - ca
    dc_par = float(np.dot(dc, w)) * w
    dc_perp = dc - dc_par
    # Solve (R(angle) - I) r0 = dc_perp for r0 in plane perp to w:
    # r0 = -0.5 * dc_perp - (0.5 / tan(angle/2)) * (w x dc_perp)
    tan_half = math.tan(0.5 * angle)
    if abs(tan_half) < 1e-9:
        c_u = (1.0 - u) * ca + u * cb
    else:
        r0 = -0.5 * dc_perp - (0.5 / tan_half) * np.cross(w, dc_perp)
        pivot = ca - r0
        th = u * angle
        K = np.array([[0.0, -w[2], w[1]], [w[2], 0.0, -w[0]], [-w[1], w[0], 0.0]], dtype=float)
        R_u = np.eye(3) + math.sin(th) * K + (1.0 - math.cos(th)) * (K @ K)
        c_u = pivot + R_u @ r0 + u * dc_par
    th = u * angle
    K = np.array([[0.0, -w[2], w[1]], [w[2], 0.0, -w[0]], [-w[1], w[0], 0.0]], dtype=float)
    R_u = np.eye(3) + math.sin(th) * K + (1.0 - math.cos(th)) * (K @ K)
    return c_u, R_u @ Ra


def _rodrigues_interp(Ra: np.ndarray, Rb: np.ndarray, u: float) -> np.ndarray:
    dR = Ra.T @ Rb
    tr = float(np.clip(0.5 * (np.trace(dR) - 1.0), -1.0, 1.0))
    angle = math.acos(tr)
    if angle < 1e-9:
        return Ra
    axis = np.array([dR[2, 1] - dR[1, 2], dR[0, 2] - dR[2, 0], dR[1, 0] - dR[0, 1]], dtype=float)
    norm = float(np.linalg.norm(axis))
    if norm < 1e-12:
        return Ra
    axis /= norm
    theta = u * angle
    K = np.array([[0.0, -axis[2], axis[1]], [axis[2], 0.0, -axis[0]], [-axis[1], axis[0], 0.0]], dtype=float)
    R_step = np.eye(3) + math.sin(theta) * K + (1.0 - math.cos(theta)) * (K @ K)
    return Ra @ R_step


@dataclass
class OBB:
    name: str
    center: np.ndarray
    axes: np.ndarray
    half_extents: np.ndarray
    group: str = "moving"
    color: str = "#2563EB"

    @classmethod
    def from_bounds(
        cls, name: str, x0: float, y0: float, z0: float, x1: float, y1: float, z1: float,
        group: str = "moving", color: str = "#2563EB", hollow_inner_half: tuple[float, float] | None = None,
    ) -> "OBB":
        cx, cy, cz = 0.5 * (x0 + x1), 0.5 * (y0 + y1), 0.5 * (z0 + z1)
        hx = max(1e-6, 0.5 * abs(x1 - x0))
        hy = max(1e-6, 0.5 * abs(y1 - y0))
        hz = max(1e-6, 0.5 * abs(z1 - z0))
        return cls(name=name, center=np.array([cx, cy, cz], dtype=float), axes=np.eye(3, dtype=float), half_extents=np.array([hx, hy, hz], dtype=float), group=group, color=color)

    def transformed(self, rotation: np.ndarray | None = None, origin: np.ndarray | None = None, translation: np.ndarray | None = None) -> "OBB":
        R = np.eye(3) if rotation is None else rotation
        orig = np.zeros(3) if origin is None else origin
        trans = np.zeros(3) if translation is None else translation
        return OBB(
            name=self.name, center=orig + R @ (self.center - orig) + trans, axes=R @ self.axes,
            half_extents=self.half_extents.copy(), group=self.group, color=self.color,
        )

    def corners(self) -> np.ndarray:
        signs = np.array([
            [-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1],
            [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1],
        ], dtype=float)
        return self.center[None, :] + (signs * self.half_extents[None, :]) @ self.axes.T

    def aabb(self) -> tuple[np.ndarray, np.ndarray]:
        c = self.corners()
        return np.min(c, axis=0), np.max(c, axis=0)


def obb_sat_distance(a: OBB, b: OBB) -> tuple[bool, float, float]:
    t_vec = b.center - a.center
    A, B = a.axes, b.axes
    ea, eb = a.half_extents, b.half_extents
    R = A.T @ B
    abs_R = np.abs(R) + 1e-12

    min_overlap = float("inf")
    max_gap = -float("inf")
    colliding = True

    for i in range(3):
        ra = ea[i]
        rb = float(eb @ abs_R[i, :])
        dist = abs(float(t_vec @ A[:, i]))
        ov = (ra + rb) - dist
        if ov <= SAT_TOL:
            colliding = False
            max_gap = max(max_gap, max(0.0, -ov))
        else:
            min_overlap = min(min_overlap, ov)

    for j in range(3):
        ra = float(ea @ abs_R[:, j])
        rb = eb[j]
        dist = abs(float(t_vec @ B[:, j]))
        ov = (ra + rb) - dist
        if ov <= SAT_TOL:
            colliding = False
            max_gap = max(max_gap, max(0.0, -ov))
        else:
            min_overlap = min(min_overlap, ov)

    for i in range(3):
        for j in range(3):
            axis = np.cross(A[:, i], B[:, j])
            norm = float(np.linalg.norm(axis))
            if norm < 1e-8:
                continue
            axis /= norm
            ra = float(np.sum(ea * np.abs(A.T @ axis)))
            rb = float(np.sum(eb * np.abs(B.T @ axis)))
            dist = abs(float(t_vec @ axis))
            ov = (ra + rb) - dist
            if ov <= SAT_TOL:
                colliding = False
                max_gap = max(max_gap, max(0.0, -ov))
            else:
                min_overlap = min(min_overlap, ov)

    if colliding:
        return True, float(max(0.0, min_overlap)), 0.0
    return False, 0.0, float(max(0.0, max_gap))


def swept_obb_vs_obb(
    a0: OBB, a1: OBB, b0: OBB, b1: OBB,
    step_bound_mm: float = 1.5,
    angle_bound_deg: float = 3.0,
    max_substeps: int = 256,
) -> dict:
    """Conservative continuous swept collision between TWO moving (or moving vs fixed) OBBs.

    - Subdivides based on BOTH linear corner displacement AND rotation angle (never uses endpoint-only AABB!).
    - On each sub-interval, interpolates center + SO(3) geodesic rotation for BOTH A and B,
      and inflates half_extents by conservative half-substep displacement + rotational sagitta.
    - Returns status in {'PASS', 'FAIL', 'UNRESOLVED'}, max_penetration_mm, min_clearance_mm, n_substeps.
    """
    disp_a = float(np.max(np.linalg.norm(a1.corners() - a0.corners(), axis=1)))
    disp_b = float(np.max(np.linalg.norm(b1.corners() - b0.corners(), axis=1)))
    ang_a = _rotation_angle(a0.axes, a1.axes)
    ang_b = _rotation_angle(b0.axes, b1.axes)
    total_disp = disp_a + disp_b
    max_ang_deg = math.degrees(max(ang_a, ang_b))

    if total_disp < 1e-9 and max_ang_deg < 1e-6:
        col, pen, clr = obb_sat_distance(a0, b0)
        return {"status": "FAIL" if col else "PASS", "colliding": col, "penetration_mm": pen, "clearance_mm": clr, "n_substeps": 1}

    n_disp = int(math.ceil(total_disp / step_bound_mm))
    n_ang = int(math.ceil(max_ang_deg / angle_bound_deg))
    n_sub = max(1, n_disp, n_ang)
    unresolved = n_sub > max_substeps
    n_sub = min(max_substeps, n_sub)

    # Conservative half-substep margin + rotational sagitta: r*(1 - cos(dtheta/2))
    r_a = float(np.linalg.norm(a0.half_extents))
    r_b = float(np.linalg.norm(b0.half_extents))
    sag_a = r_a * (1.0 - math.cos(0.5 * ang_a / n_sub))
    sag_b = r_b * (1.0 - math.cos(0.5 * ang_b / n_sub))
    margin_a = 0.5 * (disp_a / n_sub) + sag_a
    margin_b = 0.5 * (disp_b / n_sub) + sag_b

    max_pen = 0.0
    min_clr = float("inf")
    any_col = False

    for s in range(n_sub):
        u = (s + 0.5) / n_sub
        ca_u, Ra_u = _screw_interp_pose(a0.center, a0.axes, a1.center, a1.axes, u)
        cb_u, Rb_u = _screw_interp_pose(b0.center, b0.axes, b1.center, b1.axes, u)
        sub_a = OBB(name=a0.name, center=ca_u, axes=Ra_u, half_extents=a0.half_extents + margin_a)
        sub_b = OBB(name=b0.name, center=cb_u, axes=Rb_u, half_extents=b0.half_extents + margin_b)
        col, pen, clr = obb_sat_distance(sub_a, sub_b)
        if col:
            any_col = True
            max_pen = max(max_pen, pen)
            min_clr = 0.0
        elif not any_col:
            min_clr = min(min_clr, clr)

    if any_col:
        status = "FAIL"
    elif unresolved:
        status = "UNRESOLVED"
    else:
        status = "PASS"

    return {
        "status": status,
        "colliding": any_col,
        "penetration_mm": float(max_pen),
        "clearance_mm": float(min_clr if min_clr < float("inf") else 0.0),
        "n_substeps": n_sub,
    }
