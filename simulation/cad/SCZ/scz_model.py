"""SCZ folded concept assembly.

Process: conceptual assembly; load-bearing joints require machined metal after measurement.
Material: aluminium extrusion and unspecified metal joint hardware.
Interfaces: every pivot, slot, lock and accessory dimension is an unchecked concept assumption.
理想等长剪刀、单输入同步；上框架随剪刀高度移动，目标打印高度 180 mm。
"""
from build123d import *

POLYGONS_MM = [('base', 347.0, [(315.0, 0.0), (315.0, 20.0), (0.0, 20.0), (0.0, 0.0)]), ('scissor_a', 30.0, [(307.89404, 70.96721), (308.77925, 65.03287), (7.10596, 20.03283), (6.22075, 25.96717)]), ('scissor_b', 30.0, [(6.22075, 65.03287), (7.10596, 70.96721), (308.77925, 25.96717), (307.89404, 20.03283)]), ('top_frame', 300.0, [(307.5, 68.00004), (307.5, 105.00004), (7.5, 105.00004), (7.5, 68.00004)])]
EXPECTED_BOUNDS_MM = (0.0, 0.0, 315.0, 105.00004008313482)


def interfaces() -> list[dict]:
    return []


def checks() -> list[dict]:
    min_x, min_z, max_x, max_z = EXPECTED_BOUNDS_MM
    return [
        {"feature": "expected folded X span", "bbox_x": {"min": 0.0, "max": max_x - min_x + 0.1}},
        {"feature": "expected folded Z span", "bbox_z": {"min": 0.0, "max": max_z - min_z + 0.1}},
    ]


def build() -> Part:
    with BuildPart() as assembly:
        for name, width_mm, points_mm in POLYGONS_MM:
            with BuildSketch(Plane.XZ):
                with BuildLine():
                    Polyline(points_mm + [points_mm[0]])
                make_face()
            extrude(amount=width_mm)
    return assembly.part
