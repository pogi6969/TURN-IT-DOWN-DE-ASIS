"""Bigger collection: bow guide booms that sweep a wide path into the intake, and
hopper wings that funnel the wide intake belt onto the narrower sorting belt.
Boat coordinates, port side; mirror for starboard."""
import math

import numpy as np
from manifold3d import Manifold

from common import *

BOOM_ANGLE = math.radians(30.0)      # outward from straight ahead
BOOM_ROOT = (BOAT_L / 2 + 4.0, P_IN + 21.0)
BOOM_T = 8.0
BOOM_LEN = 165.0
BOOM_Z = (25.0, 85.0)                # blade spans the waterline (about 50 mm)
BOOM_HOLES_S = (-30.0, -10.0)        # tab screws, along the boom axis
WING_X = (CAM_ZONE[0] - 18.0, C1_HEAD[0] - 57.0)   # clear of the camera mast and the intake cleats
WING_SCREW_X = (WING_X[0] + 12.0, WING_X[1] - 12.0)
WING_Z0 = 225.0                      # top of the sorting-conveyor guide walls


def boom_frame():
    """Matrix mapping boom-local (s along the boom, t across, z) to boat coordinates."""
    c, s = math.cos(BOOM_ANGLE), math.sin(BOOM_ANGLE)
    return matrix(np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], float), [BOOM_ROOT[0], BOOM_ROOT[1], 0])


def boom_hole_points():
    m = boom_frame()
    return [tuple((m @ np.array([sh, 0, 0, 1]))[:2]) for sh in BOOM_HOLES_S]


def boom_local():
    """Flat part: deck tab, drop arm in front of the bow, blade at the waterline.
    Local s along the boom, t = thickness (-4..4), z up. Print lying flat (t vertical)."""
    t0, t1 = -BOOM_T / 2, BOOM_T / 2
    m = box(-42, 0, t0, t1, DECK_Z, DECK_Z + 5)                       # tab on the deck
    m = m + box(0, 10, t0, t1, BOOM_Z[0], DECK_Z + 25)                # drop arm
    m = m + box(10, BOOM_LEN, t0, t1, BOOM_Z[0], BOOM_Z[1])           # blade
    m = m + Manifold.hull_points([[s, t, z] for t in (t0, t1)
                                  for (s, z) in ((-20, DECK_Z + 5), (0, DECK_Z + 5), (0, DECK_Z + 25))])   # gusset
    m = m + Manifold.hull_points([[s, t, z] for t in (t0, t1)
                                  for (s, z) in ((10, BOOM_Z[1]), (10, BOOM_Z[1] + 15), (35, BOOM_Z[1]))])
    for sh in BOOM_HOLES_S:
        m = m - cyl_z(1.7, DECK_Z - 1, DECK_Z + 6, sh, 0, 16)
    for sl in range(40, int(BOOM_LEN) - 20, 30):                      # water passes, trash does not
        m = m - box(sl, sl + 6, t0 - 1, t1 + 1, BOOM_Z[0] + 8, BOOM_Z[0] + 22)
    return m


def boom():
    return boom_local().transform(boom_frame())


def hopper_wing():
    """Sloped wing clipped on the port guide wall of the sorting conveyor; catches the
    outer part of the wide intake's discharge and slides it onto the belt."""
    x0, x1 = WING_X
    yi, yo = FRAME_IN, C1_FRAME_IN + 3.0
    zt = WING_Z0 + (yo - yi) * 1.15                                   # ~49 deg slope
    pts = [[x, y, z] for x in (x0, x1) for (y, z) in ((yi, WING_Z0), (yi, WING_Z0 + 2.6), (yo, zt), (yo, zt + 2.6))]
    m = Manifold.hull_points(pts)
    yw = FRAME_IN + FRAME_T                                           # outer face of the guide wall
    m = m + box(x0, x1, yi, yw + 2.0, WING_Z0, WING_Z0 + 3.0)         # seat on the wall top
    m = m + box(x0, x1, yw, yw + 2.0, WING_Z0 - 12.0, WING_Z0 + 0.01) # prong outside the wall
    for x in WING_SCREW_X:
        m = m - cyl_y(1.7, yw - 1, yw + 3, x, WING_Z0 - 6.0, 16)
    return m
