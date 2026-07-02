"""Render the assembled robot (and an exploded view) from the part STLs."""
import os, glob
import numpy as np
import trimesh
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

HERE = os.path.dirname(__file__)
PARTS = os.path.abspath(os.path.join(HERE, "..", "models", "parts"))
OUT = os.path.abspath(os.path.join(HERE, "..", "models", "parts_preview.png"))

COLOR = {
    "face_bezel": "#1b1d22",
    "back_panel": "#dfe2e6",
    "hinge_pin": "#9aa0a6",
}
DEFAULT = "#f1f1f3"


def collections(meshes, explode=0.0):
    cols = []
    for name, m in meshes:
        V = m.vertices[:, [0, 2, 1]].copy()   # Y up -> matplotlib Z
        if explode:
            c = m.vertices.mean(axis=0)
            off = np.array([c[0], c[2], (c[1] - 100)]) * explode * 0.012
            V += off
        tris = V[m.faces]
        pc = Poly3DCollection(tris, facecolor=COLOR.get(name, DEFAULT),
                              edgecolor="#c9c9cf", linewidths=0.05)
        cols.append((pc, V))
    return cols


def draw(ax, meshes, elev, azim, explode=0.0):
    allV = []
    for pc, V in collections(meshes, explode):
        ax.add_collection3d(pc)
        allV.append(V)
    allV = np.vstack(allV)
    mn, mx = allV.min(0), allV.max(0)
    c = (mn + mx) / 2
    r = (mx - mn).max() / 2 * 1.05
    ax.set_xlim(c[0]-r, c[0]+r); ax.set_ylim(c[1]-r, c[1]+r); ax.set_zlim(c[2]-r, c[2]+r)
    ax.set_box_aspect((1, 1, 1)); ax.view_init(elev=elev, azim=azim); ax.set_axis_off()


def main():
    meshes = []
    for f in sorted(glob.glob(os.path.join(PARTS, "*.stl"))):
        name = os.path.splitext(os.path.basename(f))[0]
        meshes.append((name, trimesh.load(f)))
    # draw the black face panel LAST so it isn't hidden by the head shell
    meshes.sort(key=lambda nm: nm[0] == "face_bezel")
    fig = plt.figure(figsize=(15, 11), facecolor="#d9d9dc")
    views = [("front", 8, 90), ("3/4", 16, 130), ("side", 6, 180),
             ("back", 8, -90), ("top", 80, 90), ("exploded 3/4", 16, 130)]
    for i, (title, e, a) in enumerate(views):
        ax = fig.add_subplot(2, 3, i+1, projection="3d")
        ax.set_facecolor("#d9d9dc")
        draw(ax, meshes, e, a, explode=8.0 if "exploded" in title else 0.0)
        ax.set_title(title, fontsize=13)
    fig.tight_layout()
    fig.savefig(OUT, dpi=85, facecolor="#d9d9dc")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
