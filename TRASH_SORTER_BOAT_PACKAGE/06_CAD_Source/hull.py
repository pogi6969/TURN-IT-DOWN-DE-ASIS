"""Pontoon segments, dowels, drive-motor saddles and paddle wheels."""
import math

import numpy as np
from manifold3d import Manifold

from common import *

# C1 frame bosses screw into the bow segments' inner walls at these (u, w)
C1_BOSSES_UW = [(0.0, -20.0), (70.0, -20.0)]


def _rounded_rect_pts(x0, x1, y0, y1, z, r, n=12):
    pts = []
    for cx, cy, a0 in [(x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180), (x1 - r, y0 + r, 270)]:
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append([cx + r * math.cos(a), cy + r * math.sin(a), z])
    return pts


def _segment_body(kind):
    x0, x1 = {"stern": SEG_X[0], "mid": SEG_X[1], "bow": SEG_X[-1]}[kind]
    y0, y1 = P_IN, P_OUT
    if kind == "mid":
        return box(x0, x1, y0, y1, 0, P_H)
    # bow / stern: raked end, rounded corners at the free end only
    if kind == "bow":
        top = _rounded_rect_pts(x0 - 20, x1, y0, y1, P_H, 12)
        bot = _rounded_rect_pts(x0 - 20, x1 - BOW_RAKE, y0, y1, 0, 12)
        body = Manifold.hull_points(top + bot) ^ box(x0, x1 + 1, y0, y1, -1, P_H + 1)
    else:
        top = _rounded_rect_pts(x0, x1 + 20, y0, y1, P_H, 12)
        bot = _rounded_rect_pts(x0 + 25, x1 + 20, y0, y1, 0, 12)
        body = Manifold.hull_points(top + bot) ^ box(x0 - 1, x1, y0, y1, -1, P_H + 1)
    return body


def _motor_pocket(ax):
    cut = box(ax - 13.5, ax + 13.5, POCKET_Y0, P_OUT - 3.0, POCKET_FLOOR, P_H + 1)
    cut = cut + cyl_y(4.0, P_OUT - 4, P_OUT + 1, ax, SHAFT_Z)                 # shaft + gearbox boss
    for s in (-1, 1):                                                       # M3 face screws (slotted)
        xa, xb = ax + s * 7.5, ax + s * 9.5
        cut = cut + (cyl_y(1.7, P_OUT - 4, P_OUT + 1, xa, SHAFT_Z) + cyl_y(1.7, P_OUT - 4, P_OUT + 1, xb, SHAFT_Z)
                     + box(min(xa, xb), max(xa, xb), P_OUT - 4, P_OUT + 1, SHAFT_Z - 1.7, SHAFT_Z + 1.7))
    cut = cut + cyl_y(2.0, P_OUT - 4, P_OUT + 1, ax, POCKET_FLOOR + 2.5)      # drain
    return cut


def pontoon_segment(kind):
    """Port-side segment (y > 0). Mirror for starboard. Printed solid with low
    infill so each segment is its own sealed buoyancy chamber."""
    x0, x1 = {"stern": SEG_X[0], "mid": SEG_X[1], "bow": SEG_X[-1]}[kind]
    m = _segment_body(kind)
    # alignment dowel holes on joint faces
    faces = {"stern": [x1], "mid": [x0, x1], "bow": [x0]}[kind]
    for fx in faces:
        d = 1 if fx == x0 else -1
        for dy in (-25, 25):
            m = m - cyl_x(3.2, fx - 1 if d > 0 else fx - 12, fx + 12 if d > 0 else fx + 1, P_CY + dy, 50)
    # blind holes in the top for deck screws (M3 self-tapping or #4 wood screws)
    for hx in (x0 + 20, x1 - 20, (x0 + x1) / 2):
        for dy in (-30, 30):
            m = m - cyl_z(1.25, P_H - 14, P_H + 1, hx, P_CY + dy, 16)
    if kind in ("bow", "stern"):
        ax = AXLE_X if kind == "bow" else -AXLE_X
        m = m - _motor_pocket(ax)
    if kind == "bow":
        for (u, w) in C1_BOSSES_UW:     # blind holes for the intake-frame bosses
            bx, bz = c1_point(u, w)
            m = m - cyl_y(1.3, P_IN - 1, P_IN + 14, bx, bz, 16)
    return m


def dowel():
    return cyl_z(3.0, 0, 22, 0, 0, 32) - (cyl_z(4, 21, 23, 0, 0) - Manifold.cylinder(2, 3.0, 2.2, 32).translate([0, 0, 20.5]))


def motor_saddle():
    """Sits on the drive motor in its pocket; the deck clamps it down.
    Local z = 0 is the motor axis. Print flat face down."""
    h = P_H - SHAFT_Z
    return box(-13, 13, -20, 20, 0, h) - cyl_y(MOTOR_D / 2 + 0.3, -21, 21, 0, 0, 64)


def paddle_wheel():
    """Cupped paddle wheel for a JGA25-370 (4 mm D shaft). Flange (outboard)
    at z = 0, hub face (hull side) at z = WHEEL_W. Print flange-down."""
    seg = 120
    w = cyl_z(WHEEL_R, 0, 2.5, 0, 0, seg)
    w = w + (cyl_z(WHEEL_RIM, 0, WHEEL_W, 0, 0, seg) - cyl_z(WHEEL_RIM - 2.0, -1, WHEEL_W + 1, 0, 0, seg))
    web = cyl_z(WHEEL_RIM - 1, 0, 2.5, 0, 0, seg)
    for i in range(6):
        a = 2 * math.pi * i / 6
        web = web - cyl_z(15.0, -1, 4, 40 * math.cos(a), 40 * math.sin(a), 40)
    w = w + web
    paddles = Manifold()
    for i in range(10):
        paddles = paddles + box(WHEEL_RIM - 2, WHEEL_R, -1.25, 1.25, 0, WHEEL_W).rotate([0, 0, 360 * i / 10 + 10])
    w = w + (paddles ^ cyl_z(WHEEL_R, -1, WHEEL_W + 1, 0, 0, seg))
    w = w + cyl_z(11.0, 0, WHEEL_W, 0, 0, 48)
    for i in range(3):                                   # hub ribs
        w = w + box(10, WHEEL_RIM - 2, -2, 2, 0, 14).rotate([0, 0, 120 * i + 30])
    bore = cyl_z(2.05, WHEEL_W - 11, WHEEL_W + 1, 0, 0, 32) ^ box(-3, 1.55, -3, 3, WHEEL_W - 11.1, WHEEL_W + 1.1)
    w = w - bore - cyl_z(2.6, -1, WHEEL_W - 11, 0, 0, 24)          # screwdriver access
    zs = WHEEL_W - 5.0                                             # M3 set screw onto the flat
    w = w - cyl_x(1.7, -1, 12, 0, zs, 16)
    w = w - box(5.0, 7.6, -3.0, 3.0, zs - 3.0, WHEEL_W + 1)        # M3 nut trap, drop-in from hub face
    return w
