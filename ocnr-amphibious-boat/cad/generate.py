"""Generates the STL files for the amphibious paddle-wheel boat.

Units: millimetres. Hull frame: x = forward, y = port (left), z = up,
z = 0 is the hull bottom.

    pip install manifold3d trimesh numpy
    python generate.py
"""
import math
import os

import numpy as np
import trimesh
from manifold3d import Manifold, CrossSection

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "stl")

# ---------------------------------------------------------------- parameters
HULL_LEN = 210.0          # deck length
HULL_H = 50.0             # hull height (deck top)
PONTOON_W = 48.0          # each side pontoon
TUB_W = 76.0              # central electronics tub (outer)
HALF_W = TUB_W / 2 + PONTOON_W   # 86 -> hull beam 172
WALL = 2.0

BOW_BOTTOM_X = 70.0       # flat bottom ends here, bow rakes up to the deck
STERN_BOTTOM_X = -100.0

TUB_X = 60.0              # tub outer half-length
AXLE_X = 75.0             # front/rear axle x position (+/-)
POCKET_FLOOR_Z = 28.0     # TT motor pocket floor
SHAFT_Z = 46.0            # nominal TT motor shaft height
POCKET_Y = (52.0, HALF_W - WALL)  # inboard / outboard pocket faces
POCKET_X_FWD = 13.0       # pocket extends this far beyond the shaft (gearbox end)
POCKET_X_AFT = 60.0       # and this far toward the motor can

WHEEL_R_TIP = 52.0        # paddle tip radius -> 6 mm ground clearance under hull
WHEEL_R_RIM = 40.0
WHEEL_W = 22.0
PADDLES = 10

LID_CLEAR = 0.3


def box(x0, x1, y0, y1, z0, z1):
    return Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def cyl_y(r, y0, y1, x, z, seg=48):
    """Cylinder along +y."""
    return (Manifold.cylinder(y1 - y0, r, r, seg)
            .rotate([-90, 0, 0]).translate([x, y0, z]))


def cyl_z(r, z0, z1, x, y, seg=48):
    return Manifold.cylinder(z1 - z0, r, r, seg).translate([x, y, z0])


# --------------------------------------------------------------------- hull
def hull_outer():
    """Flat-bottom tri-hull shell, raked bow, rounded deck corners."""
    r = 8.0
    half_l = HULL_LEN / 2
    pts = []
    # deck outline (rounded rectangle) at z = HULL_H
    for cx, cy in [(half_l - r, HALF_W - r), (half_l - r, -HALF_W + r),
                   (-half_l + r, HALF_W - r), (-half_l + r, -HALF_W + r)]:
        for a in np.linspace(0, 2 * math.pi, 24, endpoint=False):
            pts.append([cx + r * math.cos(a), cy + r * math.sin(a), HULL_H])
    # bottom outline at z = 0 (bow raked back to BOW_BOTTOM_X)
    rb = 10.0
    for cx, cy in [(BOW_BOTTOM_X - rb, HALF_W - rb), (BOW_BOTTOM_X - rb, -HALF_W + rb),
                   (STERN_BOTTOM_X + rb, HALF_W - rb), (STERN_BOTTOM_X + rb, -HALF_W + rb)]:
        for a in np.linspace(0, 2 * math.pi, 24, endpoint=False):
            pts.append([cx + rb * math.cos(a), cy + rb * math.sin(a), 0.0])
    return Manifold.hull_points(pts)


def motor_pocket(sign_x, sign_y):
    """Open-top TT-motor pocket with a U-notch in the outer wall for the shaft."""
    ax = sign_x * AXLE_X
    if sign_x > 0:
        x0, x1 = ax - POCKET_X_AFT, ax + POCKET_X_FWD
    else:
        x0, x1 = ax - POCKET_X_FWD, ax + POCKET_X_AFT
    y0, y1 = POCKET_Y
    cut = box(x0, x1, y0, y1, POCKET_FLOOR_Z, HULL_H + 1)
    # U-notch for shaft (7.5 wide, round bottom at SHAFT_Z - 3.5)
    notch_r = 3.75
    notch = (box(ax - notch_r, ax + notch_r, y1 - 1, HALF_W + 1, SHAFT_Z, HULL_H + 1)
             + cyl_y(notch_r, y1 - 1, HALF_W + 1, ax, SHAFT_Z))
    cut = cut + notch
    # zip-tie tunnel under the pocket floor (two 5x3 slots joined by a tunnel)
    for dx in (-18.0, -36.0):
        tx = ax + sign_x * dx
        cut = cut + box(tx - 2.5, tx + 2.5, y0 + 1, y0 + 4, POCKET_FLOOR_Z - 7, POCKET_FLOOR_Z + 1)
        cut = cut + box(tx - 2.5, tx + 2.5, y1 - 4, y1 - 1, POCKET_FLOOR_Z - 7, POCKET_FLOOR_Z + 1)
        cut = cut + box(tx - 2.5, tx + 2.5, y0 + 1, y1 - 1, POCKET_FLOOR_Z - 7, POCKET_FLOOR_Z - 4)
    # wire tunnel from the pocket into the electronics tub
    wx = ax - sign_x * 45.0
    cut = cut + cyl_y(2.2, TUB_W / 2 - WALL - 1, y0 + 1, wx, HULL_H - 7)
    if sign_y < 0:
        cut = cut.mirror([0, 1, 0])
    return cut


def make_hull():
    h = hull_outer()
    # electronics tub (open top, 2 mm floor)
    ix, iy = TUB_X - WALL, TUB_W / 2 - WALL
    h = h - box(-ix, ix, -iy, iy, WALL, HULL_H + 1)
    # lid seating ledge: widen the top 3 mm of the opening by 2 mm
    h = h - box(-ix - 2, ix + 2, -iy - 2, iy + 2, HULL_H - 3, HULL_H + 1)
    for sx in (1, -1):
        for sy in (1, -1):
            h = h - motor_pocket(sx, sy)
    # battery tie-down slots in the tub floor (blind, through a bridge)
    for x in (-25.0, 25.0):
        for y in (-30.0, 30.0):
            h = h - box(x - 2, x + 2, y - 1.5, y + 1.5, WALL, WALL + 4)
    # finger notches to lift the lid
    for sx in (1, -1):
        h = h - box(sx * (ix + 2) - 6, sx * (ix + 2) + 6, -8, 8, HULL_H - 6, HULL_H + 1)
    # bow tow / recovery eye
    eye = (box(HULL_LEN / 2 - 6, HULL_LEN / 2 + 8, -4, 4, HULL_H - 8, HULL_H)
           - cyl_y(3.0, -5, 5, HULL_LEN / 2 + 3, HULL_H - 4))
    h = h + eye
    return h


def make_lid():
    """Drop-in lid: 3 mm plate sits on the tub ledge flush with the deck, with a
    6 mm skirt that fits inside the tub. Seal the joint with electrical tape."""
    ix, iy = TUB_X - WALL + 2 - LID_CLEAR, TUB_W / 2 - WALL + 2 - LID_CLEAR
    plate = box(-ix, ix, -iy, iy, 0, 3)
    lip_o = box(-ix + 2, ix - 2, -iy + 2, iy - 2, -6, 0.01)
    lip_i = box(-ix + 3.6, ix - 3.6, -iy + 3.6, iy - 3.6, -7, 0.02)
    return plate + (lip_o - lip_i)


# -------------------------------------------------------------------- wheel
def make_wheel():
    """Cupped paddle wheel: rolls on its outer flange and paddle tips on land,
    paddles push water. Printed flange-down. Axis along +z; the hull side is
    z = WHEEL_W, where the hub face sits 0.5 mm off the hull side."""
    seg = 96
    flange = cyl_z(WHEEL_R_TIP, 0, 2.0, 0, 0, seg)
    rim = cyl_z(WHEEL_R_RIM, 0, WHEEL_W, 0, 0, seg) - cyl_z(WHEEL_R_RIM - 2.0, -1, WHEEL_W + 1, 0, 0, seg)
    web = cyl_z(WHEEL_R_RIM - 1, 0, 2.5, 0, 0, seg)
    for i in range(6):                      # lightening holes
        a = 2 * math.pi * i / 6
        web = web - cyl_z(8.0, -1, 4, 22 * math.cos(a), 22 * math.sin(a), 32)
    paddles = Manifold()
    for i in range(PADDLES):
        a = 360.0 * i / PADDLES
        p = (box(WHEEL_R_RIM - 1.5, WHEEL_R_TIP, -1.25, 1.25, 0, WHEEL_W)
             .rotate([0, 0, a + 12]))       # slight sweep
        paddles = paddles + p
    # outer edge of paddles trimmed to a circle
    paddles = paddles ^ cyl_z(WHEEL_R_TIP, -1, WHEEL_W + 1, 0, 0, seg)
    hub = cyl_z(7.5, 0, WHEEL_W, 0, 0, 48)
    w = flange + rim + web + paddles + hub
    # TT motor double-D shaft bore (5.5 dia, 3.8 across flats), 7 mm deep from the hull side
    bore = (cyl_z(2.8, WHEEL_W - 7, WHEEL_W + 1, 0, 0, 32)
            ^ box(-1.95, 1.95, -3, 3, WHEEL_W - 7.1, WHEEL_W + 1.1))
    w = w - bore
    w = w - cyl_z(1.1, WHEEL_W - 10, WHEEL_W, 0, 0, 16)   # M2 x 10 retaining screw
    w = w - cyl_z(3.0, -1, WHEEL_W - 10, 0, 0, 24)          # screwdriver / head access
    return w


# ---------------------------------------------------------------- export
def to_trimesh(m):
    mesh = m.to_mesh()
    return trimesh.Trimesh(vertices=np.asarray(mesh.vert_properties)[:, :3],
                           faces=np.asarray(mesh.tri_verts), process=True)


def main():
    os.makedirs(OUT, exist_ok=True)
    parts = {
        "hull.stl": make_hull(),
        "lid.stl": make_lid().mirror([0, 0, 1]),  # print plate-down
        "paddle_wheel_x4.stl": make_wheel(),
    }
    for name, m in parts.items():
        t = to_trimesh(m)
        bb = t.bounds
        t.apply_translation([-(bb[0][0] + bb[1][0]) / 2, -(bb[0][1] + bb[1][1]) / 2, -bb[0][2]])
        t.export(os.path.join(OUT, name))
        ext = t.extents
        print(f"{name:22s} {ext[0]:6.1f} x {ext[1]:6.1f} x {ext[2]:5.1f} mm  "
              f"vol {t.volume / 1000:7.1f} cm3  watertight={t.is_watertight}")
    return parts


if __name__ == "__main__":
    main()
