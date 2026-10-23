"""Renders preview images and an assembled STL of the boat."""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import trimesh
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

import generate as g

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def assembly():
    hull = g.make_hull()
    lid = g.make_lid().translate([0, 0, g.HULL_H - 3])
    wheel = g.make_wheel()
    hub_y = g.HALF_W + 0.5
    wheels = []
    for sx in (1, -1):
        port = wheel.rotate([90, 0, 0]).translate([sx * g.AXLE_X, hub_y + g.WHEEL_W, g.SHAFT_Z])
        wheels += [port, port.mirror([0, 1, 0])]
    return hull, lid, wheels


def draw(ax, m, color, alpha=1.0):
    mesh = m.to_mesh()
    v = np.asarray(mesh.vert_properties)[:, :3]
    f = np.asarray(mesh.tri_verts)
    tris = v[f]
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-9
    light = np.clip(n @ np.array([0.4, 0.3, 0.85]), 0, 1) * 0.65 + 0.35
    base = np.array(matplotlib.colors.to_rgb(color))
    pc = Poly3DCollection(tris, facecolors=np.clip(base * light[:, None], 0, 1),
                          edgecolor="none", alpha=alpha)
    ax.add_collection3d(pc)


def view(parts, path, elev, azim, title, waterline=None):
    fig = plt.figure(figsize=(9, 6.5), dpi=130)
    ax = fig.add_subplot(111, projection="3d")
    for m, c in parts:
        draw(ax, m, c)
    if waterline is not None:
        xx, yy = np.meshgrid([-170, 170], [-150, 150])
        ax.plot_surface(xx, yy, np.full_like(xx, waterline, dtype=float), color="#3a8fd6", alpha=0.25)
    ax.set_xlim(-140, 140); ax.set_ylim(-140, 140); ax.set_zlim(-60, 100)
    ax.set_box_aspect((280, 280, 160))
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def main():
    out = os.path.join(ROOT, "renders")
    os.makedirs(out, exist_ok=True)
    hull, lid, wheels = assembly()
    parts = [(hull, "#f2a33a"), (lid, "#e0e0e0")] + [(w, "#333333") for w in wheels]
    view(parts, os.path.join(out, "assembly_iso.png"), 25, -60, "Assembled boat (lid on)")
    view([(hull, "#f2a33a")] + [(w, "#333333") for w in wheels],
         os.path.join(out, "assembly_top.png"), 70, -90, "Top view, lid off: tub + 4 motor pockets")
    view(parts, os.path.join(out, "afloat_side.png"), 5, -90, "Afloat at ~25 mm draft (800 g)",
         waterline=25)
    view([(g.make_wheel(), "#333333")], os.path.join(out, "paddle_wheel.png"), 35, -50, "Paddle wheel")

    allm = hull + lid
    for w in wheels:
        allm = allm + w
    mesh = allm.to_mesh()
    trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts)).export(
        os.path.join(ROOT, "stl", "assembly_preview_DO_NOT_PRINT.stl"))


if __name__ == "__main__":
    main()
