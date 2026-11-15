"""Demo-scale forward kinematics for ROUND1 candidates.

World frame: X forward (over bed), Y left-right, Z up. Units mm.
Link geometry = 0.5 * V3.2.1 full-scale. Joint local enlargements documented.

Phase order (matches V3.2.1 _phase_lift_fold, arm_fold_enabled=1):
  1) X-arm fold 0->90 deg (down)      t in [0.00, 0.20]
  2) lift 0->L (cosine ease)          t in [0.20, 0.40]
  3) shift (F08 only)                 t in [0.28, 0.45]
  4) root fold 0->90 deg              t in [0.45, 0.95]
  5) hold                             t in [0.95, 1.00]
SCZ: toolhead park t in [0,0.15]; H 135->22.5 linear t in [0.15,1].
"""
from __future__ import annotations

import math
from dataclasses import dataclass

S = 0.5

# ---- shared gantry (F09 / F07) demo geometry ----
BASE = dict(x=157.5, y=173.5, z=10.0)
BED = dict(x0=35.0, x1=125.0, y=90.0, z0=18.0, z1=28.0)  # demo bed envelope (top -2mm for arm clearance)
TOWER_Y = {"F09_L82": [-65.0, 65.0], "F07": [0.0]}
POST_X = 10.0
POST_DY = 15.0
POST_D = 5.0
TOWER_TOP = 65.0          # nominal (20+lift+28)*S ; cap locally +4
LIFT = {"F09_L82": 41.0, "F07": 37.5}   # 82*S, 75*S
CAR = dict(x0=6.0, x1=21.0, dy=19.0, z0=10.0, h=14.0)
PIVOT_X = 20.0            # 40*S
PIVOT_Z0 = 13.0           # 10 + 3 mm local hinge-boss enlargement (nominal 10)
COL = dict(dx=15.0, dy=20.0, top=169.5)   # tube local z10..169.5 above root pivot
ARM_PIVOT = (16.0, 0.0, 137.0)            # column local; +8.5mm fwd, +2.5mm up vs nominal (swing clearance)
ARM = dict(length=107.5, dy=16.0, dz=12.0)
TH = dict(x0=42.5, x1=67.5, dy=26.0, z0=-33.5, z1=-6.0)  # toolhead marker, arm local
XBAR = dict(z0=154.5, z1=169.5, dy=150.0)  # column-local frame, F09 only
BRG = dict(z0=127.0, z1=142.0, dy=110.0)

# ---- SCZ demo geometry (mirrored classic scissor: fixed right, slider left) ----
SCZ = dict(
    L=77.0,            # half arm length (full arm 154 = 2*154_full*S)
    h_fold=22.5,       # 45*S
    h_max=135.0,       # 270*S
    low_z=18.0,        # 24*S=12 nominal, +6mm so arm ends/post clevis clear base top (z10)
    fix_x=155.0,       # fixed bottom pivot & platform top pivot x
    yA=62.5,           # inner scissor plane (125*S)
    yB=71.0,           # outer plane (stagger 8.5 mm, full 10*S=5 enlarged for print)
    arm_len=160.0, arm_h=10.0, arm_t=3.0,
    arm_holes=(3.0, 80.0, 157.0),
    shaft_len=132.0, shaft_d=4.0,
    plat_dx=(-160.0, 5.0), plat_dy=152.0, plat_t=6.0, plat_dz=4.0,
)


def scz_span(H: float) -> float:
    return math.sqrt(max(0.0, 4 * SCZ["L"] ** 2 - H * H))


def ease(t: float) -> float:
    return 0.5 - 0.5 * math.cos(math.pi * min(1.0, max(0.0, t)))


def phase_values(cand: str, t: float) -> dict:
    """Continuous phase variables at normalized time t (V3.2.1 ordering)."""
    t = min(1.0, max(0.0, t))
    if cand == "SCZ":
        park = min(1.0, t / 0.15)
        frac = max(0.0, (t - 0.15) / 0.85)
        H = SCZ["h_max"] + (SCZ["h_fold"] - SCZ["h_max"]) * frac
        return dict(H=H, park=park)
    if cand == "F08_OPTIONAL":
        lift_max, shift_max = 12.5, -37.5
    else:
        lift_max, shift_max = LIFT[cand], 0.0
    arm = min(1.0, t / 0.20) * 90.0
    lift = lift_max * ease((t - 0.20) / 0.20)
    if cand == "F08_OPTIONAL":
        # V6: card L-slot requires lift THEN shift sequentially (no overlap),
        # otherwise the root pin moves diagonally and binds in the L-slot.
        shift = shift_max * ease((t - 0.40) / 0.15)
        root = -min(1.0, max(0.0, (t - 0.55) / 0.40)) * 90.0
    else:
        shift = shift_max * ease((t - 0.28) / 0.17)
        root = min(1.0, max(0.0, (t - 0.45) / 0.50)) * 90.0
    return dict(arm=arm, lift=lift, shift=shift, root=root)


def gantry_placements(cand: str, arm: float, lift: float, root: float) -> dict:
    """part_id -> (pos, rotY_deg) world placements. Local frames per build scripts."""
    out = {}
    out["BASE"] = ((0, 0, 0), 0.0)
    out["BED"] = ((0, 0, 0), 0.0)
    for i, yc in enumerate(TOWER_Y[cand]):
        out[f"TWR_{i}"] = ((POST_X, yc, 10.0), 0.0)
        out[f"CAR_{i}"] = ((CAR["x0"], yc, CAR["z0"] + lift), 0.0)
    if cand == "F09_L82":
        out["SYNC"] = ((0, 0, CAR["z0"] + lift), 0.0)
    for i, yc in enumerate(TOWER_Y[cand]):
        out[f"COL_{i}"] = ((PIVOT_X, yc, PIVOT_Z0 + lift), root)
    if cand == "F09_L82":
        out["XBAR"] = ((PIVOT_X, 0, PIVOT_Z0 + lift), root)
        out["BRG"] = ((PIVOT_X, 0, PIVOT_Z0 + lift), root)
    out["ARM"] = None  # composed below
    return out


def arm_placement(cand: str, arm: float, lift: float, root: float):
    """ARM world pose = root pose * arm-hinge offset * arm rotation."""
    px, py, pz = PIVOT_X, 0.0, PIVOT_Z0 + lift
    ax, ay, az = ARM_PIVOT
    # rotate arm pivot by root about Y through root pivot
    c, s = math.cos(math.radians(root)), math.sin(math.radians(root))
    wx = px + c * ax + s * az
    wz = pz - s * ax + c * az
    return (wx, py + ay, wz), root + arm


def scz_placements(H: float) -> dict:
    Sp = scz_span(H)
    sx = SCZ["fix_x"] - Sp
    hz = SCZ["low_z"] + H
    th = math.degrees(math.atan2(H, Sp))
    out = {}
    out["BASE"] = ((0, 0, 0), 0.0)
    for side, sgn in (("L", -1), ("R", 1)):
        yA, yB = sgn * SCZ["yA"], sgn * SCZ["yB"]
        out[f"ARM_A_{side}"] = ((sx, yA, SCZ["low_z"]), -th)
        out[f"ARM_B_{side}"] = ((SCZ["fix_x"], yB, SCZ["low_z"]), -(180.0 - th))
        out[f"SLB_{side}"] = ((sx, yA, SCZ["low_z"]), 0.0)
        out[f"SLT_{side}"] = ((sx, yB, hz), 0.0)
        out[f"POST_{side}"] = ((SCZ["fix_x"], yB, 0.0), 0.0)
    out["SHB"] = ((sx, 0, 4.0), 0.0)
    out["SHT"] = ((sx, 0, hz + 9.0), 0.0)   # V6: top shaft follows top sliders (sx), not fix_x
    out["PLAT"] = ((SCZ["fix_x"], 0, hz), 0.0)
    return out


def f08_placements(arm: float, lift: float, shift: float, root: float) -> dict:
    """Planar card: card plane = XY, pins along Z. root=(20+shift, 13+lift).
    World rot_y(a) maps to card rot_z(-a); world root=-90 (rear) -> card +90."""
    rx, ry = 20.0 + shift, 13.0 + lift
    cr = -root
    out = {}
    out["CARD"] = ((0, 0, 0), 0.0)
    out["SLIDER"] = ((rx, ry, 0.0), 0.0)
    out["COL"] = ((rx, ry, 0.0), cr)
    out["FOOT"] = ((-30.0, 3.0, 0.0), 0.0)
    c, s = math.cos(math.radians(cr)), math.sin(math.radians(cr))
    ax, ay = 7.5, 137.5
    out["ARM"] = ((rx + c * ax - s * ay, ry + s * ax + c * ay, 0.0), cr - arm)
    return out
