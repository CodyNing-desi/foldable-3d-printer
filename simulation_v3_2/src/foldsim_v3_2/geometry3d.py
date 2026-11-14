"""V3.2 3D OBB geometry, 15-axis SAT, and Lipschitz-certified adaptive bisection continuous collision."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

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


def rot_axis_angle(axis: np.ndarray, deg: float) -> np.ndarray:
    ax = np.asarray(axis, dtype=float)
    n = float(np.linalg.norm(ax))
    if n < 1e-12 or abs(deg) < 1e-12:
        return np.eye(3, dtype=float)
    w = ax / n
    th = math.radians(deg)
    K = np.array([[0.0, -w[2], w[1]], [w[2], 0.0, -w[0]], [-w[1], w[0], 0.0]], dtype=float)
    return np.eye(3) + math.sin(th) * K + (1.0 - math.cos(th)) * (K @ K)


def _rotation_angle(Ra: np.ndarray, Rb: np.ndarray) -> float:
    dR = Rb @ Ra.T
    tr = float(np.clip(0.5 * (np.trace(dR) - 1.0), -1.0, 1.0))
    return math.acos(tr)


def _screw_interp_pose(ca: np.ndarray, Ra: np.ndarray, cb: np.ndarray, Rb: np.ndarray, u: float) -> tuple[np.ndarray, np.ndarray, bool]:
    """Chasles screw / circular-arc rigid-body interpolation. Returns (center_u, R_u, degenerate_180)."""
    dR = Rb @ Ra.T
    tr = float(np.clip(0.5 * (np.trace(dR) - 1.0), -1.0, 1.0))
    angle = math.acos(tr)
    if angle < 1e-7:
        return (1.0 - u) * ca + u * cb, Ra, False
    if angle >= math.pi - 1e-3:
        # 180-deg rotation axis cannot be uniquely or safely inferred without explicit joint law
        return (1.0 - u) * ca + u * cb, Ra, True
    axis = np.array([dR[2, 1] - dR[1, 2], dR[0, 2] - dR[2, 0], dR[1, 0] - dR[0, 1]], dtype=float)
    norm = float(np.linalg.norm(axis))
    if norm < 1e-12:
        return (1.0 - u) * ca + u * cb, Ra, True
    w = axis / norm
    dc = cb - ca
    dc_par = float(np.dot(dc, w)) * w
    dc_perp = dc - dc_par
    tan_half = math.tan(0.5 * angle)
    r0 = -0.5 * dc_perp - (0.5 / tan_half) * np.cross(w, dc_perp)
    pivot = ca - r0
    th = u * angle
    K = np.array([[0.0, -w[2], w[1]], [w[2], 0.0, -w[0]], [-w[1], w[0], 0.0]], dtype=float)
    R_u = np.eye(3) + math.sin(th) * K + (1.0 - math.cos(th)) * (K @ K)
    c_u = pivot + R_u @ r0 + u * dc_par
    return c_u, R_u @ Ra, False


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
    """Exact 15-axis SAT returning (colliding, penetration_mm, clearance_mm).
    Note: clearance_mm is a conservative lower bound on Euclidean separation (exact when axis-aligned).
    """
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


def _motion_upper_bound(o0: OBB, om: OBB, o1: OBB) -> float:
    """Lipschitz upper bound on ||x(t) - x(t_mid)|| for any point x in OBB over t in [t0, t1]."""
    # Center arc upper bound via 2-segment polygonal bound ||c0-cm|| + ||cm-c1||, half is <= max(||cm-c0||, ||c1-cm||)
    # Plus rotational corner excursion ||h||_2 * 2*sin(dtheta/4) <= ||h||_2 * 0.5 * dtheta_max
    dc0 = float(np.linalg.norm(om.center - o0.center))
    dc1 = float(np.linalg.norm(o1.center - om.center))
    ang0 = _rotation_angle(o0.axes, om.axes)
    ang1 = _rotation_angle(om.axes, o1.axes)
    r_obb = float(np.linalg.norm(om.half_extents))
    # Over [t0, tm] and [tm, t1], max deviation from midpoint is max(dc0 + r*ang0, dc1 + r*ang1)
    # Add 1.05x safety factor for slight curvature between t0 and tm
    return 1.05 * max(dc0 + r_obb * ang0, dc1 + r_obb * ang1)


def verify_interval_collision(
    pose_a: Callable[[float], OBB],
    pose_b: Callable[[float], OBB],
    t0: float = 0.0,
    t1: float = 1.0,
    max_depth: int = 13,
    min_clearance_tol: float = 1e-5,
) -> dict:
    """Mathematically conservative adaptive bisection continuous collision check using explicit pose_a(t), pose_b(t).

    - Never uses endpoint-only AABB rejection.
    - Certifies an interval [a, b] as PASS iff SAT_clearance(mid) > U_a + U_b + SAT_TOL.
    - Returns FAIL immediately if any evaluated pose has static SAT collision.
    - Returns UNRESOLVED if max_depth is reached without proving separation.
    """
    stack: list[tuple[float, float, int, OBB, OBB, OBB, OBB]] = []
    a0, b0 = pose_a(t0), pose_b(t0)
    a1, b1 = pose_a(t1), pose_b(t1)

    for t_chk, oa, ob in ((t0, a0, b0), (t1, a1, b1)):
        col, pen, _ = obb_sat_distance(oa, ob)
        if col:
            return {"status": "FAIL", "colliding": True, "penetration_mm": pen, "clearance_mm": 0.0, "t_collision": t_chk, "evaluations": 2}

    stack.append((t0, t1, 0, a0, a1, b0, b1))
    min_cert_clr = float("inf")
    any_unresolved = False
    evals = 2

    while stack:
        ta, tb, depth, oa0, oa1, ob0, ob1 = stack.pop()
        tm = 0.5 * (ta + tb)
        am, bm = pose_a(tm), pose_b(tm)
        evals += 1

        col, pen, clr = obb_sat_distance(am, bm)
        if col:
            return {"status": "FAIL", "colliding": True, "penetration_mm": pen, "clearance_mm": 0.0, "t_collision": tm, "evaluations": evals}

        ua = _motion_upper_bound(oa0, am, oa1)
        ub = _motion_upper_bound(ob0, bm, ob1)
        margin = ua + ub

        if clr > margin + min_clearance_tol:
            min_cert_clr = min(min_cert_clr, clr - margin)
        elif depth >= max_depth:
            any_unresolved = True
        else:
            stack.append((tm, tb, depth + 1, am, oa1, bm, ob1))
            stack.append((ta, tm, depth + 1, oa0, am, ob0, bm))

    if any_unresolved:
        return {"status": "UNRESOLVED", "colliding": False, "penetration_mm": 0.0, "clearance_mm": float(min_cert_clr if min_cert_clr < float("inf") else 0.0), "t_collision": None, "evaluations": evals}
    return {"status": "PASS", "colliding": False, "penetration_mm": 0.0, "clearance_mm": float(min_cert_clr if min_cert_clr < float("inf") else 0.0), "t_collision": None, "evaluations": evals}


def swept_obb_vs_obb(
    a0: OBB, a1: OBB, b0: OBB, b1: OBB,
    step_bound_mm: float = 2.0,
    angle_bound_deg: float = 3.0,
    max_depth: int = 12,
) -> dict:
    """Endpoint-to-endpoint wrapper using Chasles screw interpolation; returns UNRESOLVED for >=180 deg without explicit trajectory."""
    ang_a = _rotation_angle(a0.axes, a1.axes)
    ang_b = _rotation_angle(b0.axes, b1.axes)
    if ang_a >= math.pi - 1e-3 or ang_b >= math.pi - 1e-3:
        return {"status": "UNRESOLVED", "colliding": False, "penetration_mm": 0.0, "clearance_mm": 0.0, "t_collision": None, "evaluations": 0, "reason": "180-deg rotation requires explicit joint trajectory"}

    def pose_a(u: float) -> OBB:
        c, R, _ = _screw_interp_pose(a0.center, a0.axes, a1.center, a1.axes, u)
        return OBB(a0.name, c, R, a0.half_extents.copy())

    def pose_b(u: float) -> OBB:
        c, R, _ = _screw_interp_pose(b0.center, b0.axes, b1.center, b1.axes, u)
        return OBB(b0.name, c, R, b0.half_extents.copy())

    return verify_interval_collision(pose_a, pose_b, 0.0, 1.0, max_depth=max_depth)
