"""Exports every printed part in its print orientation, checks bed fit,
estimates mass and draft, and writes a coloured GLB of the assembly.

    pip install manifold3d trimesh numpy
    python build.py
"""
import json
import math
import os

import numpy as np
import trimesh

from common import *
import assembly
import belt
import electronics as el
import frames as fr
import hull
import sorter as so

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
STL = os.path.join(ROOT, "stl")
BED = (220.0, 220.0, 250.0)


def _swap(rows):
    return matrix(np.array(rows, float), [0, 0, 0])


# name: (part, qty, note). Parts are oriented for printing here.
def print_parts():
    up = lambda m, u0: m.transform(_swap([[0, 1, 0], [0, 0, 1], [-1, 0, 0]])).translate([0, 0, u0])
    P = {
        "pontoon_bow_port": (hull.pontoon_segment("bow"), 1, ""),
        "pontoon_bow_stbd": (mirror_y(hull.pontoon_segment("bow")), 1, ""),
        "pontoon_mid": (hull.pontoon_segment("mid"), 4, "two per side"),
        "pontoon_stern_port": (hull.pontoon_segment("stern"), 1, ""),
        "pontoon_stern_stbd": (mirror_y(hull.pontoon_segment("stern")), 1, ""),
        "dowel": (hull.dowel(), 8, ""),
        "motor_saddle": (hull.motor_saddle().rotate([180, 0, 0]), 4, ""),
        "paddle_wheel": (hull.paddle_wheel(), 4, ""),
        "belt_link": (belt.belt_link(False).rotate([90, 0, 0]), LINKS_C1 - LINKS_C1 // CLEAT_EVERY + LINKS_C2, "print on edge"),
        "belt_link_cleat": (belt.belt_link(True).rotate([90, 0, 0]), LINKS_C1 // CLEAT_EVERY, "print on edge"),
        "drum_drive": (belt.drum(True), 2, ""),
        "drum_idler": (belt.drum(False), 2, ""),
        "c1_frame_lower": (fr.c1_lower().transform(_swap([[0, 1, 0], [0, 0, 1], [-1, 0, 0]])), 1, "splice end on the bed"),
        "c1_frame_upper": (fr.c1_upper().transform(_swap([[0, 1, 0], [0, 0, 1], [1, 0, 0]])), 1, "splice end on the bed"),
        "c1_splice": (fr.c1_splice().transform(_swap([[1, 0, 0], [0, 0, 1], [0, 1, 0]])), 2, ""),
        "c1_leg_port": (fr.c1_leg().rotate([90, 0, 0]), 1, ""),
        "c1_leg_stbd": (mirror_y(fr.c1_leg()).rotate([-90, 0, 0]), 1, ""),
        "c2_front_frame": (fr.c2_front().transform(_swap([[0, 1, 0], [0, 0, 1], [1, 0, 0]])), 1, "tail end on the bed"),
        "c2_bed_beam_front": (fr.c2_beam_piece(0).transform(_swap([[1, 0, 0], [0, 1, 0], [0, 0, -1]])), 1, "bed face down"),
        "c2_bed_beam_rear": (fr.c2_beam_piece(1).transform(_swap([[1, 0, 0], [0, 1, 0], [0, 0, -1]])), 1, "bed face down"),
        "c2_head_stand_drive": (fr.c2_head_stand(True).transform(_swap([[1, 0, 0], [0, 0, 1], [0, 1, 0]])), 1, "port"),
        "c2_head_stand_idler": (mirror_y(fr.c2_head_stand(False)).transform(_swap([[1, 0, 0], [0, 0, 1], [0, -1, 0]])), 1, "starboard"),
        "sorter_frame_front_port": (so.piece(so.sorter_frame(), 0), 1, "bin 1"),
        "sorter_frame_front_stbd": (mirror_y(so.piece(so.sorter_frame(), 0)), 1, "bin 2"),
        "sorter_cover_front_port": (so.piece(so.sorter_cover(), 0), 1, "bin 1"),
        "sorter_cover_front_stbd": (mirror_y(so.piece(so.sorter_cover(), 0)), 1, "bin 2"),
        "sorter_frame_rear_port": (so.piece(so.sorter_frame(), 1), 1, "bin 3"),
        "sorter_frame_rear_stbd": (mirror_y(so.piece(so.sorter_frame(), 1)), 1, "bin 4"),
        "sorter_cover_rear_port": (so.piece(so.sorter_cover(), 1), 1, "bin 3"),
        "sorter_cover_rear_stbd": (mirror_y(so.piece(so.sorter_cover(), 1)), 1, "bin 4"),
        "servo_bridge": (so.servo_bridge(), 4, ""),
        "flap_port": (so.flap().rotate([90, 0, 0]), 2, "bins 1 + 3"),
        "flap_stbd": (mirror_y(so.flap()).rotate([-90, 0, 0]), 2, "bins 2 + 4"),
        "bucket": (so.bucket(), 4, "handle faces outboard"),
        "reject_tray": (so.reject_tray(), 1, ""),
        "electronics_box": (el.electronics_box(), 1, "port"),
        "battery_box": (mirror_y(el.battery_box()), 1, "starboard"),
        "box_lid": (el.box_lid().rotate([180, 0, 0]), 2, ""),
        "camera_mast": (el.camera_mast().transform(_swap([[1, 0, 0], [0, 0, 1], [0, -1, 0]])), 1, ""),
        "nav_cam_bracket": (el.nav_cam_bracket(), 1, ""),
    }
    return P


def to_tm(m):
    mesh = m.to_mesh()
    return trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts), process=True)


def print_grams(m, walls=1.2, infill=0.12):
    v = m.volume() / 1000.0
    shell = min(v, m.surface_area() / 100.0 * walls / 10.0)
    return (shell + infill * (v - shell)) * 1.24


def export():
    os.makedirs(STL, exist_ok=True)
    rows, total_g = [], 0.0
    for name, (m, qty, note) in print_parts().items():
        t = to_tm(m)
        b = t.bounds
        t.apply_translation([-(b[0][0] + b[1][0]) / 2, -(b[0][1] + b[1][1]) / 2, -b[0][2]])
        t.export(os.path.join(STL, name + ".stl"))
        ext = sorted(t.extents[:2]) + [t.extents[2]]
        fits = ext[0] <= BED[0] and ext[1] <= BED[1] and ext[2] <= BED[2]
        g = print_grams(m, walls=0.8, infill=0.05 if name.startswith("pontoon") else 0.15)
        total_g += g * qty
        rows.append(dict(part=name, qty=qty, size=[round(e, 1) for e in t.extents], grams_each=round(g, 1),
                         watertight=bool(t.is_watertight), fits_bed=bool(fits), note=note))
        flag = "" if fits and t.is_watertight else "  <-- CHECK"
        print(f"{name:24s} x{qty:<3d} {t.extents[0]:6.1f} x {t.extents[1]:6.1f} x {t.extents[2]:6.1f}  {g:6.1f} g{flag}")
    print(f"filament total ~ {total_g / 1000:.2f} kg")
    return rows, total_g


BOUGHT_G = {"drive motors JGA25-370 x4": 4 * 95, "conveyor motors JGA25-370 x2": 2 * 95,
            "Raspberry Pi Zero 2 W + microSD": 15, "Pi camera + USB webcam": 20 + 60, "SG90 servos x4": 4 * 9,
            "PCA9685": 10, "L298N x2": 2 * 33, "LM2596 buck converters x2": 2 * 15, "3S1P 18650 pack + BMS": 160,
            "wiring, switch, fuse, IR sensor": 130, "M6 rod axles + nuts": 120, "1.75 mm PETG filament pins (71)": 71 * 0.3,
            "screws": 90, "LED strip": 10, "deck 5 mm PVC foam": 0}


def mass_and_draft(print_g):
    deck_area = (BOAT_L * 2 * P_OUT - (BOAT_L / 2 - C1_OPEN_X) * 2 * P_IN) / 100.0   # cm2
    BOUGHT_G["deck 5 mm PVC foam"] = deck_area * 0.5 * 0.55
    dry = print_g + sum(BOUGHT_G.values())
    pontoons = assembly.union([hull.pontoon_segment("stern"), hull.pontoon_segment("bow")]
                              + [hull.pontoon_segment("mid").translate([x0 - SEG_X[1][0], 0, 0]) for (x0, x1) in SEG_X[1:-1]])
    pontoons = pontoons + mirror_y(pontoons)

    def draft(mass_g):
        lo, hi = 0.0, P_H
        for _ in range(40):
            mid = (lo + hi) / 2
            v = (pontoons ^ box(-400, 400, -200, 200, -1, mid)).volume() / 1000.0
            lo, hi = (mid, hi) if v < mass_g else (lo, mid)
        return lo

    res = {"dry_mass_g": round(dry), "max_displacement_g": round(pontoons.volume() / 1000.0)}
    for label, extra in (("dry", 0), ("with 500 g trash", 500)):
        d = draft(dry + extra)
        res[f"draft_mm_{label}"] = round(d, 1)
    res["bought_parts_g"] = {k: round(v) for k, v in BOUGHT_G.items()}
    return res


def export_glb(path):
    scene = trimesh.Scene()
    for (name, m, col, printed) in assembly.parts():
        t = to_tm(m)
        rgb = trimesh.visual.color.hex_to_rgba(assembly.COL[col])
        mat = trimesh.visual.material.PBRMaterial(baseColorFactor=rgb, metallicFactor=0.0, roughnessFactor=0.7)
        t.visual = trimesh.visual.TextureVisuals(material=mat)
        scene.add_geometry(t, node_name=name, geom_name=name)
    scene.export(path)


if __name__ == "__main__":
    rows, g = export()
    res = mass_and_draft(g)
    print(json.dumps({k: v for k, v in res.items() if k != "bought_parts_g"}, indent=1))
    os.makedirs(os.path.join(ROOT, "renders"), exist_ok=True)
    with open(os.path.join(ROOT, "cad", "parts.json"), "w") as f:
        json.dump({"parts": rows, "filament_g": round(g), **res}, f, indent=1)
    export_glb(os.path.join(ROOT, "renders", "assembly.glb"))
    asm = assembly.union([m for (n, m, c, p) in assembly.parts()])
    to_tm(asm).export(os.path.join(STL, "assembly_preview_DO_NOT_PRINT.stl"))
