"""OVERPOWERED AMPHIBOAT: V-bottom planing hull, twin ducted 5" FPV fans, 4WD
paddle wheels (JGB37-520). Units mm; x forward, y port, z up, z = 0 keel.

    pip install manifold3d trimesh numpy
    python generate.py        # STLs (print orientation) + assembly.glb + stats.json
"""
import json
import math
import os

import numpy as np
import trimesh
from manifold3d import Manifold

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SEGS = {"stern": (-270.0, -90.0), "mid": (-90.0, 90.0), "bow": (90.0, 270.0)}
B, TOP, DEAD = 100.0, 110.0, 25.0          # half-beam, deck height, deadrise rise to chine
AXLES = (180.0, -160.0)                    # front / rear wheel axle x
SHAFT_Z, WHEEL_R, WHEEL_W = 78.0, 88.0, 40.0   # ground at z = -10
MOTOR_R = 18.5                             # JGB37 gearbox radius
BAY = 75.0                                 # electronics bay half-size (mid segment)
DUCT_Y, DUCT_Z, DUCT_RI, DUCT_T = 76.0, 219.0, 66.5, 2.5   # 5" prop in a 133 mm duct
DUCT_X = (-265.0, -220.0)
LID_HOLES = [(sx * 50, sy * 88) for sx in (-1, 1) for sy in (-1, 1)] + [(sx * 83, sy * 40) for sx in (-1, 1) for sy in (-1, 1)]


def box(x0, x1, y0, y1, z0, z1):
    return Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def cyl(r, a0, a1, axis, p, q, seg=48):
    m = Manifold.cylinder(a1 - a0, r, r, seg)
    if axis == "x":
        return m.rotate([0, 90, 0]).translate([a0, p, q])
    if axis == "y":
        return m.rotate([-90, 0, 0]).translate([p, a0, q])
    return m.translate([p, q, a0])


def section(x):
    """(half-beam, keel z) of the hull at station x."""
    keel = 60.0 * ((x - 150) / 120) ** 2 if x > 150 else 0.0
    half = B - 70.0 * ((x - 200) / 70) ** 2 if x > 200 else B
    return half, keel


def hull_segment(name):
    x0, x1 = SEGS[name]
    pts = []
    for x in np.linspace(x0, x1, 13):
        b, k = section(x)
        zc = min(k + DEAD, TOP - 5)
        for (y, z) in ((0, k), (b, zc), (b, TOP), (-b, TOP), (-b, zc)):
            pts.append([x, y, z])
    m = Manifold.hull_points(pts)
    for fx in (x0, x1):                                           # dowel holes on joint faces
        if abs(fx) == 270:
            continue
        for (y, z) in ((-50, 60), (50, 60), (-25, 30), (25, 30)):
            m = m - cyl(3.2, fx - 12, fx + 12, "x", y, z, 24)
    for ax in AXLES:
        if x0 < ax < x1:
            for s in (-1, 1):                                     # motor pocket, gearbox face at the side wall
                y0, y1 = sorted((s * 22, s * (B - 3)))
                m = m - box(ax - 20, ax + 20, y0, y1, SHAFT_Z - MOTOR_R - 1.5, TOP + 1)
                ya, yb = sorted((s * (B - 4), s * (B + 1)))
                m = m - cyl(6.5, ya, yb, "y", ax, SHAFT_Z)
                for dx in (-15.5, 15.5):
                    m = m - cyl(1.7, ya, yb, "y", ax + dx, SHAFT_Z, 16)
                m = m - cyl(2.0, ya, yb, "y", ax, SHAFT_Z - MOTOR_R + 1, 16)       # drain
            for dx in (-25, 25):                                  # cover screws
                for y in (-60, 0, 60):
                    m = m - cyl(1.3, TOP - 14, TOP + 1, "z", ax + dx, y, 16)
    if name == "mid":
        m = m - box(-BAY, BAY, -BAY, BAY, 30, TOP + 1)
        for (x, y) in LID_HOLES:
            m = m - cyl(1.3, TOP - 14, TOP + 1, "z", x, y, 16)
    if name == "stern":
        for s in (-1, 1):
            for (x, dy) in ((-255, -14), (-255, 14), (-230, -14), (-230, 14)):
                m = m - cyl(1.3, TOP - 14, TOP + 1, "z", x, s * DUCT_Y + dy, 16)
    return m


def bay_lid():
    m = box(-88, 88, -97, 97, TOP, TOP + 4)
    m = m + (box(-BAY + 0.4, BAY - 0.4, -BAY + 0.4, BAY - 0.4, TOP - 6, TOP + 0.01)
             - box(-BAY + 2.4, BAY - 2.4, -BAY + 2.4, BAY - 2.4, TOP - 7, TOP + 1))
    m = m - (box(-81, 81, -81, 81, TOP - 1, TOP + 1.5) - box(-78, 78, -78, 78, TOP - 2, TOP + 2))   # gasket groove
    for (x, y) in LID_HOLES:
        m = m - cyl(1.7, TOP - 1, TOP + 5, "z", x, y, 16)
    for (x, y) in ((55, 45), (55, -45), (-55, 45), (-55, -45), (-55, 0)):
        m = m - cyl(6.4, TOP - 7, TOP + 5, "z", x, y, 32)        # PG7 cable glands
    return m


def pocket_cover(ax):
    m = box(ax - 28, ax + 28, -B + 2, B - 2, TOP, TOP + 4)
    for s in (-1, 1):                                             # saddles that clamp the motors
        y0, y1 = sorted((s * 30, s * 90))
        m = m + (box(ax - 19, ax + 19, y0, y1, SHAFT_Z, TOP + 0.01) - cyl(MOTOR_R + 0.3, -B, B, "y", ax, SHAFT_Z, 64))
        m = m - cyl(4.0, TOP - 40, TOP + 5, "z", ax, s * 26, 24)  # wire grommet
    for dx in (-25, 25):
        for y in (-60, 0, 60):
            m = m - cyl(1.7, TOP - 1, TOP + 5, "z", ax + dx, y, 16)
    return m


def wheel():
    """Paddle wheel for a JGB37 6 mm D shaft. Flange z = 0 (outboard), hub face z = WHEEL_W."""
    w = cyl(WHEEL_R, 0, 3, "z", 0, 0, 120)
    rim = WHEEL_R - 18
    w = w + (cyl(rim, 0, WHEEL_W, "z", 0, 0, 120) - cyl(rim - 2.5, -1, WHEEL_W + 1, "z", 0, 0, 120))
    web = cyl(rim - 1, 0, 3, "z", 0, 0, 96)
    for i in range(6):
        a = math.pi * i / 3
        web = web - cyl(16, -1, 4, "z", 40 * math.cos(a), 40 * math.sin(a), 40)
    paddles = Manifold()
    for i in range(10):
        paddles = paddles + box(rim - 4, WHEEL_R, -1.5, 1.5, 0, WHEEL_W).rotate([0, 0, 36 * i + 12])
    w = w + web + (paddles ^ cyl(WHEEL_R, -1, WHEEL_W + 1, "z", 0, 0, 120)) + cyl(12, 0, WHEEL_W, "z", 0, 0, 48)
    bore = cyl(3.05, WHEEL_W - 15, WHEEL_W + 1, "z", 0, 0, 32) ^ box(-4, 2.55, -4, 4, WHEEL_W - 16, WHEEL_W + 2)
    w = w - bore - cyl(3.5, -1, WHEEL_W - 15, "z", 0, 0, 24)
    for zs in (WHEEL_W - 5, WHEEL_W - 11):                        # 2 x M3 grub screws onto the flat
        w = w - cyl(1.25, -1, 13, "x", 0, zs, 16)
    return w


def fan_duct():
    """Duct + motor spider (front, 2306 16x16 mount) + base, port side (y = +DUCT_Y).
    Axis along x; prop pushes aft."""
    xa, xb = DUCT_X
    ro = DUCT_RI + DUCT_T
    m = cyl(ro, xa, xb, "x", DUCT_Y, DUCT_Z, 128) - cyl(DUCT_RI, xa - 1, xb + 1, "x", DUCT_Y, DUCT_Z, 128)
    m = m + cyl(ro + 3, xb - 4, xb, "x", DUCT_Y, DUCT_Z, 128) - cyl(DUCT_RI, xb - 5, xb + 1, "x", DUCT_Y, DUCT_Z, 128)  # front lip
    hub = cyl(16, xb - 5, xb, "x", DUCT_Y, DUCT_Z, 48)
    for i in range(6):                                            # spokes double as the front guard
        hub = hub + box(xb - 5, xb, -2, 2, 0, DUCT_RI + 1).rotate([60 * i, 0, 0]).translate([0, DUCT_Y, DUCT_Z])
    hub = hub + (cyl(42, xb - 5, xb, "x", DUCT_Y, DUCT_Z, 96) - cyl(39, xb - 6, xb + 1, "x", DUCT_Y, DUCT_Z, 96))
    m = m + hub - cyl(4.5, xb - 6, xb + 1, "x", DUCT_Y, DUCT_Z, 24)
    for (dy, dz) in ((8, 8), (8, -8), (-8, 8), (-8, -8)):
        m = m - cyl(1.7, xb - 6, xb + 1, "x", DUCT_Y + dy, DUCT_Z + dz, 16)
    base = box(xa, xb, DUCT_Y - 22, DUCT_Y + 22, TOP, DUCT_Z - ro + 6) - cyl(DUCT_RI, xa - 1, xb + 1, "x", DUCT_Y, DUCT_Z, 128)
    m = m + base
    for (x, dy) in ((-255, -14), (-255, 14), (-230, -14), (-230, 14)):
        m = m - cyl(1.7, TOP - 1, TOP + 30, "z", x, DUCT_Y + dy, 16) - cyl(3.2, TOP + 6, TOP + 60, "z", x, DUCT_Y + dy, 24)
    for (dy, dz) in ((ro + 1.5, 0), (-ro - 1.5, 0), (0, ro + 1.5)):
        m = m + (cyl(3.5, xa, xa + 6, "x", DUCT_Y + dy, DUCT_Z + dz, 24) - cyl(1.3, xa - 1, xa + 7, "x", DUCT_Y + dy, DUCT_Z + dz, 16))
    return m


def rear_guard():
    """Flat grille screwed to the duct's aft end. Built in the duct's y-z plane at x = 0."""
    ro = DUCT_RI + DUCT_T
    g = cyl(ro + 5, 0, 2.5, "x", 0, 0, 128) - cyl(ro - 1, -1, 3.5, "x", 0, 0, 128)
    for i in range(-3, 4):
        g = g + box(0, 2.5, -1.25 + 18 * i, 1.25 + 18 * i, -ro, ro)
    g = g ^ cyl(ro + 5, -1, 4, "x", 0, 0, 128)
    for (dy, dz) in ((ro + 1.5, 0), (-ro - 1.5, 0), (0, ro + 1.5)):
        g = g - cyl(1.7, -1, 4, "x", dy, dz, 16)
    return g


def dowel():
    return cyl(3.0, 0, 22, "z", 0, 0, 32)


def assembly():
    P = []
    for n in SEGS:
        P.append((f"hull_{n}", hull_segment(n), "#f2a33a"))
    P.append(("bay_lid", bay_lid(), "#5b5f66"))
    for ax in AXLES:
        P.append((f"pocket_cover_{ax:+.0f}", pocket_cover(ax), "#5b5f66"))
        for s in (-1, 1):
            mot = cyl(MOTOR_R, 22, B - 3, "y", ax, SHAFT_Z, 32)
            wh = wheel().rotate([90, 0, 0]).translate([ax, B + 3 + WHEEL_W, SHAFT_Z])
            P.append((f"motor_{ax:+.0f}_{s}", mot if s > 0 else mot.mirror([0, 1, 0]), "#9aa3ad"))
            P.append((f"wheel_{ax:+.0f}_{s}", wh if s > 0 else wh.mirror([0, 1, 0]), "#333333"))
    for s in (-1, 1):
        d = fan_duct()
        g = rear_guard().translate([DUCT_X[0] - 2.5, DUCT_Y, DUCT_Z])
        P.append((f"fan_duct_{s}", d if s > 0 else d.mirror([0, 1, 0]), "#3c6fb0"))
        P.append((f"rear_guard_{s}", g if s > 0 else g.mirror([0, 1, 0]), "#3c6fb0"))
        fm = cyl(14.5, DUCT_X[1] - 23, DUCT_X[1] - 5, "x", s * DUCT_Y, DUCT_Z, 32) + cyl(63.5, DUCT_X[1] - 32, DUCT_X[1] - 30, "x", s * DUCT_Y, DUCT_Z, 64)
        P.append((f"fpv_motor_prop_{s}", fm, "#c94c3c"))
    return P


def to_tm(m):
    mesh = m.to_mesh()
    return trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts), process=False)


def grams(m, walls=0.8, infill=0.15):
    v = m.volume() / 1000
    sh = min(v, m.surface_area() / 100 * walls / 10)
    return (sh + infill * (v - sh)) * 1.24


def main():
    stl = os.path.join(ROOT, "stl")
    os.makedirs(stl, exist_ok=True)
    parts = {"hull_bow": (hull_segment("bow"), 1), "hull_mid": (hull_segment("mid"), 1),
             "hull_stern": (hull_segment("stern"), 1), "dowel": (dowel(), 8),
             "bay_lid": (bay_lid().rotate([180, 0, 0]), 1),
             "pocket_cover": (pocket_cover(0).rotate([180, 0, 0]), 2), "wheel": (wheel(), 4),
             "fan_duct_port": (fan_duct().rotate([0, -90, 0]), 1),
             "fan_duct_stbd": (fan_duct().mirror([0, 1, 0]).rotate([0, -90, 0]), 1),
             "rear_guard": (rear_guard().rotate([0, -90, 0]), 2)}
    rows, total = [], 0.0
    for name, (m, q) in parts.items():
        t = to_tm(m)
        b = t.bounds
        t.apply_translation([-(b[0][0] + b[1][0]) / 2, -(b[0][1] + b[1][1]) / 2, -b[0][2]])
        t.export(os.path.join(stl, name + ".stl"))
        g = grams(m, 1.2, 0.05) if name.startswith("hull") else grams(m)
        total += g * q
        e = sorted(t.extents[:2])
        rows.append(dict(part=name, qty=q, size=[round(v) for v in t.extents], grams=round(g * q),
                         fits=bool(e[1] <= 220 and t.extents[2] <= 250), watertight=bool(t.is_watertight)))
    P = assembly()
    clash = []
    for i in range(len(P)):
        for j in range(i + 1, len(P)):
            v = (P[i][1] ^ P[j][1]).volume()
            if v > 1:
                clash.append((P[i][0], P[j][0], round(v)))
    bought = {"JGB37-520 x4": 4 * 175, "2306 FPV motors + 5in props x2": 2 * 40, "30A ESC x2": 2 * 25,
              "BTS7960 x2": 2 * 65, "4S 2200 mAh LiPo": 240, "Nano, receiver, buck, wiring, screws": 180}
    dry = total + sum(bought.values())
    hull = Manifold()
    for n in SEGS:
        hull = hull + hull_segment(n)
    full = Manifold()
    for n in SEGS:                                    # displacement ignores the open bay/pockets (above water)
        x0, x1 = SEGS[n]
        full = full + Manifold.hull_points([[x, y, z] for x in np.linspace(x0, x1, 13)
                                            for (y, z) in ((0, section(x)[1]), (section(x)[0], min(section(x)[1] + DEAD, TOP - 5)),
                                                           (section(x)[0], TOP), (-section(x)[0], TOP),
                                                           (-section(x)[0], min(section(x)[1] + DEAD, TOP - 5)))])
    lo, hi = 0.0, TOP
    for _ in range(40):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if (full ^ box(-400, 400, -200, 200, -1, mid)).volume() / 1000 < dry else (lo, mid)
    stats = dict(printed_g=round(total), dry_mass_g=round(dry), draft_mm=round(lo, 1),
                 max_displacement_g=round(full.volume() / 1000), clashes=clash, parts=rows)
    with open(os.path.join(ROOT, "cad", "stats.json"), "w") as f:
        json.dump(stats, f, indent=1)
    scene = trimesh.Scene()
    for (n, m, c) in P:
        t = to_tm(m)
        rgba = trimesh.visual.color.hex_to_rgba(c)
        t.visual = trimesh.visual.TextureVisuals(material=trimesh.visual.material.PBRMaterial(baseColorFactor=rgba, metallicFactor=0, roughnessFactor=0.7))
        scene.add_geometry(t, node_name=n, geom_name=n)
    os.makedirs(os.path.join(ROOT, "renders"), exist_ok=True)
    scene.export(os.path.join(ROOT, "renders", "assembly.glb"))
    print(json.dumps({k: v for k, v in stats.items() if k != "parts"}, indent=1))
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()
