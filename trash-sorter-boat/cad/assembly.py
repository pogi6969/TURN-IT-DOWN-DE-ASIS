"""Places every part (and stand-ins for bought parts) in boat coordinates."""
import math

import numpy as np
from manifold3d import Manifold

from common import *
import belt
import electronics as el
import frames as fr
import hull
import sorter as so

DRUM_TO_LOCAL = matrix(np.array([[1, 0, 0], [0, 0, 1], [0, 1, 0]], float), [0, 0, 0])

COL = {"hull": "#f2a33a", "deck": "#d9d4c7", "frame": "#3c6fb0", "belt": "#2b2b2b", "drum": "#8a8a8a",
       "sorter": "#4e9a55", "bucket": "#e8e2d0", "flap": "#c94c3c", "elec": "#5b5f66", "buy": "#9aa3ad",
       "wheel": "#333333"}


def _conv(m, which):
    return m.transform(conveyor_matrix(which))


def _links(which, c_dist, n, cleat_every=None):
    plain, cleat = belt.belt_link(False), belt.belt_link(True)
    out = Manifold()
    for i, (p0, p1) in enumerate(belt.belt_path(c_dist, n)):
        p0, p1 = np.array(p0), np.array(p1)
        a = (p1 - p0) / np.linalg.norm(p1 - p0)
        c = np.array([-a[1], a[0]])
        rot = np.column_stack([[a[0], 0, a[1]], [0, 1, 0], [c[0], 0, c[1]]])
        mid = (p0 + p1) / 2
        lk = cleat if (cleat_every and i % cleat_every == 0) else plain
        out = out + lk.transform(matrix(rot, [mid[0], 0, mid[1]]))
    return _conv(out, which)


def _drum(drive, u, which, phase=0.0):
    return _conv(belt.drum(drive).rotate([0, 0, phase]).transform(DRUM_TO_LOCAL).translate([u, 0, 0]), which)


def _motor_local(u, which):
    return _conv(cyl_y(MOTOR_D / 2, FRAME_IN + FRAME_T, FRAME_IN + FRAME_T + MOTOR_LEN, u, 0, 32), which)


def both(m):
    return [m, mirror_y(m)]


def flap_placed(xh, open_deg=0.0):
    f = so.flap().rotate([0, 0, -open_deg]).translate([xh, HINGE_Y, so.FLAP_Z0])
    return f


def parts(open_flap=True):
    """List of (name, manifold, colour key, printed?)."""
    P = []
    add = lambda n, m, c, pr=True: P.append((n, m, c, pr))
    for i, (x0, x1) in enumerate(SEG_X):
        k = "stern" if i == 0 else "bow" if i == len(SEG_X) - 1 else "mid"
        seg = hull.pontoon_segment(k).translate([x0 - SEG_X[1][0] if k == "mid" else 0, 0, 0])
        add(f"pontoon_{i}_{k}_port", seg, "hull")
        add(f"pontoon_{i}_{k}_stbd", mirror_y(seg), "hull")
    deck = box(-BOAT_L / 2, BOAT_L / 2, -P_OUT, P_OUT, P_H, DECK_Z) - box(C1_OPEN_X, BOAT_L, -P_IN, P_IN, P_H - 1, DECK_Z + 1)
    add("deck (5 mm PVC foam)", deck, "deck", False)
    for ax in (AXLE_X, -AXLE_X):
        sad = hull.motor_saddle().translate([ax, (POCKET_Y0 + P_OUT - 3) / 2, SHAFT_Z])
        mot = cyl_y(MOTOR_D / 2, P_OUT - 3 - MOTOR_LEN, P_OUT - 3, ax, SHAFT_Z, 32)
        wh = hull.paddle_wheel().rotate([90, 0, 0]).translate([ax, P_OUT + WHEEL_GAP + WHEEL_W, SHAFT_Z])
        for s, m in zip(("port", "stbd"), both(sad)):
            add(f"motor_saddle_{ax:+.0f}_{s}", m, "frame")
        for s, m in zip(("port", "stbd"), both(mot)):
            add(f"drive_motor_{ax:+.0f}_{s}", m, "buy", False)
        for s, m in zip(("port", "stbd"), both(wh)):
            add(f"wheel_{ax:+.0f}_{s}", m, "wheel")
    # intake conveyor C1
    add("c1_lower", _conv(fr.c1_lower(), "c1"), "frame")
    add("c1_upper", _conv(fr.c1_upper(), "c1"), "frame")
    sp = _conv(fr.c1_splice().translate([0, FRAME_IN + FRAME_T, 0]), "c1")
    for s, m in zip(("port", "stbd"), both(sp)):
        add(f"c1_splice_{s}", m, "frame")
    lg = fr.c1_leg().translate([0, FRAME_IN + FRAME_T, 0])
    for s, m in zip(("port", "stbd"), both(lg)):
        add(f"c1_leg_{s}", m, "frame")
    add("c1_drum_tail", _drum(False, 0, "c1"), "drum")
    add("c1_drum_head", _drum(True, C1_C, "c1", 22.5 if (C1_C / PITCH) % 1 > 0.25 else 0.0), "drum")
    add("c1_motor", _motor_local(C1_C, "c1"), "buy", False)
    add("c1_belt", _links("c1", C1_C, LINKS_C1, CLEAT_EVERY), "belt")
    # sorting conveyor C2
    add("c2_front", _conv(fr.c2_front(), "c2"), "frame")
    for i in (0, 1):
        add(f"c2_beam_{i}", _conv(fr.c2_beam_piece(i), "c2"), "frame")
    add("c2_head_stand_port", _conv(fr.c2_head_stand(True), "c2"), "frame")
    add("c2_head_stand_stbd", mirror_y(_conv(fr.c2_head_stand(False), "c2")), "frame")
    add("c2_drum_tail", _drum(False, 0, "c2"), "drum")
    half = (C2_C / PITCH) % 1 > 0.25
    add("c2_drum_head", _drum(True, C2_C, "c2", 22.5 if half else 0.0), "drum")
    add("c2_motor", _motor_local(C2_C, "c2"), "buy", False)
    add("c2_belt", _links("c2", C2_C, LINKS_C2), "belt")
    add("reject_tray", so.reject_tray(), "sorter")
    # sorter
    for i, bay in ((0, "front"), (1, "rear")):
        for s, m in zip(("port", "stbd"), both(so.piece(so.sorter_frame(), i))):
            add(f"sorter_frame_{bay}_{s}", m, "sorter")
        for s, m in zip(("port", "stbd"), both(so.piece(so.sorter_cover(), i))):
            add(f"sorter_cover_{bay}_{s}", m, "sorter")
    bins = {"port": (1, 3), "stbd": (2, 4)}
    for side in ("port", "stbd"):
        for (xh, (bx0, bx1), nbin) in zip(so.HINGES, so.BAYS, bins[side]):
            ang = 60.0 if (open_flap and nbin == 1) else 0.0
            items = [("flap", flap_placed(xh, ang), "flap", True),
                     ("servo_bridge", so.servo_bridge().translate([xh, HINGE_Y, SERVO_BRIDGE_Z]), "sorter", True),
                     ("servo", box(xh + so.SERVO_OFF - 11.4, xh + so.SERVO_OFF + 11.4, HINGE_Y - 6.1, HINGE_Y + 6.1,
                                   SERVO_BRIDGE_Z - 6.8, SERVO_BRIDGE_Z + 16), "buy", False),
                     ("bucket", so.bucket().translate([bx0 + 0.5, 0, 0]), "bucket", True)]
            for (n, m, c, pr) in items:
                add(f"{n}_bin{nbin}", m if side == "port" else mirror_y(m), c, pr)
    # electronics
    add("electronics_box", el.electronics_box(), "elec")
    add("battery_box", mirror_y(el.battery_box()), "elec")
    add("lid_port", el.box_lid(), "elec")
    add("lid_stbd", mirror_y(el.box_lid()), "elec")
    add("camera_mast", el.camera_mast(), "frame")
    add("nav_cam_bracket", el.nav_cam_bracket(), "frame")
    z = DECK_Z + el.BOX_H + 2.5
    add("nav_camera", box(el.BOX_X[1] - 3, el.BOX_X[1] + 22, el.BOX_YC - 25, el.BOX_YC + 25, z + 12, z + 42), "buy", False)
    add("sort_camera", box(el.CAM_X - 12.5, el.CAM_X + 12.5, -12, 12, el.CAM_Z - 6, el.CAM_Z), "buy", False)
    return P
