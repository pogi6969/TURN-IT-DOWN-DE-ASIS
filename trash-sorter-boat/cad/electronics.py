"""Electronics box (port bow deck), battery box (starboard bow deck), shared lid,
sorting-camera mast and navigation-camera bracket. Boat coordinates, port side."""
import math

from manifold3d import Manifold

from common import *

BOX_X = (120.0, 300.0)
BOX_Y = (62.0, 148.0)
BOX_H = 60.0
WALL = 2.4
PI_HOLES = [(0, 0), (58, 0), (0, 23), (58, 23)]            # Raspberry Pi Zero 2 W, M2.5
L298_HOLES = [(0, 0), (37, 0), (0, 37), (37, 37)]          # L298N module, M3
CAM_X = (CAM_ZONE[0] + CAM_ZONE[1]) / 2                    # sorting camera over the camera zone
CAM_Z = C2_Z_SURF + 108.0


def _shell(h):
    (x0, x1), (y0, y1) = BOX_X, BOX_Y
    m = box(x0, x1, y0, y1, DECK_Z, DECK_Z + h) - box(x0 + WALL, x1 - WALL, y0 + WALL, y1 - WALL, DECK_Z + WALL, DECK_Z + h + 1)
    for (x, y) in ((x0 + 8, y0 + 8), (x1 - 8, y0 + 8), (x0 + 8, y1 - 8), (x1 - 8, y1 - 8)):  # deck screws
        m = m - cyl_z(1.7, DECK_Z - 1, DECK_Z + WALL + 1, x, y, 16)
    m = m - cyl_z(5.0, DECK_Z - 1, DECK_Z + WALL + 1, AXLE_X, POCKET_Y0 + 8, 24)  # drive-motor wires
    m = m - cyl_x(6.0, x0 - 1, x0 + WALL + 1, 0, 0).translate([0, y0 + 20, DECK_Z + 14])  # cable exit, aft wall
    return m


def _standoffs(holes, ox, oy, r_hole, h=6.0):
    m = Manifold()
    cut = Manifold()
    for (dx, dy) in holes:
        m = m + cyl_z(3.2, DECK_Z + WALL - 0.01, DECK_Z + WALL + h, ox + dx, oy + dy, 24)
        cut = cut + cyl_z(r_hole, DECK_Z + WALL, DECK_Z + WALL + h + 1, ox + dx, oy + dy, 16)
    return m, cut


def electronics_box():
    m = _shell(BOX_H)
    ox, oy = BOX_X[1] - 14 - 58, BOX_Y[0] + 30                 # Pi Zero 2 W at the bow end
    a, c1 = _standoffs(PI_HOLES, ox, oy, 1.1)
    b, c2 = _standoffs(L298_HOLES, BOX_X[0] + 10, BOX_Y[0] + 8, 1.25)        # drive L298N
    c, c3 = _standoffs(L298_HOLES, BOX_X[0] + 58, BOX_Y[0] + 8, 1.25)        # conveyor L298N
    m = (m + a + b + c) - c1 - c2 - c3
    m = m - box(BOX_X[1] - 1, BOX_X[1] + 1, BOX_Y[0] + 20, BOX_Y[0] + 34, DECK_Z + 12, DECK_Z + 22)  # USB to nav cam
    return m


def battery_box():
    m = _shell(BOX_H)
    m = m - box(BOX_X[0] + 60, BOX_X[0] + 81.5, BOX_Y[1] - 1, BOX_Y[1] + 1, DECK_Z + 25, DECK_Z + 40)  # rocker switch 21x15
    m = m - cyl_y(6.5, BOX_Y[1] - 1, BOX_Y[1] + 1, BOX_X[0] + 110, DECK_Z + 32, 32)                   # charge port / fuse
    for x in (BOX_X[0] + 30, BOX_X[0] + 100):                                 # cell-pack strap slots
        m = m - box(x - 2, x + 2, BOX_Y[0] + 10, BOX_Y[1] - 10, DECK_Z - 1, DECK_Z + WALL + 1)
    return m


def box_lid():
    (x0, x1), (y0, y1) = BOX_X, BOX_Y
    z = DECK_Z + BOX_H
    m = box(x0, x1, y0, y1, z, z + 2.5)
    i = WALL + 0.3                                                            # lip fits inside the walls
    m = m + (box(x0 + i, x1 - i, y0 + i, y1 - i, z - 5, z + 0.01)
             - box(x0 + i + 1.6, x1 - i - 1.6, y0 + i + 1.6, y1 - i - 1.6, z - 6, z + 1))
    for (x, y) in ((x1 - 12, 95.0), (x1 - 12, 115.0)):                       # nav-camera bracket bolts
        m = m - cyl_z(1.7, z - 1, z + 4, x, y, 16)
    return m


def camera_mast():
    """Bolts to the C2 front frame's port wall; holds the Pi camera 108 mm over the
    belt, looking down, with an LED strip slot either side of the lens."""
    y_wall = FRAME_IN + FRAME_T
    bolt_z = C2_AXIS_Z + 55.0
    m = box(CAM_X - 28, CAM_X + 28, y_wall, y_wall + 4, bolt_z - 12, CAM_Z + 12)   # upright
    m = m + box(CAM_X - 16, CAM_X + 16, -18, y_wall + 4, CAM_Z + 4, CAM_Z + 12)   # arm over the belt
    m = m + box(CAM_X - 16, CAM_X + 16, -18, 18, CAM_Z, CAM_Z + 12)               # camera plate
    m = m - box(CAM_X - 5, CAM_X + 5, -5, 5, CAM_Z - 1, CAM_Z + 13)               # lens window
    for dx in (-10.5, 10.5):
        for dy in (-6.25, 6.25):
            m = m - cyl_z(1.0, CAM_Z - 1, CAM_Z + 13, CAM_X + dx, dy, 12)          # Pi camera M2
    for dy in (-14, 14):
        m = m - box(CAM_X - 15, CAM_X + 15, dy - 1.5, dy + 1.5, CAM_Z - 1, CAM_Z + 3)  # LED strip slots
    for x in (CAM_X - 10.0, CAM_X + 10.0):
        m = m - cyl_y(1.7, y_wall - 1, y_wall + 5, x, bolt_z, 16)
    m = m + Manifold.hull_points([[x, y, z] for x in (CAM_X - 2, CAM_X + 2)            # gusset
                                  for (y, z) in ((y_wall + 4, CAM_Z + 4), (y_wall + 4, CAM_Z - 30), (y_wall - 25, CAM_Z + 4))])
    return m


def nav_cam_bracket():
    """L-bracket on the electronics-box lid; 1/4-20 tripod bolt or zip ties for a USB webcam."""
    z = DECK_Z + BOX_H + 2.5
    x1 = BOX_X[1]
    base = box(x1 - 20, x1 - 4, 85, 125, z, z + 4)
    for y in (95.0, 115.0):
        base = base - cyl_z(1.7, z - 1, z + 5, x1 - 12, y, 16)
    up = box(x1 - 8, x1 - 4, 85, 125, z, z + 40)
    m = base + up
    m = m - cyl_x(3.3, x1 - 9, x1 - 3, 105, z + 28, 24)                   # 1/4" bolt
    for y in (90.0, 120.0):
        m = m - box(x1 - 9, x1 - 3, y - 1.5, y + 1.5, z + 8, z + 14)       # zip-tie slots
    return m
