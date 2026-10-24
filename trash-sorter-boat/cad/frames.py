"""Conveyor frames. Everything is built in the conveyor's local (u, v, w)
frame (see common.py) unless noted; build.py places parts with conveyor_matrix().
"""
import math

import numpy as np
from manifold3d import Manifold, CrossSection

from common import *
from hull import C1_BOSSES_UW

W_BOT, W_TOP = -22.0, 69.0          # C1 side-wall extent (guards reach 36 mm above the belt)
SPLICE_U = C1_C / 2
SPLICE_HOLES = [(SPLICE_U + du, w) for du in (-16.0, -8.0, 8.0, 16.0) for w in (-5.0, 50.0)]
C1_LEGS_U = (C1_C - 50.0, C1_C - 28.0)
C2_FRONT_U = (-32.0, C2_TAIL_X - (SORTER_X[1] + 1.5))   # front frame stops 1.5 mm short of the sorter frames
C2_BEAM_X = (SORTER_X[1] + 1.5, C2_HEAD_X + 30.0)


def body(u0, u1):
    """Slider bed inside the belt loop (I-beam) + side strips to the walls."""
    parts = [box(u0, u1, -38, 38, 19.4, 22.4),             # bed surface under the top-run knuckles
             box(u0, u1, -30, 30, -19, -16),               # bottom flange
             box(u0, u1, -21, -18, -19, 22.4), box(u0, u1, 18, 21, -19, 22.4)]
    for s in (-1, 1):                                       # thin strips to the walls + ribs
        y0, y1 = min(s * 20, s * 41.01), max(s * 20, s * 41.01)
        parts.append(box(u0, u1, y0, y1, -1.5, 1.5))
        u = u0
        while u <= u1 - 3:
            parts.append(box(u, u + 3, y0, y1, -8, 8))
            u += 40.0
        parts.append(box(u1 - 3, u1, y0, y1, -8, 8))
    return union(parts)


def walls(u0, u1, w0, w1):
    return box(u0, u1, FRAME_IN, FRAME_IN + FRAME_T, w0, w1) + box(u0, u1, -FRAME_IN - FRAME_T, -FRAME_IN, w0, w1)


def axle_hole(u):
    return cyl_y(3.3, -FRAME_IN - FRAME_T - 1, FRAME_IN + FRAME_T + 1, u, 0, 32)


def motor_face(u, side=1):
    """JGA25 gearbox face on the outer side of a wall at drum axis u (port = +v)."""
    y0, y1 = (FRAME_IN - 1, FRAME_IN + FRAME_T + 1) if side > 0 else (-FRAME_IN - FRAME_T - 1, -FRAME_IN + 1)
    cut = cyl_y(4.0, y0, y1, u, 0, 32)
    for s in (-1, 1):
        a, b = u + s * 7.5, u + s * 9.5
        cut = cut + cyl_y(1.7, y0, y1, a, 0, 16) + cyl_y(1.7, y0, y1, b, 0, 16) + box(min(a, b), max(a, b), y0, y1, -1.7, 1.7)
    return cut


def _trim_boat(local, which, box_boat):
    m = conveyor_matrix(which)
    inv = np.linalg.inv(np.vstack([m, [0, 0, 0, 1]]))[:3]
    return (local.transform(m) ^ box_boat).transform(inv)


def _holes(points, r=1.7):
    return union([cyl_y(r, -60, 60, u, w, 16) for (u, w) in points])


def c1_lower():
    m = walls(-32, SPLICE_U, W_BOT, W_TOP) + body(35, SPLICE_U)
    for (u, w) in C1_BOSSES_UW:                    # stand-offs to the pontoon inner walls
        for s in (-1, 1):
            m = m + cyl_y(7.0, min(s * 44, s * P_IN), max(s * 44, s * P_IN), u, w, 32)
    m = m - axle_hole(0) - _holes([p for p in SPLICE_HOLES if p[0] < SPLICE_U])
    for (u, w) in C1_BOSSES_UW:
        m = m - cyl_y(1.7, -P_IN - 1, P_IN + 1, u, w, 16)
        for s in (-1, 1):                           # screw heads sit below the inner wall face
            m = m - cyl_y(3.2, min(s * (FRAME_IN - 1), s * (FRAME_IN + 2.5)), max(s * (FRAME_IN - 1), s * (FRAME_IN + 2.5)), u, w, 24)
    return _trim_boat(m, "c1", box(-400, 312, -200, 200, 2, 400))


def c1_upper():
    m = walls(SPLICE_U, C1_C + 32, W_BOT, W_TOP) + body(SPLICE_U, C1_C - 35)
    m = m - axle_hole(C1_C) - motor_face(C1_C, +1)
    m = m - _holes([p for p in SPLICE_HOLES if p[0] > SPLICE_U])
    for ul in C1_LEGS_U:
        m = m - _holes([(ul - 8, -12), (ul + 8, -12)])
    return m


def c1_splice():
    """Bolted across the C1 frame joint on each wall's outer face (x2). Flat plate, local (u, w)."""
    p = box(SPLICE_U - 24, SPLICE_U + 22, 0, 3, -14, 59)
    return p - union([cyl_y(1.7, -1, 4, u, w, 16) for (u, w) in SPLICE_HOLES])


def c1_leg():
    """One leg per side from the C1 upper wall (outer face) down to the deck.
    Boat (x, z); y = 0..4 is the plate (assembled at |y| = 45..49)."""
    u_lo, u_hi = C1_LEGS_U[0] - 12, C1_LEGS_U[1] + 12
    pts = [c1_point(u, w) for u in (u_lo, u_hi) for w in (W_BOT, W_BOT + 18)]
    xs = [p[0] for p in pts]
    x_lo, x_hi = min(xs) - 2, max(xs) + 2
    pts += [(x_lo, DECK_Z), (x_hi, DECK_Z)]
    leg = Manifold.hull_points([[x, y, z] for (x, z) in pts for y in (0, 4)])
    leg = leg - box(x_lo + 14, x_hi - 14, -1, 5, DECK_Z + 12, c1_point(u_hi, W_BOT)[1] - 14)   # lightening window
    leg = leg + box(x_lo, x_hi, 0, 14, DECK_Z, DECK_Z + 4)                                       # foot
    for ul in C1_LEGS_U:
        for du in (-8, 8):
            x, z = c1_point(ul + du, -12)
            leg = leg - cyl_y(1.7, -1, 5, x, z, 16)
    for x in (x_lo + 7, x_hi - 7):
        leg = leg - cyl_z(1.7, DECK_Z - 1, DECK_Z + 5, x, 9.5, 16)
    return leg


def c2_front():
    """C2 tail section: walls/guides over the landing + camera zone, tail idler,
    slider bed, deck feet and the transfer chute from the intake."""
    u0, u1 = C2_FRONT_U
    w_deck = DECK_Z - C2_AXIS_Z
    w_top = 225.0 - C2_AXIS_Z
    m = walls(u0, u1, w_deck, w_top) + body(35, u1)
    for s in (-1, 1):                                                 # deck feet (outboard)
        for uf in (u0 + 2, u1 - 16):
            y0, y1 = sorted((s * (FRAME_IN + FRAME_T), s * 58))
            m = m + box(uf, uf + 14, y0, y1, w_deck, w_deck + 4)
    # transfer chute between the walls, from just outside the intake head's cleat circle down onto the belt
    def uw(x, z):
        return (C2_TAIL_X - x, z - C2_AXIS_Z)
    a, b = uw(C1_HEAD[0] - 56.0, C1_HEAD[1] + 10.0), uw(C2_TAIL_X - 23.0, C2_Z_SURF + 6.0)
    t = 3.0
    pts = [a, b, (b[0], b[1] - t), (a[0], a[1] - t)]
    m = m + prism_uw(pts, -FRAME_IN - 0.01, FRAME_IN + 0.01)
    m = m - axle_hole(0)
    for s in (-1, 1):
        for uf in (u0 + 2, u1 - 16):
            m = m - cyl_z(1.7, w_deck - 1, w_deck + 5, uf + 7, s * 52, 16)
    ir_u = C2_TAIL_X - (CAM_ZONE[1] + 14.0)                         # IR sensor window, starboard wall
    m = m - box(ir_u - 6, ir_u + 6, -FRAME_IN - FRAME_T - 1, -FRAME_IN + 1, 36, 44)
    m = m - cyl_y(1.7, -FRAME_IN - FRAME_T - 1, -FRAME_IN + 1, ir_u - 12, 40, 16)
    cam_x = (CAM_ZONE[0] + CAM_ZONE[1]) / 2
    for (um, wm) in ((C2_TAIL_X - cam_x + 10.0, 55.0), (C2_TAIL_X - cam_x - 10.0, 55.0)):   # camera mast bolts, port wall
        m = m - cyl_y(1.7, FRAME_IN - 1, FRAME_IN + FRAME_T + 1, um, wm, 16)
    return m


def c2_beam():
    """Slider bed for the sorting run; ears bolt to the sorter-frame inner walls."""
    u0, u1 = C2_TAIL_X - C2_BEAM_X[0], C2_TAIL_X - C2_BEAM_X[1]
    m = body(u0, u1) ^ box(u0, u1, -38, 38, -30, 30)                 # strips stop at the bed width
    for xe in C2_EAR_X:
        ue = C2_TAIL_X - xe
        m = m + box(ue - 6, ue + 6, -WALL_Y, WALL_Y, -8, 8)
        m = m - cyl_y(1.3, -WALL_Y - 1, WALL_Y + 1, ue, 0, 16)
    return m


def c2_head_stand(drive=False):
    """Plate beside the head drum (port = drive). Built at +v; mirror for starboard."""
    ua, ub = C2_C - 16.0, C2_C + 28.0
    w_deck = DECK_Z - C2_AXIS_Z
    m = box(ua, ub, FRAME_IN, FRAME_IN + FRAME_T, w_deck, 18)
    m = m + box(ua, ub, FRAME_IN + FRAME_T - 0.01, 58, w_deck, w_deck + 4)
    m = m + box(ub - 0.01, ub + 40, FRAME_IN, FRAME_IN + FRAME_T, -12, -2)    # arm for the reject tray
    m = m - axle_hole(C2_C)
    if drive:
        m = m - motor_face(C2_C, +1)
    for du in (-10, 22):
        m = m - cyl_z(1.7, w_deck - 1, w_deck + 5, C2_C + du, 52, 16)
    m = m - cyl_y(1.7, FRAME_IN - 1, FRAME_IN + FRAME_T + 1, ub + 32, -7, 16)
    return m
