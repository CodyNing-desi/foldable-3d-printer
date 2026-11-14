"""3D OBB geometry, 15-axis SAT collision, conservative swept-envelope check, and STL/OBJ export."""

from __future__ import annotations

import math
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np


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
        cls,
        name: str,
        x0: float, y0: float, z0: float,
        x1: float, y1: float, z1: float,
        group: str = "moving",
        color: str = "#2563EB",
        hollow_inner_half: tuple[float, float] | None = None,
    ) -> "OBB":
        cx, cy, cz = 0.5 * (x0 + x1), 0.5 * (y0 + y1), 0.5 * (z0 + z1)
        hx = max(1e-6, 0.5 * abs(x1 - x0))
        hy = max(1e-6, 0.5 * abs(y1 - y0))
        hz = max(1e-6, 0.5 * abs(z1 - z0))
        inner = np.array([hollow_inner_half[0], hollow_inner_half[1], hz + 1.0], dtype=float) if hollow_inner_half else None
        return cls(
            name=name,
            center=np.array([cx, cy, cz], dtype=float),
            axes=np.eye(3, dtype=float),
            half_extents=np.array([hx, hy, hz], dtype=float),
            group=group,
            color=color,
            hollow_inner_half=inner,
        )

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
            hollow_inner_half=None if self.hollow_inner_half is None else self.hollow_inner_half.copy(),
        )

    def inflated(self, margin: float) -> "OBB":
        return OBB(
            name=self.name,
            center=self.center.copy(),
            axes=self.axes.copy(),
            half_extents=self.half_extents + margin,
            group=self.group,
            color=self.color,
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
        if ov <= 0.0:
            colliding = False
            max_gap = max(max_gap, -ov)
        else:
            min_overlap = min(min_overlap, ov)

    for j in range(3):
        ra = float(ea @ abs_R[:, j])
        rb = eb[j]
        dist = abs(float(t_vec @ B[:, j]))
        ov = (ra + rb) - dist
        if ov <= 0.0:
            colliding = False
            max_gap = max(max_gap, -ov)
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
            if ov <= 0.0:
                colliding = False
                max_gap = max(max_gap, -ov)
            else:
                min_overlap = min(min_overlap, ov)

    if colliding:
        return True, float(max(0.0, min_overlap)), 0.0
    return False, 0.0, float(max(0.0, max_gap))


def obb_triangles(obb: OBB) -> np.ndarray:
    if obb.hollow_inner_half is not None:
        return _hollow_tube_triangles(obb)
    c = obb.corners()
    faces = [
        (0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
        (0, 1, 5), (0, 5, 4), (2, 3, 7), (2, 7, 6),
        (1, 2, 6), (1, 6, 5), (3, 0, 4), (3, 4, 7),
    ]
    return np.array([[c[i], c[j], c[k]] for i, j, k in faces], dtype=float)


def _hollow_tube_triangles(obb: OBB) -> np.ndarray:
    hx, hy, hz = obb.half_extents
    ix, iy, _ = obb.hollow_inner_half
    ix = min(ix, hx - 0.5)
    iy = min(iy, hy - 0.5)
    tris = []
    for x0, x1, y0, y1 in [(-hx, hx, -hy, -iy), (-hx, hx, iy, hy), (-hx, -ix, -iy, iy), (ix, hx, -iy, iy)]:
        sub = OBB.from_bounds(obb.name, x0, y0, -hz, x1, y1, hz)
        sub_w = OBB(obb.name, obb.center + obb.axes @ sub.center, obb.axes, sub.half_extents)
        tris.append(obb_triangles(sub_w))
    return np.concatenate(tris, axis=0)


def export_stl_binary(obbs: Iterable[OBB], path: Path, header_text: str = "foldsim_v3 CAD") -> dict:
    all_tris = [obb_triangles(o) for o in obbs]
    tris = np.concatenate(all_tris, axis=0) if all_tris else np.zeros((0, 3, 3), dtype=float)
    path.parent.mkdir(parents=True, exist_ok=True)
    header = header_text.encode("ascii", errors="ignore")[:80].ljust(80, b" ")
    with path.open("wb") as f:
        f.write(header)
        f.write(struct.pack("<I", len(tris)))
        for tri in tris:
            v0, v1, v2 = tri
            n = np.cross(v1 - v0, v2 - v0)
            norm = np.linalg.norm(n)
            n = n / norm if norm > 1e-12 else np.zeros(3)
            f.write(struct.pack("<3f", *n))
            f.write(struct.pack("<3f", *v0))
            f.write(struct.pack("<3f", *v1))
            f.write(struct.pack("<3f", *v2))
            f.write(struct.pack("<H", 0))
    return {"path": str(path), "triangle_count": int(len(tris)), "solid_count": len(all_tris)}


def export_obj(obbs: Iterable[OBB], path: Path) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# foldsim_v3 parametric 3D assembly OBJ\n"]
    v_offset = 1
    obb_list = list(obbs)
    for o in obb_list:
        lines.append(f"o {o.name}\n")
        for tri in obb_triangles(o):
            for v in tri:
                lines.append(f"v {v[0]:.4f} {v[1]:.4f} {v[2]:.4f}\n")
            lines.append(f"f {v_offset} {v_offset+1} {v_offset+2}\n")
            v_offset += 3
    path.write_text("".join(lines), encoding="utf-8")
    return {"path": str(path), "object_count": len(obb_list)}
