"""Headless assembly renderer (painter's algorithm, numpy+PIL). No GPU needed.
Produces PNG snapshots + motion GIF for visual review of ROUND1 assemblies."""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image, ImageDraw

import kinematics_r1 as K
from validate_r1 import placements, base_name, load_parts, ROOT, CAND_DIRS, rot_y, rot_z


def render_meshes(meshes: list[trimesh.Trimesh], size=(1100, 850), elev=22, azim=-55,
                  title="", bg=(248, 250, 252)) -> Image.Image:
    tris = []
    cols = []
    palette = [(2, 132, 199), (37, 99, 235), (14, 165, 233), (245, 158, 11),
               (100, 116, 139), (22, 163, 74), (219, 39, 119), (124, 58, 237)]
    for i, m in enumerate(meshes):
        v = m.vertices[m.faces]
        tris.append(v)
        c = palette[i % len(palette)]
        cols.append(np.tile(c, (len(v), 1)))
    if not tris:
        return Image.new("RGB", size, bg)
    V = np.concatenate(tris)
    C = np.concatenate(cols)
    # camera
    el, az = math.radians(elev), math.radians(azim)
    fwd = np.array([math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)])
    up0 = np.array([0, 0, 1.0])
    right = np.cross(fwd, up0)
    right /= np.linalg.norm(right)
    up = np.cross(right, fwd)
    center = V.reshape(-1, 3).mean(axis=0)
    Pc = V - center
    x = Pc @ right
    y = Pc @ up
    z = Pc @ fwd
    span = max(x.max() - x.min(), y.max() - y.min()) * 1.12
    s = min(size) / span
    cx, cy = size[0] / 2, size[1] / 2
    X = cx + x * s
    Y = cy - y * s
    # normals & shading
    n = np.cross(V[:, 1] - V[:, 0], V[:, 2] - V[:, 0])
    nl = np.linalg.norm(n, axis=1)
    nl[nl == 0] = 1
    n = n / nl[:, None]
    light = np.array([0.4, -0.5, 0.77])
    shade = 0.45 + 0.55 * np.clip(n @ light, 0, 1)
    order = np.argsort(z.mean(axis=1))
    img = Image.new("RGB", size, bg)
    dr = ImageDraw.Draw(img)
    for i in order:
        col = tuple(int(c * shade[i]) for c in C[i])
        pts = [(X[i, 0], Y[i, 0]), (X[i, 1], Y[i, 1]), (X[i, 2], Y[i, 2])]
        dr.polygon(pts, fill=col)
    if title:
        dr.text((14, 12), title, fill=(15, 23, 42))
    return img


def assembly_meshes(cand: str, parts, t: float):
    pl = placements(cand, t)
    out = []
    for pid, (pos, R) in pl.items():
        m = parts[base_name(pid)].copy()
        T = np.eye(4)
        T[:3, :3] = R
        T[:3, 3] = pos
        m.apply_transform(T)
        out.append(m)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cands", nargs="*", default=list(CAND_DIRS))
    ap.add_argument("--gif", action="store_true")
    args = ap.parse_args()
    for cand in args.cands:
        parts = load_parts(cand)
        out = ROOT / CAND_DIRS[cand] / "ASSEMBLY"
        out.mkdir(parents=True, exist_ok=True)
        for name, t in (("open", 0.0), ("armfold", 0.20), ("lifted", 0.42),
                        ("midfold", 0.70), ("folded", 1.0)):
            ms = assembly_meshes(cand, parts, t)
            img = render_meshes(ms, title=f"{cand}  t={t:.2f}  ({name})")
            img.save(out / f"view_{name}.png")
        # contact sheet
        imgs = [Image.open(out / f"view_{n}.png") for n in ("open", "armfold", "lifted", "midfold", "folded")]
        w, h = imgs[0].size
        sheet = Image.new("RGB", (w * 3, h * 2), (255, 255, 255))
        for i, im in enumerate(imgs):
            sheet.paste(im, ((i % 3) * w, (i // 3) * h))
        sheet.save(out / "contact_sheet.png")
        if args.gif:
            frames = []
            for t in np.linspace(0, 1, 48):
                ms = assembly_meshes(cand, parts, float(t))
                frames.append(render_meshes(ms, size=(640, 500), title=f"{cand} t={t:.2f}"))
            frames[0].save(out / "motion.gif", save_all=True, append_images=frames[1:],
                           duration=120, loop=0)
        print(f"[{cand}] snapshots -> {out}")


if __name__ == "__main__":
    main()
