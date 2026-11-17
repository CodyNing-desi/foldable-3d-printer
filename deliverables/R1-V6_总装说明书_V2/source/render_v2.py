"""V2 instruction-deck renderer: true-CAD exploded states, assembled states,
insertion arrows, joint closeups, pin reference and clip-method images.
No generative imagery. All geometry from ROUND1_DEMO_CAD STL + kinematics."""
import math
import sys
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image, ImageDraw

ROOT = Path(r"G:\我的云端硬盘\ROUND1_DEMO_CAD")
OUT = Path(__file__).parent / "assets" / "v2"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / "F07" / "CAD_SOURCE"))
import kinematics_r1 as K  # noqa: E402

OLD = (196, 202, 210)
NEW = {"F07": (208, 16, 18), "F09_L82": (0, 87, 168), "SCZ": (0, 133, 43)}
ORANGE = (245, 158, 11)
RED = (219, 39, 119)
SLATE = (100, 116, 139)


def rot_y(deg):
    r = math.radians(deg)
    c, s = math.cos(r), math.sin(r)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def placements(cand, t=0.0):
    pv = K.phase_values(cand, t)
    out = {}
    if cand in ("F09_L82", "F07"):
        for pid, val in K.gantry_placements(cand, pv["arm"], pv["lift"], pv["root"]).items():
            if pid != "ARM":
                pos, rot = val
                out[pid] = (np.array(pos, float), rot_y(rot))
        apos, arot = K.arm_placement(cand, pv["arm"], pv["lift"], pv["root"])
        out["ARM"] = (np.array(apos, float), rot_y(arot))
    else:
        for pid, (pos, rot) in K.scz_placements(pv["H"]).items():
            out[pid] = (np.array(pos, float), rot_y(rot))
        out["BED"] = (np.zeros(3), np.eye(3))
    return out


PARTS = {}
PINS = {}


def load_all():
    for cand in ("F07", "F09_L82", "SCZ"):
        PARTS[cand] = {}
        PINS[cand] = {}
        for f in sorted((ROOT / cand / "STL").glob("*.stl")):
            pid = f.stem.split("-", 1)[1]
            if pid.startswith(("PIN", "CLIP")):
                PINS[cand][pid] = trimesh.load(str(f), force="mesh")
            else:
                PARTS[cand][pid] = trimesh.load(str(f), force="mesh")
    for f in sorted((ROOT / "COUPONS_L4" / "STL").glob("*.stl")):
        PINS.setdefault("L4", {})[f.stem] = trimesh.load(str(f), force="mesh")


def xform(mesh, pos, R=None):
    m = mesh.copy()
    T = np.eye(4)
    if R is not None:
        T[:3, :3] = R
    T[:3, 3] = pos
    m.apply_transform(T)
    return m


def pid_mesh(cand, pid, offset=(0, 0, 0), t=0.0):
    pos, R = placements(cand, t)[pid]
    return xform(PARTS[cand][pid.split("_")[0]], pos + np.array(offset, float), R)


def joint(cand, pid, local, t=0.0):
    pos, R = placements(cand, t)[pid]
    return R @ np.array(local, float) + pos


def axis_z(axis):
    axis = np.array(axis, float)
    axis /= np.linalg.norm(axis)
    z = np.array([0.0, 0.0, 1.0])
    if np.allclose(axis, z):
        return np.eye(3)
    if np.allclose(axis, -z):
        return np.array([[1.0, 0, 0], [0, -1.0, 0], [0, 0, -1.0]])
    v = np.cross(z, axis)
    c = float(z @ axis)
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + vx + vx @ vx * (1 / (1 + c))


def pin_item(cand, pinid, center, axis, offset=(0, 0, 0), clip=False, clip_extra=0.0):
    """Headed pin centered on joint; optional C-clip at the tail groove."""
    mesh = PINS[cand][pinid]
    L = float(pinid.split("-L")[1])
    axis = np.array(axis, float)
    axis /= np.linalg.norm(axis)
    R = axis_z(axis)
    center = np.array(center, float) + np.array(offset, float)
    origin = center - axis * (L / 2)
    items = [(xform(mesh, origin, R), ORANGE)]
    if clip:
        clipid = "CLIP25" if pinid.startswith("PIN25") else "CLIP" + pinid.split("-")[0].replace("PIN", "")
        cm = PINS[cand].get(clipid)
        if cm is not None:
            cc = center + axis * (L / 2 - 1.5 + clip_extra)
            items.append((xform(cm, cc, R), RED))
    return items


def vertical_pin(cand, pinid, xy, z_head, offset=(0, 0, 0), clip=True):
    """Pin inserted downward: head at z_head, shaft along -Z."""
    mesh = PINS[cand][pinid]
    L = float(pinid.split("-L")[1])
    R = axis_z((0, 0, -1))
    origin = np.array([xy[0], xy[1], z_head]) + np.array(offset, float)
    items = [(xform(mesh, origin, R), ORANGE)]
    if clip:
        cm = PINS[cand]["CLIP" + pinid.split("-")[0].replace("PIN", "")]
        items.append((xform(cm, (xy[0], xy[1], z_head - L + 2.0), R), RED))
    return items


# ---------------- painter renderer with arrows ----------------
def render(mc, file, frame=None, arrows=(), size=(1200, 900), elev=22, azim=-55, bg=(248, 250, 252)):
    tris, cols = [], []
    for m, c in mc:
        v = m.vertices[m.faces]
        tris.append(v)
        cols.append(np.tile(c, (len(v), 1)))
    V = np.concatenate(tris)
    C = np.concatenate(cols)
    el, az = math.radians(elev), math.radians(azim)
    fwd = np.array([math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)])
    right = np.cross(fwd, np.array([0, 0, 1.0]))
    right /= np.linalg.norm(right)
    up = np.cross(right, fwd)
    center, span = frame if frame else (None, None)
    if center is None:
        center = V.reshape(-1, 3).mean(axis=0)
    Pc = V - center
    x, y, z = Pc @ right, Pc @ up, Pc @ fwd
    if span is None:
        span = max(np.ptp(x), np.ptp(y)) * 1.12
    s = min(size) / span
    X = size[0] / 2 + x * s
    Y = size[1] / 2 - y * s
    n = np.cross(V[:, 1] - V[:, 0], V[:, 2] - V[:, 0])
    nl = np.linalg.norm(n, axis=1)
    nl[nl == 0] = 1
    n = n / nl[:, None]
    shade = 0.45 + 0.55 * np.clip(n @ np.array([0.4, -0.5, 0.77]), 0, 1)
    order = np.argsort(z.mean(axis=1))
    img = Image.new("RGB", size, bg)
    dr = ImageDraw.Draw(img)
    for i in order:
        col = tuple(int(c * shade[i]) for c in C[i])
        dr.polygon([(X[i, 0], Y[i, 0]), (X[i, 1], Y[i, 1]), (X[i, 2], Y[i, 2])], fill=col)

    def proj(p):
        q = np.array(p, float) - center
        return (size[0] / 2 + (q @ right) * s, size[1] / 2 - (q @ up) * s)

    for a, b, col in arrows:
        xa, ya, xb, yb = *proj(a), *proj(b)
        dr.line((xa, ya, xb, yb), fill=col, width=8)
        ang = math.atan2(yb - ya, xb - xa)
        L, W = 26, 13
        p1 = (xb - L * math.cos(ang) + W * math.sin(ang), yb - L * math.sin(ang) - W * math.cos(ang))
        p2 = (xb - L * math.cos(ang) - W * math.sin(ang), yb - L * math.sin(ang) + W * math.cos(ang))
        dr.polygon([(xb, yb), p1, p2], fill=col)
    img.save(OUT / file)
    print("rendered", file, flush=True)


def scene(cand, name, existing, new, exploded=(), after_pins=(), frame=None, size=(1200, 900)):
    """exploded: tuples (kind, payload...) handled by caller-created items/arrows."""
    old_items = [(pid_mesh(cand, pid), OLD) for pid in existing]
    new_items = [(pid_mesh(cand, pid), NEW[cand]) for pid in new]
    render(old_items + new_items + list(after_pins), name + "_after.png", frame=frame, size=size)


def ref_frame(cand, existing, new, extra=()):
    meshes = [pid_mesh(cand, p) for p in list(existing) + list(new)] + [m for m, c in extra]
    V = np.concatenate([m.vertices for m in meshes])
    el, az = math.radians(22), math.radians(-55)
    fwd = np.array([math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)])
    right = np.cross(fwd, np.array([0, 0, 1.0]))
    right /= np.linalg.norm(right)
    up = np.cross(right, fwd)
    center = V.mean(axis=0)
    Pc = V - center
    span = max(np.ptp(Pc @ right), np.ptp(Pc @ up)) * 1.12
    return center, span


def detail(cand, name, items, center, span=45, arrows=(), elev=22, azim=-55):
    norm = [(it, OLD) if not isinstance(it, tuple) else it for it in items]
    render(norm, name + "_detail.png", frame=(np.array(center, float), span), arrows=arrows, size=(900, 800), elev=elev, azim=azim)


load_all()
print("loaded parts", flush=True)

# ---------- pin reference images (same scale for every pin) ----------
PIN_REFS = [
    ("F07", "PIN3-L14"), ("F09_L82", "PIN3-L18"), ("F09_L82", "PIN3-L22"),
    ("F07", "PIN3-L26"), ("F07", "PIN3-L34"), ("SCZ", "PIN4-L16"),
    ("SCZ", "PIN4-L18"), ("F07", "PIN5-L34"), ("SCZ", "PIN25-L10"),
]
for cand, pid in PIN_REFS:
    m = PINS[cand][pid]
    L = float(pid.split("-L")[1])
    c = m.bounds.mean(axis=0)
    render([(m, ORANGE)], f"pin_{pid}.png", frame=(c, 44), size=(600, 700))

# ---------- clip method images ----------
pin5 = PINS["F07"]["PIN5-L34"]
clip5 = PINS["F07"]["CLIP5"]
# groove closeup, clip approaching from +X, seated, wrong orientation
render([(pin5, ORANGE)], "clip_1_groove.png", frame=(np.array([0, 0, 31.0]), 16), size=(900, 800))
render([(pin5, ORANGE), (xform(clip5, (12, 0, 31.2)), RED)], "clip_2_approach.png",
       frame=(np.array([4, 0, 31.0]), 34), arrows=[((12, 0, 31.2), (0, 0, 31.2), RED)], size=(900, 800))
render([(pin5, ORANGE), (xform(clip5, (0, 0, 31.2)), RED)], "clip_3_seated.png",
       frame=(np.array([0, 0, 31.0]), 18), size=(900, 800))
render([(pin5, ORANGE), (xform(clip5, (0, 0, 24.0)), RED)], "clip_4_wrong.png",
       frame=(np.array([0, 0, 29.0]), 24), size=(900, 800))
print("PIN/CLIP REFERENCE DONE", flush=True)
