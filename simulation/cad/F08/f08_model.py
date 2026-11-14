"""F08 folded concept assembly.

Process: conceptual assembly; load-bearing joints require machined metal after measurement.
Material: aluminium extrusion and unspecified metal joint hardware.
Interfaces: every pivot, slot, lock and accessory dimension is an unchecked concept assumption.
先抬升并向后移动枢轴，向底座后方翻折；外伸托架计入包络。
"""
from build123d import *

POLYGONS_MM = [('base', 347.0, [(315.0, 0.0), (315.0, 20.0), (0.0, 20.0), (0.0, 0.0)]), ('bed', 180.0, [(250.0, 40.0), (250.0, 60.0), (70.0, 60.0), (70.0, 40.0)]), ('column', 40.0, [(10.0, 40.00002), (-335.0, 40.00002), (-335.0, 20.00002), (10.0, 20.00002)])]
EXPECTED_BOUNDS_MM = (-335.000001769342, 0.0, 315.0, 60.0)


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
