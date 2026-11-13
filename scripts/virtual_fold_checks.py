import math

def hinge_sweep(column, obstacles, pivot, angles_deg):
    from shapely.affinity import rotate
    from shapely.geometry import Polygon
    moving = Polygon(column)
    fixed = [Polygon(obstacle) for obstacle in obstacles]
    results = []
    for angle in angles_deg:
        pose = rotate(moving, angle, origin=pivot, use_radians=False)
        intersection = sum(pose.intersection(obstacle).area for obstacle in fixed)
        clearance = min((pose.distance(obstacle) for obstacle in fixed), default=math.inf)
        results.append({"angle_deg": angle, "intersection_area_mm2": intersection, "clearance_mm": clearance})
    return results

def scissor_state(arm_length_mm, horizontal_span_mm):
    height_squared = 4 * arm_length_mm**2 - horizontal_span_mm**2
    if height_squared <= 0:
        raise ValueError("Geometry is outside the ideal scissor model's reachable range")
    height = math.sqrt(height_squared)
    return {"height_mm": height, "dH_dS": -horizontal_span_mm / height}

def flip_torque_nmm(mass_kg, horizontal_com_distance_mm, gravity=9.81):
    return mass_kg * gravity * horizontal_com_distance_mm

def self_check():
    from shapely.geometry import Polygon
    assert Polygon([(0, 0), (1, 0), (1, 2), (0, 2)]).area == 2
    clear = hinge_sweep([(0, 0), (1, 0), (1, 2), (0, 2)], [[(2, 0), (3, 0), (3, 2), (2, 2)]], (0, 0), [0])
    assert clear[0]["intersection_area_mm2"] == 0
    collision = hinge_sweep([(0, 0), (1, 0), (1, 2), (0, 2)], [[(-2, 0), (-1, 0), (-1, 2), (-2, 2)]], (0, 0), [90])
    assert collision[0]["intersection_area_mm2"] > 0
    state = scissor_state(100, 150)
    assert math.isclose(state["height_mm"], 132.2875655532, rel_tol=1e-9)
    step = 1e-4
    finite = (scissor_state(100, 150 + step)["height_mm"] - scissor_state(100, 150 - step)["height_mm"]) / (2 * step)
    assert math.isclose(state["dH_dS"], finite, rel_tol=1e-6)
    assert math.isclose(flip_torque_nmm(2, 100), 1962.0)
    print("METHOD SELF-CHECK PASSED: rotation, collision, scissor mapping and flip torque")
    print("This is not evidence that any physical folding printer design is feasible")

if __name__ == "__main__":
    self_check()
