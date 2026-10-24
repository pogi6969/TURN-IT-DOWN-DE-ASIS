"""Interference check over the whole assembly: prints every pair of parts whose
solids overlap by more than 1 mm^3."""
import itertools
import sys

import assembly
from common import *


def main():
    P = assembly.parts(open_flap="--closed" not in sys.argv)
    boxes = [(n, m, m.bounding_box()) for (n, m, c, pr) in P]
    hits = []
    for (na, ma, ba), (nb, mb, bb) in itertools.combinations(boxes, 2):
        if any(ba[i] > bb[i + 3] or bb[i] > ba[i + 3] for i in range(3)):
            continue
        v = (ma ^ mb).volume()
        if v > 1.0:
            hits.append((v, na, nb))
    for v, a, b in sorted(hits, reverse=True):
        print(f"{v:10.1f} mm3  {a}  x  {b}")
    print(f"{len(hits)} overlapping pairs out of {len(P)} parts")
    ground = SHAFT_Z - WHEEL_R
    low = sorted((m.bounding_box()[2], n) for (n, m, c, pr) in P if not n.startswith("wheel"))[:3]
    print(f"ground (wheels) at z = {ground:.1f}; lowest other parts: " + ", ".join(f"{n} {z:.1f}" for z, n in low))
    # open flap: tip gap to the far belt edge
    f = [m for (n, m, c, pr) in P if n == "flap_bin1"][0]
    print(f"open flap reaches y = {f.bounding_box()[1]:.1f} (far belt edge -{BELT_W / 2:.0f}, far closed flap face -{WALL_Y:.0f})")


if __name__ == "__main__":
    main()
