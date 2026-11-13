"""F12 folded concept assembly.

Process: conceptual assembly; load-bearing joints require machined metal after measurement.
Material: aluminium extrusion and unspecified metal joint hardware.
Interfaces: every pivot, slot, lock and accessory dimension is an unchecked concept assumption.
三级嵌套，完整展开后分级独立锁紧；仅工作位保证打印行程。
"""
from build123d import *

POLYGONS_MM = [('base', 347.0, [(315.0, 0.0), (315.0, 20.0), (0.0, 20.0), (0.0, 0.0)]), ('bed', 180.0, [(250.0, 40.0), (250.0, 60.0), (70.0, 60.0), (70.0, 40.0)]), ('stage_1', 40.0, [(50.0, 20.0), (50.0, 178.56033), (30.0, 178.56033), (30.0, 20.0)]), ('stage_2', 40.0, [(50.0, 20.0), (50.0, 178.56033), (30.0, 178.56033), (30.0, 20.0)]), ('stage_3', 40.0, [(50.0, 20.0), (50.0, 178.56033), (30.0, 178.56033), (30.0, 20.0)])]
EXPECTED_BOUNDS_MM = (0.0, 0.0, 315.0, 178.5603347130135)


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
