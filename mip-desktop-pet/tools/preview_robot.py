"""Render preview images of the generated robot OBJ from several angles."""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

HERE = os.path.dirname(__file__)
OBJ = os.path.abspath(os.path.join(HERE, "..", "models", "robot.obj"))
OUT = os.path.abspath(os.path.join(HERE, "..", "models", "robot_preview.png"))

# colors per part name (approximate the reference)
COLORS = {
    "face_screen": "#15171c",
    "eye_left": "#7fe8ef",
    "eye_right": "#7fe8ef",
    "side_button": "#e9e9ec",
}
DEFAULT = "#f3f3f5"


def load_obj(path):
    objects = []  # (name, verts, faces)
    name = "default"
    verts = []
    faces = []
    base = 0
    all_v = []

    def flush():
        nonlocal verts, faces
        if faces:
            objects.append((name, np.array(all_v), list(faces)))
        verts = []
        faces = []

    with open(path) as f:
        for line in f:
            if line.startswith("o "):
                name = line[2:].strip()
            elif line.startswith("v "):
                _, x, y, z = line.split()
                all_v.append((float(x), float(y), float(z)))
            elif line.startswith("f "):
                idx = [int(p.split("/")[0]) - 1 for p in line.split()[1:]]
                faces.append(idx)
    # group faces back per object by re-parsing with object boundaries
    return all_v


def load_grouped(path):
    all_v = []
    groups = []  # (name, [face idx tuples])
    cur = None
    with open(path) as f:
        for line in f:
            if line.startswith("o "):
                cur = (line[2:].strip(), [])
                groups.append(cur)
            elif line.startswith("v "):
                _, x, y, z = line.split()
                all_v.append((float(x), float(y), float(z)))
            elif line.startswith("f "):
                idx = [int(p.split("/")[0]) - 1 for p in line.split()[1:]]
                if cur is None:
                    cur = ("default", [])
                    groups.append(cur)
                cur[1].append(idx)
    return np.array(all_v), groups


def render(V, groups, elev, azim, ax):
    for name, faces in groups:
        polys = [V[f] for f in faces]
        color = COLORS.get(name, DEFAULT)
        col = Poly3DCollection(polys, facecolor=color, edgecolor="none",
                               linewidths=0, alpha=1.0)
        col.set_zsort("average")
        ax.add_collection3d(col)
    mn = V.min(axis=0)
    mx = V.max(axis=0)
    c = (mn + mx) / 2
    r = (mx - mn).max() / 2 * 1.05
    ax.set_xlim(c[0] - r, c[0] + r)
    ax.set_ylim(c[2] - r, c[2] + r)  # note: we map z->depth
    ax.set_zlim(c[1] - r, c[1] + r)
    ax.set_box_aspect((1, 1, 1))
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()


def main():
    V, groups = load_grouped(OBJ)
    # remap axes so Y is up in matplotlib's Z
    Vp = V[:, [0, 2, 1]]
    views = [("front", 12, -90), ("3/4", 18, -55),
             ("side", 8, 0), ("back", 12, 90)]
    fig = plt.figure(figsize=(12, 12), facecolor="#d9d9dc")
    for i, (title, elev, azim) in enumerate(views):
        ax = fig.add_subplot(2, 2, i + 1, projection="3d")
        ax.set_facecolor("#d9d9dc")
        render(Vp, groups, elev, azim, ax)
        ax.set_title(title, fontsize=14)
    fig.tight_layout()
    fig.savefig(OUT, dpi=80, facecolor="#d9d9dc")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
