"""F08 optional planar motion card (1:2). Card plane = XY, pins along Z.
Layers: card z0..3, slider z3..6, column z6..9, arm z9..12.
Sequence: arm fold 90 -> lift 12.5 -> shift -37.5 -> rearward root fold -90."""
from __future__ import annotations

import math

from build123d import Box, Cylinder, Part, Pos, Rot, Location

from common_r1 import pin, clip, z_hole, rounded_slot_x, CLR_ROT, CLR_SLD

ROOT0 = (20.0, 13.0)
LIFT = 12.5
SHIFT = -37.5
COL_PIVOT = (7.5, 137.5)   # arm pivot in column local frame


def _l_slot(p: Part, x0, y0, x1, y1, x2, y2, w=3.4):
    """L-shaped through slot: vertical then horizontal."""
    v = Pos((x0 + x1) / 2, (y0 + y1) / 2, 1.5) * Box(w, abs(y1 - y0) + w, 3.02)
    h = Pos((x1 + x2) / 2, (y1 + y2) / 2, 1.5) * Box(abs(x2 - x1) + w, w, 3.02)
    return p - v - h


def build_card() -> Part:
    p = Pos(40, 87.5, 1.5) * Box(200, 175, 3)
    # root L-slot and parallel guide L-slot (+20 in y)
    p = _l_slot(p, 20, 13, 20, 25.5, -17.5, 25.5)
    p = _l_slot(p, 20, 33, 20, 45.5, -17.5, 45.5)
    # detent holes: 0 deg (guide slot end) and -90 deg
    p = p - Pos(-17.5, 45.5, 1.5) * z_hole(3.0, 4, CLR_SLD)
    p = p - Pos(-37.5, 25.5, 1.5) * z_hole(3.0, 4, CLR_SLD)
    # rear foot pivot + stowed/deployed lock holes
    p = p - Pos(-30, 3, 1.5) * z_hole(3.0, 4, CLR_ROT)
    p = p - Pos(-56, 3, 1.5) * z_hole(3.0, 4, CLR_SLD)
    p = p - Pos(-30, 29, 1.5) * z_hole(3.0, 4, CLR_SLD)
    # angle scale around final pivot (-17.5, 25.5), r=28, 0..-90 deg
    for a in range(0, -91, -15):
        r = math.radians(a)
        x = -17.5 + 28 * math.cos(r)
        y = 25.5 + 28 * math.sin(r)
        p = p - Pos(x, y, 2.6) * Rot(0, 0, a) * Box(4, 0.8, 1.0)
    # ground line engraving
    p = p - Pos(40, 0.8, 2.6) * Box(198, 0.8, 1.0)
    p.label = "F08-CARD"
    return p


def build_slider() -> Part:
    p = Pos(0, 0, 4.5) * Box(12, 12, 3)
    p = p + Pos(0, 0, 1.5) * Cylinder(1.5, 3)      # down into card slot
    up = Pos(0, 0, 9) * Cylinder(1.5, 6)           # up through column
    up = up - Pos(0, 0, 9.8) * (Cylinder(1.51, 1.0) - Cylinder(1.25, 1.02))
    p = p + up
    p.label = "F08-SLIDER"
    return p


def build_column() -> Part:
    ang = math.degrees(math.atan2(COL_PIVOT[1], COL_PIVOT[0]))
    ln = math.hypot(*COL_PIVOT)
    p = Pos(COL_PIVOT[0] / 2, COL_PIVOT[1] / 2, 7.5) * Rot(0, 0, ang) * Box(ln + 10, 12, 3)
    p = p + Pos(0, 0, 7.5) * Cylinder(6, 3)
    p = p + Pos(*COL_PIVOT, 7.5) * Cylinder(6, 3)
    p = p - Pos(0, 0, 7.5) * z_hole(3.0, 5, CLR_ROT)          # root on slider pin
    p = p - Pos(0, 20, 7.5) * z_hole(3.0, 5, CLR_ROT)         # removable guide pin
    p = p - Pos(*COL_PIVOT, 7.5) * z_hole(3.0, 5, CLR_ROT)    # arm pivot
    # arm lock holes (0 deg: +8x ; -90 deg: -8y about arm pivot)
    p = p - Pos(COL_PIVOT[0] + 8, COL_PIVOT[1], 7.5) * z_hole(3.0, 5, CLR_SLD)
    p = p - Pos(COL_PIVOT[0], COL_PIVOT[1] - 8, 7.5) * z_hole(3.0, 5, CLR_SLD)
    p.label = "F08-COL"
    return p


def build_arm() -> Part:
    p = Pos(107.5 / 2, 0, 10.5) * Box(107.5, 12, 3)
    t = Pos(-6, 0, 10.5) * Box(12, 12, 3) + Pos(0, 0, 10.5) * Cylinder(6, 3)
    p = p + t
    p = p - Pos(0, 0, 10.5) * z_hole(3.0, 5, CLR_ROT)
    p = p - Pos(8, 0, 10.5) * z_hole(3.0, 5, CLR_SLD)   # lock: 0 & -90
    p = p + Pos(55, 0, 10.5) * Box(25, 16, 3)           # toolhead marker
    p.label = "F08-ARM"
    return p


def build_foot() -> Part:
    p = Pos(-15, 0, 4.5) * Box(30, 10, 3)
    p = p + Pos(0, 0, 4.5) * Cylinder(5, 3)
    p = p - Pos(0, 0, 4.5) * z_hole(3.0, 5, CLR_ROT)
    p = p - Pos(-26, 0, 4.5) * z_hole(3.0, 5, CLR_SLD)  # deployed lock hole
    p.label = "F08-FOOT"
    return p


def f08_pins() -> list[tuple[str, Part, str, int]]:
    return [
        ("PIN3-L14", pin(3, 14), "PETG", 2),   # arm pivot + arm lock (from below, clip on top)
        ("PIN3-L12", pin(3, 12), "PETG", 1),   # guide pin
        ("PIN3-L10", pin(3, 10), "PETG", 1),   # foot
        ("CLIP3", clip(3), "PETG", 5),
    ]
