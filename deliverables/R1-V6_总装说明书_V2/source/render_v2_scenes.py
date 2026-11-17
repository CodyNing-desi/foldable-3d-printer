"""Scene definitions appended to render_v2 (run after its reference images)."""
from render_v2 import *  # noqa: F401,F403


def frame_items(items):
    V = np.concatenate([m.vertices for m, c in items])
    el, az = math.radians(22), math.radians(-55)
    fwd = np.array([math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)])
    right = np.cross(fwd, np.array([0, 0, 1.0]))
    right /= np.linalg.norm(right)
    up = np.cross(right, fwd)
    center = V.mean(axis=0)
    Pc = V - center
    span = max(np.ptp(Pc @ right), np.ptp(Pc @ up)) * 1.12
    return center, span


def make_step(cand, name, existing, new, offsets, pins_expl=(), pins_final=(), arrows=(), frame=None):
    final = [(pid_mesh(cand, p), OLD) for p in existing] + [(pid_mesh(cand, p), NEW[cand]) for p in new]
    final += list(pins_final)
    expl = [(pid_mesh(cand, p), OLD) for p in existing]
    for p in new:
        expl.append((pid_mesh(cand, p, offsets.get(p, (0, 0, 0))), NEW[cand]))
    expl += list(pins_expl)
    fr = frame if frame is not None else frame_items(expl)
    render(expl, name + "_exploded.png", frame=fr, arrows=arrows)
    render(final, name + "_after.png", frame=fr)


def mount_pins(cand, yc, offset_z=0):
    out = []
    for dx in (-6.0, 6.0):
        for dy in (-14.0, 14.0):
            out += vertical_pin(cand, "PIN3-L14", (10 + dx, yc + dy), 10,
                                offset=(0, 0, offset_z), clip=False)
    return out


def mount_pins_final(cand, yc):
    return mount_pins(cand, yc, 0)


# ============================ F07 ============================
cand = "F07"
base = ["BASE", "BED"]
tower = ["TWR_0"]
car = ["CAR_0"]
cap = ["CAP_0"]
col = ["COL_0"]

# F07-1 base + tower
pe = mount_pins(cand, 0, 25)
pf = mount_pins_final(cand, 0)
ar = [(joint(cand, "TWR_0", (0, 0, 0)) + np.array([0, 0, 45]), joint(cand, "TWR_0", (0, 0, 0)), NEW[cand])]
for dx in (-6, 6):
    for dy in (-14, 14):
        ar.append(((10 + dx, 0 + dy, 35), (10 + dx, 0 + dy, 10), ORANGE))
make_step(cand, "F07_1", [], base + tower, {"TWR_0": (0, 0, 45)}, pe, pf, ar)
detail(cand, "F07_1_pin", [pid_mesh(cand, "BASE"), (pid_mesh(cand, "TWR_0"), NEW[cand])] + mount_pins_final(cand, 0),
       (4, 14, 2), 34, elev=-22)

# F07-2A trial carriage
p = joint(cand, "CAR_0", (4, 15, 14))
make_step(cand, "F07_2A", base + tower, car, {"CAR_0": (0, 0, 45)}, arrows=[(p + np.array([0, 0, 45]), p, NEW[cand])])

# F07-2B cap + cap pins
pe, pf = [], []
for dy in (-15, 15):
    c = joint(cand, "TWR_0", (0, dy, 65))
    pe += pin_item(cand, "PIN3-L14", c, (1, 0, 0), offset=(-25, 0, 0))
    pf += pin_item(cand, "PIN3-L14", c, (1, 0, 0), clip=True)
ar = [(joint(cand, "CAP_0", (0, 0, 65)) + np.array([0, 0, 25]), joint(cand, "CAP_0", (0, 0, 65)), NEW[cand]),
      (joint(cand, "TWR_0", (0, 15, 65)) + np.array([-25, 0, 0]), joint(cand, "TWR_0", (0, 15, 65)), ORANGE),
      (joint(cand, "TWR_0", (0, -15, 65)) + np.array([-25, 0, 0]), joint(cand, "TWR_0", (0, -15, 65)), ORANGE)]
make_step(cand, "F07_2B", base + tower + car, cap, {"CAP_0": (0, 0, 25)}, pe, pf, ar,
          frame=(np.array([10.0, 0.0, 52.0]), 100.0))
detail(cand, "F07_2B_pin", [pid_mesh(cand, "TWR_0"), (pid_mesh(cand, "CAP_0"), NEW[cand])] + pf, (10, 15, 75), 32)

# F07-3 root column + main pin + 0 deg lock
root = joint(cand, "CAR_0", (14, 0, 3))
lock = joint(cand, "CAR_0", (14, 0, 11))
pe = pin_item(cand, "PIN5-L34", root, (0, 1, 0), offset=(0, 55, 0)) + pin_item(cand, "PIN3-L34", lock, (0, 1, 0), offset=(0, 45, 0))
pf = pin_item(cand, "PIN5-L34", root, (0, 1, 0), clip=True) + pin_item(cand, "PIN3-L34", lock, (0, 1, 0), clip=True)
ar = [(root + np.array([0, 35, 0]), root, NEW[cand]), (root + np.array([0, 55, 0]), root, ORANGE),
      (lock + np.array([0, 45, 0]), lock, ORANGE)]
make_step(cand, "F07_3", base + tower + car + cap, col, {"COL_0": (0, 35, 0)}, pe, pf, ar)
detail(cand, "F07_3_pin", [pid_mesh(cand, "CAR_0"), (pid_mesh(cand, "COL_0"), NEW[cand])] + pf, (20, 0, 17), 42)

# F07-4 arm + main pin + lock
ap = joint(cand, "COL_0", (16, 0, 137))
al = joint(cand, "COL_0", (24, 0, 137))
pe = pin_item(cand, "PIN5-L34", ap, (0, 1, 0), offset=(0, 55, 0)) + pin_item(cand, "PIN3-L34", al, (0, 1, 0), offset=(0, 45, 0))
pf = pin_item(cand, "PIN5-L34", ap, (0, 1, 0), clip=True) + pin_item(cand, "PIN3-L34", al, (0, 1, 0), clip=True)
ar = [(ap + np.array([0, 35, 0]), ap, NEW[cand]), (ap + np.array([0, 55, 0]), ap, ORANGE),
      (al + np.array([0, 45, 0]), al, ORANGE)]
make_step(cand, "F07_4", base + tower + car + cap + col, ["ARM"], {"ARM": (0, 35, 0)}, pe, pf, ar)
detail(cand, "F07_4_pin", [pid_mesh(cand, "COL_0"), (pid_mesh(cand, "ARM"), NEW[cand])] + pf, (36, 0, 150), 42)
print("F07 SCENES DONE", flush=True)

# ============================ F09 ============================
cand = "F09_L82"
base = ["BASE", "BED"]
towers = ["TWR_0", "TWR_1"]
cars = ["CAR_0", "CAR_1"]
caps = ["CAP_0", "CAP_1"]
cols = ["COL_0", "COL_1"]

# F09-1
pe = mount_pins(cand, -65, 25) + mount_pins(cand, 65, 25)
pf = mount_pins_final(cand, -65) + mount_pins_final(cand, 65)
make_step(cand, "F09_1", [], base + towers, {"TWR_0": (0, 0, 45), "TWR_1": (0, 0, 45)}, pe, pf,
          [(joint(cand, "TWR_0", (0, 0, 0)) + np.array([0, 0, 45]), joint(cand, "TWR_0", (0, 0, 0)), NEW[cand]),
           (joint(cand, "TWR_1", (0, 0, 0)) + np.array([0, 0, 45]), joint(cand, "TWR_1", (0, 0, 0)), NEW[cand]),
           ((4, -51, 35), (4, -51, 10), ORANGE), ((4, 79, 35), (4, 79, 10), ORANGE)])

# F09-2 trial carriages
p0, p1 = joint(cand, "CAR_0", (4, 15, 14)), joint(cand, "CAR_1", (4, 15, 14))
make_step(cand, "F09_2", base + towers, cars, {"CAR_0": (0, 0, 45), "CAR_1": (0, 0, 45)},
          arrows=[(p0 + np.array([0, 0, 45]), p0, NEW[cand]), (p1 + np.array([0, 0, 45]), p1, NEW[cand])])

# F09-3A SYNC + 4 horizontal pins
pe, pf = [], []
for i in (0, 1):
    for dy in (-10, 10):
        c = joint(cand, f"CAR_{i}", (2, dy, 17))
        pe += pin_item(cand, "PIN3-L18", c, (1, 0, 0), offset=(25, 0, 0))
        pf += pin_item(cand, "PIN3-L18", c, (1, 0, 0), clip=True)
sync_ar = [(joint(cand, "SYNC", (9.25, 0, 18)) + np.array([0, 0, 35]), joint(cand, "SYNC", (9.25, 0, 18)), NEW[cand])]
for i in (0, 1):
    for dy in (-10, 10):
        c = joint(cand, f"CAR_{i}", (2, dy, 17))
        sync_ar.append((c + np.array([25, 0, 0]), c, ORANGE))
make_step(cand, "F09_3A", base + towers + cars, ["SYNC"], {"SYNC": (0, 0, 35)}, pe, pf, sync_ar)
detail(cand, "F09_3A_pin", [pid_mesh(cand, "CAR_0"), (pid_mesh(cand, "SYNC"), NEW[cand])] + pf[:4], joint(cand, "CAR_0", (2, 10, 17)), 32)

# F09-3B two columns
pe, pf, ar = [], [], []
for i, sign in ((0, -1), (1, 1)):
    root = joint(cand, f"CAR_{i}", (14, 0, 3))
    lock = joint(cand, f"CAR_{i}", (14, 0, 11))
    pe += pin_item(cand, "PIN5-L34", root, (0, 1, 0), offset=(0, sign * 55, 0))
    pe += pin_item(cand, "PIN3-L34", lock, (0, 1, 0), offset=(0, sign * 45, 0))
    pf += pin_item(cand, "PIN5-L34", root, (0, 1, 0), clip=True)
    pf += pin_item(cand, "PIN3-L34", lock, (0, 1, 0), clip=True)
    ar += [(root + np.array([0, sign * 35, 0]), root, NEW[cand]),
           (root + np.array([0, sign * 55, 0]), root, ORANGE)]
make_step(cand, "F09_3B", base + towers + cars + ["SYNC"], cols,
          {"COL_0": (0, -35, 0), "COL_1": (0, 35, 0)}, pe, pf, ar)
detail(cand, "F09_3B_pin", [pid_mesh(cand, "CAR_0"), (pid_mesh(cand, "COL_0"), NEW[cand])] + pf[:4], joint(cand, "CAR_0", (14, 0, 3)), 42)

# F09-3C caps
pe, pf, ar = [], [], []
for i in (0, 1):
    for dy in (-15, 15):
        c = joint(cand, f"TWR_{i}", (0, dy, 65))
        pe += pin_item(cand, "PIN3-L14", c, (1, 0, 0), offset=(-25, 0, 0))
        pf += pin_item(cand, "PIN3-L14", c, (1, 0, 0), clip=True)
    cc = joint(cand, f"CAP_{i}", (0, 0, 65))
    ar.append((cc + np.array([0, 0, 25]), cc, NEW[cand]))
ar += [(joint(cand, "TWR_0", (0, 15, 65)) + np.array([-25, 0, 0]), joint(cand, "TWR_0", (0, 15, 65)), ORANGE),
       (joint(cand, "TWR_1", (0, -15, 65)) + np.array([-25, 0, 0]), joint(cand, "TWR_1", (0, -15, 65)), ORANGE)]
make_step(cand, "F09_3C", base + towers + cars + ["SYNC"] + cols, caps,
          {"CAP_0": (0, 0, 25), "CAP_1": (0, 0, 25)}, pe, pf, ar,
          frame=(np.array([10.0, 0.0, 52.0]), 190.0))
detail(cand, "F09_3C_pin", [pid_mesh(cand, "TWR_0"), (pid_mesh(cand, "CAP_0"), NEW[cand]), pid_mesh(cand, "SYNC")] + pf[:4], (10, -50, 75), 32)

# F09-4A XBAR
pe, pf = [], []
for i, yc in ((0, -65), (1, 65)):
    c = joint(cand, f"COL_{i}", (0, yc, 162))
    pe += pin_item(cand, "PIN3-L22", c, (1, 0, 0), offset=(25, 0, 0))
    pf += pin_item(cand, "PIN3-L22", c, (1, 0, 0), clip=True)
xbar_ar = [(joint(cand, "XBAR", (0, 0, 173.5)) + np.array([0, 0, 35]), joint(cand, "XBAR", (0, 0, 173.5)), NEW[cand])]
for i, yc in ((0, -65), (1, 65)):
    c = joint(cand, f"COL_{i}", (0, yc, 162))
    xbar_ar.append((c + np.array([25, 0, 0]), c, ORANGE))
make_step(cand, "F09_4A", base + towers + cars + ["SYNC"] + cols + caps, ["XBAR"], {"XBAR": (0, 0, 35)}, pe, pf, xbar_ar)
detail(cand, "F09_4A_pin", [pid_mesh(cand, "COL_0"), (pid_mesh(cand, "XBAR"), NEW[cand])] + pf[:2], joint(cand, "COL_0", (0, -65, 162)), 34)

# F09-4B BRG
pe, pf = [], []
for dy in (-61.5, 61.5):
    c = joint(cand, "BRG", (0, dy, 132))
    pe += pin_item(cand, "PIN3-L18", c, (0, 1, 0), offset=(0, 45, 0))
    pf += pin_item(cand, "PIN3-L18", c, (0, 1, 0), clip=True)
brg_ar = [(joint(cand, "BRG", (0, 0, 137)) + np.array([35, 0, 0]), joint(cand, "BRG", (0, 0, 137)), NEW[cand])]
for dy in (-61.5, 61.5):
    c = joint(cand, "BRG", (0, dy, 132))
    brg_ar.append((c + np.array([0, 45, 0]), c, ORANGE))
make_step(cand, "F09_4B", base + towers + cars + ["SYNC"] + cols + caps + ["XBAR"], ["BRG"], {"BRG": (35, 0, 0)}, pe, pf, brg_ar)
detail(cand, "F09_4B_pin", [pid_mesh(cand, "COL_0"), (pid_mesh(cand, "BRG"), NEW[cand])] + pf[:2], joint(cand, "BRG", (0, -61.5, 132)), 32)

# F09-5A central arm
ap = joint(cand, "BRG", (16, 0, 137))
al = joint(cand, "BRG", (24, 0, 137))
pe = pin_item(cand, "PIN5-L34", ap, (0, 1, 0), offset=(0, 55, 0)) + pin_item(cand, "PIN3-L34", al, (0, 1, 0), offset=(0, 45, 0))
pf = pin_item(cand, "PIN5-L34", ap, (0, 1, 0), clip=True) + pin_item(cand, "PIN3-L34", al, (0, 1, 0), clip=True)
make_step(cand, "F09_5A", base + towers + cars + ["SYNC"] + cols + caps + ["XBAR", "BRG"], ["ARM"], {"ARM": (0, 35, 0)}, pe, pf,
          [(ap + np.array([0, 35, 0]), ap, NEW[cand]), (ap + np.array([0, 55, 0]), ap, ORANGE),
           (al + np.array([0, 45, 0]), al, ORANGE)])
detail(cand, "F09_5A_pin", [pid_mesh(cand, "BRG"), (pid_mesh(cand, "ARM"), NEW[cand])] + pf, (36, 0, 150), 42)
print("F09 SCENES DONE", flush=True)

# ============================ SCZ ============================
cand = "SCZ"
base = ["BASE", "BED"]
posts = ["POST_L", "POST_R"]
slbs = ["SLB_L", "SLB_R"]
armas = ["ARM_A_L", "ARM_A_R"]
armbs = ["ARM_B_L", "ARM_B_R"]
slts = ["SLT_L", "SLT_R"]

# SCZ-1 base + posts
pe, pf = [], []
for yc in (-71, 71):
    for dx in (-3, 3):
        for dy in (-3.6, 3.6):
            pe += vertical_pin(cand, "PIN3-L13", (155 + dx, yc + dy), 13, offset=(0, 0, 25), clip=False)
            pf += vertical_pin(cand, "PIN3-L13", (155 + dx, yc + dy), 13, clip=True)
make_step(cand, "SCZ_1", [], base + posts, {"POST_L": (0, 0, 35), "POST_R": (0, 0, 35)}, pe, pf,
          [(joint(cand, "POST_L", (0, 0, 11.5)) + np.array([0, 0, 35]), joint(cand, "POST_L", (0, 0, 11.5)), NEW[cand]),
           (joint(cand, "POST_R", (0, 0, 11.5)) + np.array([0, 0, 35]), joint(cand, "POST_R", (0, 0, 11.5)), NEW[cand])])

# SCZ-2 bottom sliders + arm A
pe, pf, ar = [], [], []
for side, sign in (("L", -1), ("R", 1)):
    c = joint(cand, f"SLB_{side}", (0, 0, 0))
    pe += pin_item(cand, "PIN4-L18", c, (0, 1, 0), offset=(0, sign * 45, 0))
    pf += pin_item(cand, "PIN4-L18", c, (0, 1, 0), clip=True)
    ar += [(joint(cand, f"SLB_{side}", (0, 0, -4)) + np.array([0, 0, 30]), joint(cand, f"SLB_{side}", (0, 0, -4)), NEW[cand]),
           (c + np.array([0, sign * 45, 0]), c, ORANGE)]
make_step(cand, "SCZ_2", base + posts, slbs + armas,
          {"SLB_L": (0, 0, 30), "SLB_R": (0, 0, 30), "ARM_A_L": (0, -30, 0), "ARM_A_R": (0, 30, 0)}, pe, pf, ar)
detail(cand, "SCZ_2_pin", [pid_mesh(cand, "SLB_L"), (pid_mesh(cand, "ARM_A_L"), NEW[cand])] + pf[:2], joint(cand, "SLB_L", (0, 0, 0)), 32)

# SCZ-3A bottom shaft from below + cross pins + end clips
pe, pf = [], []
for side, sign in (("L", -1), ("R", 1)):
    c = joint(cand, f"SLB_{side}", (0, 0, -9))
    pe += pin_item(cand, "PIN25-L10", c, (0, 0, 1), offset=(0, 0, -20))
    pf += pin_item(cand, "PIN25-L10", c, (0, 0, 1))
shb_c = joint(cand, "SHB", (0, 0, 0))
for sy in (-1, 1):
    cc = shb_c + np.array([0, sy * 79.6, 0])
    pe.append((xform(PINS[cand]["CLIP4"], cc + np.array([0, sy * 20, 0]), axis_z((0, 1, 0))), RED))
    pf.append((xform(PINS[cand]["CLIP4"], cc, axis_z((0, 1, 0))), RED))
shb_ar = [(shb_c + np.array([0, 0, -35]), shb_c, NEW[cand])]
for side in ("L", "R"):
    c = joint(cand, f"SLB_{side}", (0, 0, -9))
    shb_ar.append((c + np.array([0, 0, -20]), c, ORANGE))
make_step(cand, "SCZ_3A", base + posts + slbs + armas, ["SHB"], {"SHB": (0, 0, -35)}, pe, pf, shb_ar)
detail(cand, "SCZ_3A_pin", [pid_mesh(cand, "BASE"), pid_mesh(cand, "SLB_L"), (pid_mesh(cand, "SHB"), NEW[cand])] + pf[:3], shb_c + np.array([0, -62.5, 0]), 36, elev=-15)

# SCZ-3B arm B + center hinge
pe, pf, ar = [], [], []
for side, sign in (("L", -1), ("R", 1)):
    cb = joint(cand, f"POST_{side}", (0, 0, 18))
    cc = (joint(cand, f"ARM_A_{side}", (77, 0, 0)) + joint(cand, f"ARM_B_{side}", (77, 0, 0))) / 2
    pe += pin_item(cand, "PIN4-L16", cb, (0, 1, 0), offset=(0, sign * 45, 0))
    pe += pin_item(cand, "PIN4-L16", cc, (0, 1, 0), offset=(0, sign * 55, 0))
    pf += pin_item(cand, "PIN4-L16", cb, (0, 1, 0), clip=True)
    pf += pin_item(cand, "PIN4-L16", cc, (0, 1, 0), clip=True)
    ar += [(cb + np.array([0, sign * 45, 0]), cb, ORANGE), (cc + np.array([0, sign * 55, 0]), cc, ORANGE)]
make_step(cand, "SCZ_3B", base + posts + slbs + armas + ["SHB"], armbs,
          {"ARM_B_L": (0, -30, 0), "ARM_B_R": (0, 30, 0)}, pe, pf, ar)
detail(cand, "SCZ_3B_center", [pid_mesh(cand, "ARM_A_L"), (pid_mesh(cand, "ARM_B_L"), NEW[cand])] + pf[2:4], joint(cand, "ARM_A_L", (77, 0, 0)), 32)

# SCZ-4A top sliders + top shaft
pe, pf = [], []
for side, sign in (("L", -1), ("R", 1)):
    c = joint(cand, f"SLT_{side}", (0, 0, 0))
    cp = joint(cand, f"SLT_{side}", (0, 0, 9))
    pe += pin_item(cand, "PIN4-L16", c, (0, 1, 0), offset=(0, sign * 45, 0))
    pe += pin_item(cand, "PIN25-L10", cp, (0, 0, 1), offset=(0, 0, 20))
    pf += pin_item(cand, "PIN4-L16", c, (0, 1, 0), clip=True)
    pf += pin_item(cand, "PIN25-L10", cp, (0, 0, 1))
sht_c = joint(cand, "SHT", (0, 0, 0))
for sy in (-1, 1):
    cc = sht_c + np.array([0, sy * 79.6, 0])
    pe.append((xform(PINS[cand]["CLIP4"], cc + np.array([0, sy * 20, 0]), axis_z((0, 1, 0))), RED))
    pf.append((xform(PINS[cand]["CLIP4"], cc, axis_z((0, 1, 0))), RED))
slt_ar = []
for side, sign in (("L", -1), ("R", 1)):
    c = joint(cand, f"SLT_{side}", (0, 0, 0))
    cp = joint(cand, f"SLT_{side}", (0, 0, 9))
    slt_ar += [(c + np.array([0, sign * 45, 0]), c, ORANGE), (cp + np.array([0, 0, 20]), cp, ORANGE)]
slt_ar.append((sht_c + np.array([0, 45, 0]), sht_c, NEW[cand]))
make_step(cand, "SCZ_4A", base + posts + slbs + armas + ["SHB"] + armbs, slts + ["SHT"],
          {"SLT_L": (0, -30, 0), "SLT_R": (0, 30, 0), "SHT": (0, 45, 0)}, pe, pf, slt_ar)
detail(cand, "SCZ_4A_pin", [(pid_mesh(cand, "SLT_L"), NEW[cand]), pid_mesh(cand, "ARM_B_L"), (pid_mesh(cand, "SHT"), NEW[cand])] + pf[:4], joint(cand, "SLT_L", (0, 0, 5)), 34)

# SCZ-4B platform
pe, pf = [], []
for sy in (-1, 1):
    c = joint(cand, "PLAT", (0, sy * 62.5, 0))
    pe += pin_item(cand, "PIN4-L18", c, (0, 1, 0), offset=(0, sy * 45, 0))
    pf += pin_item(cand, "PIN4-L18", c, (0, 1, 0), clip=True)
make_step(cand, "SCZ_4B", base + posts + slbs + armas + ["SHB"] + armbs + slts + ["SHT"], ["PLAT"], {"PLAT": (0, 0, 40)}, pe, pf,
          [(joint(cand, "PLAT", (-77.5, 0, 9)) + np.array([0, 0, 40]), joint(cand, "PLAT", (-77.5, 0, 9)), NEW[cand])])
detail(cand, "SCZ_4B_pin", [(pid_mesh(cand, "PLAT"), NEW[cand]), pid_mesh(cand, "ARM_A_L")] + pf[:2], joint(cand, "PLAT", (0, -62.5, 0)), 32)
print("SCZ SCENES DONE", flush=True)
print("ALL V2 SCENES DONE", flush=True)
