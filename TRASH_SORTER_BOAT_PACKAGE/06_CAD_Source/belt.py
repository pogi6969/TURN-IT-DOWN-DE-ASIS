"""Printed modular link belt (80 mm wide, 20 mm pitch) and 8-tooth sprocket drums.

Link frame: a = travel direction, b = across the belt, c = outward (carrying side).
Pins (2.0 mm bicycle-spoke pieces or 1.75 mm filament) run along b at a = +/-10.
"""
import math

import numpy as np
from manifold3d import Manifold, CrossSection

from common import *

def _segments(width):
    """Odd number of knuckle segments across the belt: A (leading pin) at even
    indices, B (trailing pin) at odd ones. Returns (seg, A centres, B centres)."""
    n = int(round(width / 16.0))
    n += 1 - n % 2
    seg = width / n
    c = [-width / 2 + seg * (k + 0.5) for k in range(n)]
    return seg, c[0::2], c[1::2]


def _ac_prism(pts, b0, b1):
    """Polygon in (a, c) extruded along b."""
    m = CrossSection([pts]).extrude(b1 - b0).translate([0, 0, b0])
    return m.transform(matrix(np.array([[1, 0, 0], [0, 0, 1], [0, 1, 0]], float), [0, 0, 0]))


def _d_knuckle(a0, b0, b1):
    pts = [(a0 + KNUCKLE_R * math.cos(math.radians(t)), KNUCKLE_R * math.sin(math.radians(t)))
           for t in range(180, 361, 10)]
    pts += [(a0 + KNUCKLE_R, PLATE_OUT), (a0 - KNUCKLE_R, PLATE_OUT)]
    return _ac_prism(pts, b0, b1)


def belt_link(cleat=False, width=BELT_W):
    half = width / 2
    seg, A_SEGS, B_SEGS = _segments(width)
    KNUCKLE_LEN = seg - 0.6
    m = _ac_prism([(-6, PLATE_IN), (6, PLATE_IN), (6, PLATE_OUT), (-6, PLATE_OUT)], -half, half)
    for bc in A_SEGS:
        b0, b1 = max(bc - KNUCKLE_LEN / 2, -half + 0.3), min(bc + KNUCKLE_LEN / 2, half - 0.3)
        m = m + _d_knuckle(PITCH / 2, b0, b1)
        m = m + _ac_prism([(5.9, PLATE_IN), (10, PLATE_IN), (10, PLATE_OUT), (5.9, PLATE_OUT)], b0, b1)
    for bc in B_SEGS:
        b0, b1 = bc - KNUCKLE_LEN / 2, bc + KNUCKLE_LEN / 2
        m = m + _d_knuckle(-PITCH / 2, b0, b1)
        m = m + _ac_prism([(-10, PLATE_IN), (-5.9, PLATE_IN), (-5.9, PLATE_OUT), (-10, PLATE_OUT)], b0, b1)
    for a0 in (-PITCH / 2, PITCH / 2):            # pin holes
        m = m - cyl_y(PIN_HOLE / 2, -half - 1, half + 1, a0, 0, 16)
    if cleat:
        m = m + box(-1.5, 1.5, -half + 1, half - 1, PLATE_OUT - 0.1, PLATE_OUT + CLEAT_H)
        m = m + box(-3.5, 3.5, -half + 1, half - 1, PLATE_OUT - 0.1, PLATE_OUT + 3)   # fillet foot
    else:
        for bc in [x for x in (A_SEGS + B_SEGS) if abs(x) < half - 6]:   # drain slots
            m = m - box(-1.25, 1.25, bc - 4, bc + 4, PLATE_IN - 1, PLATE_OUT + 1)
    return m


def sprocket_profile():
    """2D 8-tooth profile for the knuckle rows (seat r = 3.9 at the pin circle)."""
    tip = R_PIN * math.cos(math.pi / TEETH) + PLATE_IN - 0.45
    prof = CrossSection.circle(tip, 96)
    cuts = []
    for k in range(TEETH):
        phi = 2 * math.pi * k / TEETH
        pk = np.array([R_PIN * math.cos(phi), R_PIN * math.sin(phi)])
        cuts.append(CrossSection.circle(3.9, 24).translate(list(pk)))
        for nb in (k + 1, k - 1):                 # knuckle path as the next link swings in
            pn = np.array([R_PIN * math.cos(2 * math.pi * nb / TEETH), R_PIN * math.sin(2 * math.pi * nb / TEETH)])
            base = math.atan2(*(pn - pk)[::-1])
            for t in np.linspace(0, math.radians(24), 7):
                cand = [pk + PITCH * np.array([math.cos(base + s * t), math.sin(base + s * t)]) for s in (1, -1)]
                q = max(cand, key=lambda c: np.linalg.norm(c))
                cuts.append(CrossSection.circle(3.9, 24).translate(list(q)))
    for c in cuts:
        prof = prof - c
    return prof


def drum(drive=False, width=BELT_W):
    """Sprocket drum, axis along z (print standing). z = v; the motor side is +z."""
    half = (width - 2) / 2
    m = sprocket_profile().extrude(2 * half).translate([0, 0, -half])
    m = m + cyl_z(8.0, -half - 1.5, half + 1.5, 0, 0, 48)          # hub stubs to the side walls
    if not drive:
        return m - cyl_z(3.3, -half - 2, half + 2, 0, 0, 32)       # M6 axle
    top = half + 1.5
    bore = cyl_z(2.05, top - 10, top + 1, 0, 0, 32) ^ box(-3, 1.55, -3, 3, top - 10.1, top + 1.1)
    m = m - bore
    m = m - cyl_x(1.25, 0, 30, 0, top - 6, 16)                     # M3 grub screw onto the flat (self-tap)
    m = m - cyl_z(3.3, -top - 1, -top + 15, 0, 0, 32)              # M6 stub axle on the idle side
    return m


def belt_path(c_dist, n_links):
    """Pin positions (u, w) for the assembly preview: links seated on both
    sprockets, straight top run, any half-pitch left over taken up as return-run sag."""
    deg = math.radians
    pins = []
    nt = int(c_dist // PITCH + 1e-9)
    half = (c_dist / PITCH - nt) > 0.25
    for i in range(nt + 1):
        pins.append((i * PITCH, R_PIN))
    head = [67.5, 22.5, -22.5, -67.5, -112.5] if half else [45.0, 0.0, -45.0, -90.0]
    for a in head:
        pins.append((c_dist + R_PIN * math.cos(deg(a)), R_PIN * math.sin(deg(a))))
    u_h, w_h = pins[-1]
    nb = int(round(u_h / PITCH))
    for k in range(1, nb):
        t = k / nb
        pins.append((u_h * (1 - t), w_h + (-R_PIN - w_h) * t))
    for a in (-90.0, -135.0, 180.0, 135.0):
        pins.append((R_PIN * math.cos(deg(a)), R_PIN * math.sin(deg(a))))
    assert len(pins) == n_links, (len(pins), n_links)
    return [(pins[i], pins[(i + 1) % n_links]) for i in range(n_links)]
