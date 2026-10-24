"""Shared parameters and geometry helpers for the trash-sorting boat.

Units: mm. Boat frame: x = forward, y = port (left), z = up, z = 0 is the
pontoon bottom. Conveyor parts are modelled in a local frame
(u = along the belt, tail drum -> head drum; v = across = boat y;
w = belt normal, carrying side positive) and placed with conveyor_matrix().
"""
import math

import numpy as np
from manifold3d import Manifold, CrossSection

# ------------------------------------------------------------------ hull
BOAT_L = 760.0            # 4 pontoon segments x 190
SEG_L = 190.0
SEG_X = [(-BOAT_L / 2 + i * SEG_L, -BOAT_L / 2 + (i + 1) * SEG_L) for i in range(4)]  # stern, mid, mid, bow
P_W = 115.0               # pontoon width
P_H = 100.0               # pontoon height
P_IN = 107.0              # |y| of pontoon inner face (gap = 214 for the 180 mm intake)
P_OUT = P_IN + P_W        # 175, |y| of outer face
SORTER_OUT = 178.0        # |y| of the sorter bays' open outer side
POCKET_Y0 = P_OUT - 73.0  # inboard end of the drive-motor pockets
P_CY = P_IN + P_W / 2     # 117.5
DECK_T = 5.0              # 5 mm PVC foam (Sintra) deck
DECK_Z = P_H + DECK_T     # 105, deck top
BOW_RAKE = 70.0           # bottom of bow ends 70 mm behind the bow tip
C1_OPEN_X = BOAT_L / 2 - 153.0   # deck is open between pontoons for x > this

# ------------------------------------------------------------------ drive
AXLE_X = BOAT_L / 2 - 95.0       # wheel axles
SHAFT_Z = 78.0            # drive motor shaft height
WHEEL_R = 88.0            # paddle tip radius (ground at z = -10)
WHEEL_RIM = 70.0
WHEEL_W = 34.0
WHEEL_GAP = 3.0           # hub face to pontoon side
POCKET_FLOOR = 65.0
MOTOR_D = 25.0            # JGA25-370 gear motor
MOTOR_LEN = 66.0          # gearbox face to back of terminals (max)
MOTOR_HOLE_DX = 8.5       # gearbox face M3 holes at +/-8.5 mm (slotted 7.5-9.5)

# ------------------------------------------------------------------ belt
BELT_W = 120.0
PITCH = 20.0
TEETH = 8
R_PIN = PITCH / (2 * math.sin(math.pi / TEETH))   # 26.13 pin circle radius
KNUCKLE_R = 3.5
PLATE_IN, PLATE_OUT = 3.5, 6.5                    # plate between these heights over the pin line
SURF_R = R_PIN + PLATE_OUT                        # 32.6, carrying surface over drum axis
CLEAT_H = 20.0
PIN_HOLE = 2.2            # 2.0 mm bicycle-spoke or 1.75 mm filament pins
DRUM_W = BELT_W - 2.0
FRAME_IN = BELT_W / 2 + 1.0       # |v| of conveyor side-wall inner face (sorting belt)
C1_W = 180.0                      # intake (collection) belt width
C1_FRAME_IN = C1_W / 2 + 1.0
FRAME_T = 4.0

# ------------------------------------------------------------------ conveyors
C1_ALPHA = math.radians(50.0)
C1_TAIL = (BOAT_L / 2 - 60.0, 50.0)   # (x, z) of the intake tail drum axis (cleat tips clear the ground on land)
C1_C = 210.0              # drum centre distance -> 2*210/20 + 8 = 29 links
C2_Z_SURF = 185.0         # sorting belt surface height
C2_AXIS_Z = C2_Z_SURF - SURF_R
C2_C = 440.0              # 2*440/20 + 8 = 52 links


def c1_point(u, w):
    a = C1_ALPHA
    return (C1_TAIL[0] - u * math.cos(a) + w * math.sin(a),
            C1_TAIL[1] + u * math.sin(a) + w * math.cos(a))


C1_HEAD = c1_point(C1_C, 0.0)                     # (100.7, 213.9)
C2_TAIL_X = C1_HEAD[0] - 75.0                     # 25.7
C2_HEAD_X = C2_TAIL_X - C2_C                      # -284.3

# ------------------------------------------------------------------ sorter
FLAP_ANGLE = math.radians(60.0)
WALL_Y = BELT_W / 2 + 2.0          # |y| of sorter-frame inner wall
HINGE_Y = WALL_Y + 3.0    # |y| of flap hinge (post) axis; the closed flap sits in the wall
FLAP_REACH = HINGE_Y + BELT_W / 2 - 2.0           # tip stops 2 mm short of far belt edge
FLAP_L = FLAP_REACH / math.sin(FLAP_ANGLE)        # 93.8
FLAP_H = 35.0
CAM_ZONE = (C2_TAIL_X - 20.0, C2_TAIL_X - 120.0)  # landing / camera zone x range
STATION_A = CAM_ZONE[1] - FLAP_L                  # hinge x of bins 1 (port) + 2 (stbd)
STATION_B = STATION_A - FLAP_L - 10.0             # hinge x of bins 3 (port) + 4 (stbd)
SORTER_X = (STATION_B - 3.0, CAM_ZONE[1] + 3.0)   # sorter frame x extent
SORTER_SPLIT = STATION_B + FLAP_L + 4.0           # sorter frames/covers/bed beam split here (one piece per bay)
C2_EAR_X = (SORTER_X[1] - 45.0, SORTER_SPLIT + 12.0, SORTER_SPLIT - 12.0, SORTER_X[0] + 25.0)  # C2 bed-beam ear bolts
COVER_Z = 236.0           # underside of sorter cover
MOUTH_Z = 183.0           # bottom lip of the bin mouths (belt surface 185)
SERVO_BRIDGE_Z = 262.0    # top of the servo bridge plates

LINKS_C1 = int(round(2 * C1_C / PITCH)) + TEETH
LINKS_C2 = int(round(2 * C2_C / PITCH)) + TEETH
CLEAT_EVERY = 4


# ------------------------------------------------------------------ helpers
def box(x0, x1, y0, y1, z0, z1):
    return Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def cyl_x(r, x0, x1, y, z, seg=48):
    return Manifold.cylinder(x1 - x0, r, r, seg).rotate([0, 90, 0]).translate([x0, y, z])


def cyl_y(r, y0, y1, x, z, seg=48):
    return Manifold.cylinder(y1 - y0, r, r, seg).rotate([-90, 0, 0]).translate([x, y0, z])


def cyl_z(r, z0, z1, x, y, seg=48):
    return Manifold.cylinder(z1 - z0, r, r, seg).translate([x, y, z0])


def union(parts):
    out = Manifold()
    for p in parts:
        out = out + p
    return out


def matrix(rot3, t):
    m = np.zeros((3, 4))
    m[:, :3] = rot3
    m[:, 3] = t
    return m


def conveyor_matrix(which):
    """Local (u, v, w) -> boat (x, y, z) for conveyor 'c1' or 'c2'."""
    if which == "c1":
        a = C1_ALPHA
        u = [-math.cos(a), 0, math.sin(a)]
        w = [math.sin(a), 0, math.cos(a)]
        origin = [C1_TAIL[0], 0, C1_TAIL[1]]
    else:
        u = [-1, 0, 0]
        w = [0, 0, 1]
        origin = [C2_TAIL_X, 0, C2_AXIS_Z]
    rot = np.column_stack([u, [0, 1, 0], w])
    return matrix(rot, origin)


def mirror_y(m):
    return m.mirror([0, 1, 0])


def prism_uw(profile_pts, v0, v1):
    """Extrude a polygon given in (u, w) along v from v0 to v1."""
    pts = list(profile_pts)
    area = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts)))
    if area < 0:
        pts = pts[::-1]
    cs = CrossSection([pts])
    # extrude along z, then map (x, y, z) = (u, w, v) -> (u, v, w)
    m = cs.extrude(v1 - v0).translate([0, 0, v0])
    return m.transform(matrix(np.array([[1, 0, 0], [0, 0, 1], [0, 1, 0]], float), [0, 0, 0]))


def circle_pts(cx, cy, r, n=32):
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n))
            for i in range(n)]
