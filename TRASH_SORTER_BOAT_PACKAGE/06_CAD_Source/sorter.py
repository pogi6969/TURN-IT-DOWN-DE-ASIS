"""Sorter: port frame (mirror for starboard) with two bin bays, cover with
servo posts, servo bridges, removable buckets, deflector flaps, reject tray.
Boat coordinates, port side (y > 0)."""
import math

from manifold3d import Manifold

from common import *

X0, X1 = SORTER_X
WALL_T = 2.5
DIVIDER = (STATION_A - 4.5, STATION_A - 1.5)
BAYS = [(DIVIDER[1], X1 - 3.0), (X0 + 3.0, DIVIDER[0])]     # bay A (front), bay B (rear)
HINGES = [STATION_A, STATION_B]
FLAP_Z0 = C2_Z_SURF + 1.5                                  # flap bottom edge
POST_TOP = SERVO_BRIDGE_Z - 11.0                           # where the servo horn meets the post
SERVO_OFF = 5.5                                            # MG90S shaft to body centre
TAB_DX = 13.9                                              # MG90S tab holes at +/-13.9 from body centre
BRIDGE_POSTS = [(2.0, 56.0), (27.0, 56.0)]                 # relative to the hinge x, absolute y


def sorter_frame():
    top = COVER_Z
    m = box(X0, X1, WALL_Y, WALL_Y + WALL_T, DECK_Z, top)               # inner wall
    for (xa, xb) in ((X0, X0 + 3), (X1 - 3, X1), DIVIDER):              # end walls + divider
        m = m + box(xa, xb, WALL_Y, SORTER_OUT, DECK_Z, top)
    for xh in HINGES:                                                   # mouths + flap-post clearance
        m = m - box(xh, xh + FLAP_L + 0.5, WALL_Y - 1, WALL_Y + WALL_T + 1, MOUTH_Z, top + 1)
        m = m - cyl_z(4.0, MOUTH_Z + 0.5, top + 1, xh, HINGE_Y, 32)
    for xh in HINGES:                                                   # bottom pivot bosses
        m = m + box(xh - 3.5, xh + 3.5, WALL_Y, HINGE_Y + 4, MOUTH_Z - 14, MOUTH_Z)
        m = m - cyl_z(1.7, MOUTH_Z - 8, MOUTH_Z + 1, xh, HINGE_Y, 16)
    for xt in (X0 + 10, (DIVIDER[0] + DIVIDER[1]) / 2, X1 - 10):            # deck tabs, under the belt return run
        m = m + box(xt - 7, xt + 7, 30, WALL_Y + 0.01, DECK_Z, DECK_Z + 4)
        m = m - cyl_z(1.7, DECK_Z - 1, DECK_Z + 5, xt, 36, 16)
    for xe in C2_EAR_X:                                                 # C2 bed-beam ear bolts
        m = m - cyl_y(1.7, WALL_Y - 1, WALL_Y + WALL_T + 1, xe, C2_AXIS_Z, 16)
    return m


def sorter_cover():
    """Rests on the frame walls; the two flap posts through it locate it."""
    z0, z1 = COVER_Z, COVER_Z + 3
    m = box(X0, X1, WALL_Y, SORTER_OUT, z0, z1)
    for xh in HINGES:
        m = m - cyl_z(3.6, z0 - 1, z1 + 1, xh, HINGE_Y, 24)             # flap post
        for (dx, y) in BRIDGE_POSTS:
            m = m + (cyl_z(4.0, z1 - 0.01, SERVO_BRIDGE_Z - 3, xh + dx, y, 24)
                     - cyl_z(1.25, SERVO_BRIDGE_Z - 14, SERVO_BRIDGE_Z, xh + dx, y, 16))
    return m


def servo_bridge():
    """Plate that holds one MG90S shaft-down over a flap post. Local origin = hinge axis,
    top face at z = 0 (assembled at SERVO_BRIDGE_Z)."""
    m = box(-11, 31, 36 - HINGE_Y, 61 - HINGE_Y, -3, 0)
    m = m - box(SERVO_OFF - 11.7, SERVO_OFF + 11.7, -6.4, 6.4, -4, 1)  # body drops through
    for dx in (-TAB_DX, TAB_DX):
        m = m - cyl_z(0.9, -4, 1, SERVO_OFF + dx, 0, 12)                # M2 tab screws
    for (dx, y) in BRIDGE_POSTS:
        m = m - cyl_z(1.7, -4, 1, dx, y - HINGE_Y, 16)
    return m


def flap():
    """Deflector flap / bin door. Local: post axis = z axis, plate along +x on the
    belt side (y < 0 for port), bottom edge at z = 0. Print lying on the y = -3 face."""
    plate = box(0, FLAP_L - 0.5, -3.0, -0.5, 0, FLAP_H)
    post = cyl_z(3.0, 0, POST_TOP - FLAP_Z0, 0, 0, 32) ^ box(-3, 3, -3, 3, -1, 200)
    pin = cyl_z(1.5, -7, 0.01, 0, 0, 16) ^ box(-1.5, 1.5, -1.5, 1.5, -8, 1)
    m = plate + post + pin
    h = POST_TOP - FLAP_Z0
    m = m - box(-3.5, 3.5, -1.1, 1.1, h - 5, h + 1)                     # slot for the servo horn arm
    m = m - cyl_z(0.9, h - 8, h + 1, 0, 0, 12)                          # horn screw
    return m


def bucket():
    """Removable bin liner, slides out to the side. Local x along the bay, y outboard."""
    L = BAYS[0][1] - BAYS[0][0] - 1.0
    y0, y1 = WALL_Y + WALL_T + 1.5, SORTER_OUT - 2.0
    z0, z1 = DECK_Z + 0.5, MOUTH_Z - 2.0
    m = box(0, L, y0, y1, z0, z1) - box(1.6, L - 1.6, y0 + 1.6, y1 - 1.6, z0 + 1.6, z1 + 1)
    for xa in (-1, L - 6):                                              # clear the flap pivot bosses
        m = m - box(xa, xa + 7, y0 - 1, HINGE_Y + 4.5, MOUTH_Z - 15, z1 + 1)
    m = m + (box(L / 2 - 15, L / 2 + 15, y1 - 0.01, y1 + 8, z1 - 14, z1 - 2)
             - box(L / 2 - 10, L / 2 + 10, y1 + 1.5, y1 + 6.5, z1 - 15, z1 - 1))  # pull handle
    return m


def reject_tray():
    """Catches anything no flap diverted; hangs off the head-stand arms behind the stern."""
    xh = C2_HEAD_X
    x0, x1 = xh - 70.0, xh - 34.0
    z0, z1 = 118.0, 162.0
    m = box(x0, x1, -FRAME_IN + 0.5, FRAME_IN - 0.5, z0, z1) - box(x0 + 2, x1 - 2, -FRAME_IN + 2.5, FRAME_IN - 2.5, z0 + 2, z1 + 1)
    m = m - cyl_y(1.7, -FRAME_IN - 1, FRAME_IN + 1, xh - 60.0, C2_AXIS_Z - 7, 16)
    return m
