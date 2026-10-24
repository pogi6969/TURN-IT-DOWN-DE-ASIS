"""Deck cutting template (5 mm PVC foam / Sintra board): DXF for CNC/laser shops
(knife-cut PVC by hand; do NOT laser-cut PVC) and a 1:1 SVG to print and trace.
Holes: deck screws into the pontoon tops and drive-motor wire holes. Mount
footprints are drawn as thin outlines; drill those holes through the part flanges."""
import math
import os

from common import *
import electronics as el

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "deck")

R_CORNER = 12.0


def outline():
    """Closed polyline (list of (x, y)) of the deck: rectangle with the C1 slot open at the bow."""
    x0, x1, y = -BOAT_L / 2, BOAT_L / 2, P_OUT
    pts = []
    def arc(cx, cy, a0, a1, n=8):
        for i in range(n + 1):
            a = math.radians(a0 + (a1 - a0) * i / n)
            pts.append((cx + R_CORNER * math.cos(a), cy + R_CORNER * math.sin(a)))
    arc(x0 + R_CORNER, -y + R_CORNER, 180, 270)
    arc(x1 - R_CORNER, -y + R_CORNER, 270, 360)
    pts += [(x1, -P_IN), (C1_OPEN_X, -P_IN), (C1_OPEN_X, P_IN), (x1, P_IN)]
    arc(x1 - R_CORNER, y - R_CORNER, 0, 90)
    arc(x0 + R_CORNER, y - R_CORNER, 90, 180)
    return pts


def holes():
    h = []
    for (sx0, sx1) in SEG_X:
        for hx in (sx0 + 20, sx1 - 20, (sx0 + sx1) / 2):
            for s in (-1, 1):
                for dy in (-30, 30):
                    h.append((hx, s * (P_CY + dy), 1.6))          # 3.2 mm clearance for M3 / #4 screws
    for s in (-1, 1):                                              # drive-motor wire holes over the pockets
        h.append((AXLE_X, s * (POCKET_Y0 + 8), 5.0))               # bow: inside the electronics/battery boxes
        h.append((-AXLE_X, s * (SORTER_OUT + 8), 5.0))            # stern: outboard of the sorter frames
    import collector
    for (bx, by) in collector.boom_hole_points():                   # guide-boom tabs
        for s in (-1, 1):
            h.append((bx, s * by, 1.6))
    return h


def footprints():
    rects = []
    (bx0, bx1), (by0, by1) = el.BOX_X, el.BOX_Y
    rects += [(bx0, by0, bx1, by1, "electronics box"), (bx0, -by1, bx1, -by0, "battery box")]
    rects += [(SORTER_X[0], WALL_Y, SORTER_X[1], SORTER_OUT, "sorter frame 1+3"),
              (SORTER_X[0], -SORTER_OUT, SORTER_X[1], -WALL_Y, "sorter frame 2+4")]
    return rects


def write_dxf(path):
    L = ["0", "SECTION", "2", "ENTITIES"]
    pts = outline()
    for (a, b) in zip(pts, pts[1:] + pts[:1]):
        L += ["0", "LINE", "8", "CUT", "10", f"{a[0]:.3f}", "20", f"{a[1]:.3f}", "11", f"{b[0]:.3f}", "21", f"{b[1]:.3f}"]
    for (x, y, r) in holes():
        L += ["0", "CIRCLE", "8", "DRILL", "10", f"{x:.3f}", "20", f"{y:.3f}", "40", f"{r:.3f}"]
    for (x0, y0, x1, y1, _) in footprints():
        for (a, b) in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
            L += ["0", "LINE", "8", "MARK", "10", f"{a[0]:.3f}", "20", f"{a[1]:.3f}", "11", f"{b[0]:.3f}", "21", f"{b[1]:.3f}"]
    L += ["0", "ENDSEC", "0", "EOF"]
    with open(path, "w") as f:
        f.write("\n".join(L) + "\n")


def write_svg(path):
    m = 10.0
    W, H = BOAT_L + 2 * m, 2 * P_OUT + 2 * m
    tx = lambda x: x + BOAT_L / 2 + m
    ty = lambda y: P_OUT - y + m                                   # port at the top of the sheet, bow to the right
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="{H}mm" viewBox="0 0 {W} {H}">',
         '<rect width="100%" height="100%" fill="white"/>']
    d = "M " + " L ".join(f"{tx(x):.2f},{ty(y):.2f}" for (x, y) in outline()) + " Z"
    s.append(f'<path d="{d}" fill="none" stroke="black" stroke-width="0.4"/>')
    for (x, y, r) in holes():
        s.append(f'<circle cx="{tx(x):.2f}" cy="{ty(y):.2f}" r="{r}" fill="none" stroke="red" stroke-width="0.3"/>')
        s.append(f'<path d="M {tx(x) - 2} {ty(y)} H {tx(x) + 2} M {tx(x)} {ty(y) - 2} V {ty(y) + 2}" stroke="red" stroke-width="0.2"/>')
    for (x0, y0, x1, y1, label) in footprints():
        s.append(f'<rect x="{tx(x0):.2f}" y="{ty(y1):.2f}" width="{x1 - x0:.2f}" height="{y1 - y0:.2f}" fill="none" stroke="#3366cc" stroke-width="0.25" stroke-dasharray="2 2"/>')
        s.append(f'<text x="{tx((x0 + x1) / 2):.2f}" y="{ty((y0 + y1) / 2):.2f}" font-size="6" text-anchor="middle" fill="#3366cc" font-family="sans-serif">{label}</text>')
    s.append(f'<text x="{tx(BOAT_L / 2) - 4:.2f}" y="{ty(0):.2f}" font-size="7" text-anchor="end" font-family="sans-serif">BOW</text>')
    s.append(f'<path d="M {m} {H - 4} H {m + 100}" stroke="black" stroke-width="0.6"/><text x="{m + 104}" y="{H - 2.5}" font-size="5" font-family="sans-serif">100 mm check bar: print at 100 %</text>')
    s.append('</svg>')
    with open(path, "w") as f:
        f.write("\n".join(s))


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    write_dxf(os.path.join(OUT, "deck_5mm_pvc.dxf"))
    write_svg(os.path.join(OUT, "deck_template_1to1.svg"))
    print(len(holes()), "holes;", "deck", BOAT_L, "x", 2 * P_OUT, "mm")
