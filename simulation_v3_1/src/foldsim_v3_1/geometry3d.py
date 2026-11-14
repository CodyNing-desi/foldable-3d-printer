"""V3.1 3D OBB geometry, 15-axis SAT, and conservative adaptive swept-volume collision."""

from __future__ import annotations

import math
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

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


def _rodrigues_interp(Ra: np.ndarray, Rb: np.ndarray, u: float) -> np.ndarray:
    """Exact geodesic interpolation on SO(3) from Ra to Rb at u in [0, 1]."""
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
    hollow_inner_half: np.ndarray | None = None

    @classmethod
    def from_bounds(
        cls, name: str, x0: float, y0: float, z0: float, x1: float, y1: float, z1: float,
        group: str = "moving", color: str = "#2563EB", hollow_inner_half: tuple[float, float] | None = None,
    ) -> "OBB":
        cx, cy, cz = 0.5 * (x0 + x1), 0.5 * (y0 + y1), 0.5 * (z0 + z1)
        hx = max(1e-6, 0.5 * abs(x1 - x0))
        hy = max(1e-6, 0.5 * abs(y1 - y0))
        hz = max(1e-6, 0.5 * abs(z1 - z0))
        inner = np.array([hollow_inner_half[0], hollow_inner_half[1], hz + 1.0], dtype=float) if hollow_inner_half else None
        return cls(name=name, center=np.array([cx, cy, cz], dtype=float), axes=np.eye(3, dtype=float), half_extents=np.array([hx, hy, hz], dtype=float), group=group, color=color, hollow_inner_half=inner)

    def transformed(self, rotation: np.ndarray | None = None, origin: np.ndarray | None = None, translation: np.ndarray | None = None) -> "OBB":
        R = np.eye(3) if rotation is None else rotation
        orig = np.zeros(3) if origin is None else origin
        trans = np.zeros(3) if translation is None else translation
        return OBB(
            name=self.name, center=orig + R @ (self.center - orig) + trans, axes=R @ self.axes,
            half_extents=self.half_extents.copy(), group=self.group, color=self.color,
            hollow_inner_half=None if self.hollow_inner_half is None else self.hollow_inner_half.copy(),
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
    """Exact 15-axis SAT with explicit SAT_TOL separating numerical noise from real overlap."""
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


def swept_obb_vs_obstacle(m_a: OBB, m_b: OBB, obs: OBB, step_bound_mm: float = 2.0, inflate: bool = True) -> tuple[bool, float, float, int]:
    """Conservative adaptive swept collision check from m_a to m_b against obs.

    Subdivides until max corner displacement per sub-step <= step_bound_mm,
    and optionally inflates each sub-step OBB by 0.5 * sub_disp (conservative bound).
    Returns (colliding, max_penetration_mm, min_clearance_mm, n_substeps).
    """
    ca = m_a.corners()
    cb = m_b.corners()
    max_disp = float(np.max(np.linalg.norm(cb - ca, axis=1)))
    if max_disp < 1e-9:
        col, pen, clr = obb_sat_distance(m_a, obs)
        return col, pen, clr, 1

    # Broad-phase swept AABB reject
    swept_min = np.minimum(np.min(ca, axis=0), np.min(cb, axis=0)) - (0.5 * step_bound_mm if inflate else 0.0)
    swept_max = np.maximum(np.max(ca, axis=0), np.max(cb, axis=0)) + (0.5 * step_bound_mm if inflate else 0.0)
    obs_min, obs_max = obs.aabb()
    if np.any(swept_max < obs_min - SAT_TOL) or np.any(obs_max < swept_min - SAT_TOL):
        gap = float(np.linalg.norm(np.maximum(0.0, np.maximum(obs_min - swept_max, swept_min - obs_max))))
        return False, 0.0, gap, 1

    n_sub = min(128, max(1, int(math.ceil(max_disp / step_bound_mm))))
    margin = 0.5 * (max_disp / n_sub) if inflate else 0.0

    max_pen = 0.0
    min_clr = float("inf")
    any_col = False
    for s in range(n_sub):
        u = (s + 0.5) / n_sub
        ctr = (1.0 - u) * m_a.center + u * m_b.center
        axes = _rodrigues_interp(m_a.axes, m_b.axes, u)
        sub_obb = OBB(name=m_a.name, center=ctr, axes=axes, half_extents=m_a.half_extents + margin)
        col, pen, clr = obb_sat_distance(sub_obb, obs)
        if col:
            any_col = True
            max_pen = max(max_pen, pen)
            min_clr = 0.0
        elif not any_col:
            min_clr = min(min_clr, clr)

    return any_col, float(max_pen), float(min_clr if min_clr < float("inf") else 0.0), n_sub
