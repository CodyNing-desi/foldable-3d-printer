"""V3.2.1 3D OBB geometry, 15-axis SAT, and mathematically certified interval collision."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Protocol

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
    """Chasles screw interpolation. Returns (center_u, R_u, degenerate_180)."""
    dR = Rb @ Ra.T
    tr = float(np.clip(0.5 * (np.trace(dR) - 1.0), -1.0, 1.0))
    angle = math.acos(tr)
    if angle < 1e-7:
        return (1.0 - u) * ca + u * cb, Ra, False
    if angle >= math.pi - 1e-3:
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
        return cls(
            name=name,
            center=np.array([cx, cy, cz], dtype=float),
            axes=np.eye(3, dtype=float),
            half_extents=np.array([hx, hy, hz], dtype=float),
            group=group,
            color=color,
        )

    @property
    def bounding_radius(self) -> float:
        return float(np.linalg.norm(self.half_extents))

    def transformed(self, rotation: np.ndarray | None = None, origin: np.ndarray | None = None, translation: np.ndarray | None = None) -> "OBB":
        R = np.eye(3) if rotation is None else rotation
        orig = np.zeros(3) if origin is None else origin
        trans = np.zeros(3) if translation is None else translation
        return OBB(
            name=self.name,
            center=orig + R @ (self.center - orig) + trans,
            axes=R @ self.axes,
            half_extents=self.half_extents.copy(),
            group=self.group,
            color=self.color,
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
    """Exact 15-axis SAT returning (colliding, penetration_mm, clearance_lower_bound_mm)."""
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


class BoundedTrajectory(Protocol):
    """Protocol for trajectories with mathematically certified interval displacement bounds."""

    def pose(self, t: float) -> OBB:
        ...

    def interval_displacement_bound(self, ta: float, tb: float) -> float:
        """Return certified upper bound on max_{t in [ta, tb], x in OBB} ||x(t) - x((ta+tb)/2)||_2."""
        ...

    def bound_description(self) -> str:
        ...


@dataclass(frozen=True)
class StaticTrajectory:
    obb: OBB

    def pose(self, t: float) -> OBB:
        return self.obb

    def interval_displacement_bound(self, ta: float, tb: float) -> float:
        return 0.0

    def bound_description(self) -> str:
        return "static (v_max=0, w_max=0)"


@dataclass(frozen=True)
class LipschitzTrajectory:
    """Trajectory certified by global or analytical Lipschitz velocity + angular velocity bounds."""

    pose_fn: Callable[[float], OBB]
    v_center_max: float
    omega_max_rad: float
    r_obb: float
    label: str = "Lipschitz (v_max, w_max)"

    def pose(self, t: float) -> OBB:
        return self.pose_fn(t)

    def interval_displacement_bound(self, ta: float, tb: float) -> float:
        half_dt = 0.5 * abs(tb - ta)
        return (self.v_center_max + self.r_obb * self.omega_max_rad) * half_dt

    def bound_description(self) -> str:
        return f"{self.label}: v_max={self.v_center_max:.3f} mm/t, w_max={self.omega_max_rad:.4f} rad/t, r_obb={self.r_obb:.2f} mm"


@dataclass(frozen=True)
class IntervalBoundTrajectory:
    """Trajectory certified by an analytical interval-wise displacement bound function."""

    pose_fn: Callable[[float], OBB]
    bound_fn: Callable[[float, float], float]
    label: str = "Analytical interval bound"

    def pose(self, t: float) -> OBB:
        return self.pose_fn(t)

    def interval_displacement_bound(self, ta: float, tb: float) -> float:
        return float(self.bound_fn(ta, tb))

    def bound_description(self) -> str:
        return self.label


def verify_interval_collision(
    traj_a: BoundedTrajectory | Callable[[float], OBB],
    traj_b: BoundedTrajectory | Callable[[float], OBB],
    t0: float = 0.0,
    t1: float = 1.0,
    max_depth: int = 14,
    min_clearance_tol: float = 1e-5,
) -> dict:
    """Mathematically certified adaptive bisection continuous collision check.

    - NEVER infers motion upper bounds from finite sample points.
    - If either trajectory lacks a certified BoundedTrajectory bound interface, returns UNRESOLVED
      (unless a static check at endpoints/midpoint already detects collision -> FAIL).
    - Certifies an interval [ta, tb] as PASS iff SAT_clearance(mid) > U_a(ta, tb) + U_b(ta, tb) + tol.
    """
    has_bound_a = hasattr(traj_a, "interval_displacement_bound") and hasattr(traj_a, "pose")
    has_bound_b = hasattr(traj_b, "interval_displacement_bound") and hasattr(traj_b, "pose")

    pose_a = traj_a.pose if has_bound_a else traj_a  # type: ignore[assignment]
    pose_b = traj_b.pose if has_bound_b else traj_b  # type: ignore[assignment]

    a0, b0 = pose_a(t0), pose_b(t0)
    a1, b1 = pose_a(t1), pose_b(t1)
    pair_name = f"{a0.name} <-> {b0.name}"

    for t_chk, oa, ob in ((t0, a0, b0), (t1, a1, b1)):
        col, pen, _ = obb_sat_distance(oa, ob)
        if col:
            return {
                "status": "FAIL",
                "colliding": True,
                "pair": pair_name,
                "penetration_mm": float(pen),
                "clearance_mm": 0.0,
                "t_collision": float(t_chk),
                "evaluations": 2,
                "max_interval_bound_mm": 0.0,
                "tolerance_mm": float(min_clearance_tol),
                "certification_condition": "static_collision_detected",
                "bound_a": traj_a.bound_description() if has_bound_a else "NONE (uncertified callable)",
                "bound_b": traj_b.bound_description() if has_bound_b else "NONE (uncertified callable)",
            }

    if not (has_bound_a and has_bound_b):
        tm = 0.5 * (t0 + t1)
        col, pen, _ = obb_sat_distance(pose_a(tm), pose_b(tm))
        if col:
            return {
                "status": "FAIL",
                "colliding": True,
                "pair": pair_name,
                "penetration_mm": float(pen),
                "clearance_mm": 0.0,
                "t_collision": float(tm),
                "evaluations": 3,
                "max_interval_bound_mm": None,
                "tolerance_mm": float(min_clearance_tol),
                "certification_condition": "static_collision_at_midpoint_on_uncertified_callable",
                "bound_a": traj_a.bound_description() if has_bound_a else "NONE (uncertified callable)",
                "bound_b": traj_b.bound_description() if has_bound_b else "NONE (uncertified callable)",
            }
        return {
            "status": "UNRESOLVED",
            "colliding": False,
            "pair": pair_name,
            "penetration_mm": 0.0,
            "clearance_mm": 0.0,
            "t_collision": None,
            "evaluations": 3,
            "max_interval_bound_mm": None,
            "tolerance_mm": float(min_clearance_tol),
            "certification_condition": "missing_certified_motion_bound",
            "bound_a": traj_a.bound_description() if has_bound_a else "NONE (uncertified callable)",
            "bound_b": traj_b.bound_description() if has_bound_b else "NONE (uncertified callable)",
        }

    stack: list[tuple[float, float, int]] = [(float(t0), float(t1), 0)]
    min_cert_clr = float("inf")
    max_used_margin = 0.0
    any_unresolved = False
    evals = 2

    while stack:
        ta, tb, depth = stack.pop()
        tm = 0.5 * (ta + tb)
        am, bm = pose_a(tm), pose_b(tm)
        evals += 1

        col, pen, clr = obb_sat_distance(am, bm)
        if col:
            return {
                "status": "FAIL",
                "colliding": True,
                "pair": pair_name,
                "penetration_mm": float(pen),
                "clearance_mm": 0.0,
                "t_collision": float(tm),
                "evaluations": evals,
                "max_interval_bound_mm": float(max_used_margin),
                "tolerance_mm": float(min_clearance_tol),
                "certification_condition": "collision_detected_during_adaptive_bisection",
                "bound_a": traj_a.bound_description(),  # type: ignore[union-attr]
                "bound_b": traj_b.bound_description(),  # type: ignore[union-attr]
            }

        ua = float(traj_a.interval_displacement_bound(ta, tb))  # type: ignore[union-attr]
        ub = float(traj_b.interval_displacement_bound(ta, tb))  # type: ignore[union-attr]
        margin = ua + ub
        max_used_margin = max(max_used_margin, margin)

        if clr > margin + min_clearance_tol:
            min_cert_clr = min(min_cert_clr, clr - margin)
        elif depth >= max_depth:
            any_unresolved = True
        else:
            stack.append((tm, tb, depth + 1))
            stack.append((ta, tm, depth + 1))

    if any_unresolved:
        return {
            "status": "UNRESOLVED",
            "colliding": False,
            "pair": pair_name,
            "penetration_mm": 0.0,
            "clearance_mm": float(min_cert_clr if min_cert_clr < float("inf") else 0.0),
            "t_collision": None,
            "evaluations": evals,
            "max_interval_bound_mm": float(max_used_margin),
            "tolerance_mm": float(min_clearance_tol),
            "certification_condition": f"max_depth_{max_depth}_reached_without_proving_separation",
            "bound_a": traj_a.bound_description(),  # type: ignore[union-attr]
            "bound_b": traj_b.bound_description(),  # type: ignore[union-attr]
        }

    return {
        "status": "PASS",
        "colliding": False,
        "pair": pair_name,
        "penetration_mm": 0.0,
        "clearance_mm": float(min_cert_clr if min_cert_clr < float("inf") else 0.0),
        "t_collision": None,
        "evaluations": evals,
        "max_interval_bound_mm": float(max_used_margin),
        "tolerance_mm": float(min_clearance_tol),
        "certification_condition": "certified_clr_gt_Ua_plus_Ub_plus_tol_on_all_subintervals",
        "bound_a": traj_a.bound_description(),  # type: ignore[union-attr]
        "bound_b": traj_b.bound_description(),  # type: ignore[union-attr]
    }


def swept_obb_vs_obb(
    a0: OBB, a1: OBB, b0: OBB, b1: OBB,
    max_depth: int = 14,
) -> dict:
    """Endpoint-to-endpoint Chasles screw interpolation with analytical screw Lipschitz bounds.

    Returns UNRESOLVED for >=180 deg rotation without an explicit joint trajectory.
    """
    ang_a = _rotation_angle(a0.axes, a1.axes)
    ang_b = _rotation_angle(b0.axes, b1.axes)
    if ang_a >= math.pi - 1e-3 or ang_b >= math.pi - 1e-3:
        return {
            "status": "UNRESOLVED",
            "colliding": False,
            "pair": f"{a0.name} <-> {b0.name}",
            "penetration_mm": 0.0,
            "clearance_mm": 0.0,
            "t_collision": None,
            "evaluations": 0,
            "max_interval_bound_mm": None,
            "tolerance_mm": 1e-5,
            "certification_condition": "180_deg_rotation_requires_explicit_joint_trajectory",
        }

    # Exact Chasles screw center arc length bound: for rotation angle theta <= pi,
    # circular arc chord is ||c1-c0||, arc length is <= (theta / (2*sin(theta/2))) * ||c1-c0||
    def _screw_v_bound(c0: np.ndarray, c1: np.ndarray, ang: float) -> float:
        chord = float(np.linalg.norm(c1 - c0))
        if ang < 1e-7:
            return chord
        return chord * (ang / (2.0 * math.sin(0.5 * ang)))

    traj_a = LipschitzTrajectory(
        pose_fn=lambda u: OBB(a0.name, *_screw_interp_pose(a0.center, a0.axes, a1.center, a1.axes, u)[:2], a0.half_extents.copy()),
        v_center_max=_screw_v_bound(a0.center, a1.center, ang_a),
        omega_max_rad=ang_a,
        r_obb=a0.bounding_radius,
        label="Chasles screw",
    )
    traj_b = LipschitzTrajectory(
        pose_fn=lambda u: OBB(b0.name, *_screw_interp_pose(b0.center, b0.axes, b1.center, b1.axes, u)[:2], b0.half_extents.copy()),
        v_center_max=_screw_v_bound(b0.center, b1.center, ang_b),
        omega_max_rad=ang_b,
        r_obb=b0.bounding_radius,
        label="Chasles screw",
    )
    return verify_interval_collision(traj_a, traj_b, 0.0, 1.0, max_depth=max_depth)
