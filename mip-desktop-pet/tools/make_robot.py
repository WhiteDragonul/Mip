"""
Generate a 3D model of the MIP desktop-pet robot (cute white companion).

Pure-Python, no external dependencies. Builds the body from primitives:
  - head        : superellipsoid (rounded "squircle" cube)
  - face screen : flat rounded panel inset on the front
  - eyes        : two rounded pads on the face
  - ear/button  : small disc on the left side of the head
  - body        : near-spherical squashed superellipsoid
  - arms        : two capsules
  - legs        : two capsules
  - feet        : two ellipsoid shoes

Exports:
  robot.obj  (with the parts grouped, so you can hide/recolor sides in any tool)
  robot.stl  (binary STL, ready for slicing / 3D printing)

Orientation: +X right, +Y up, +Z toward the viewer (front).
Units: millimetres. Overall height ~120 mm (rescale in your slicer as you like).
"""

import math
import struct
import os

# ----------------------------------------------------------------------------
# small vector helpers
# ----------------------------------------------------------------------------

def add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])

def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])

def scale(a, s):
    return (a[0] * s, a[1] * s, a[2] * s)

def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])

def norm(a):
    m = math.sqrt(a[0] ** 2 + a[1] ** 2 + a[2] ** 2) or 1.0
    return (a[0] / m, a[1] / m, a[2] / m)


# ----------------------------------------------------------------------------
# A "part" is just (vertices, faces). Faces are 0-based triangles.
# ----------------------------------------------------------------------------

def _sign_pow(c, e):
    """Signed power used for superquadrics."""
    return math.copysign(abs(c) ** e, c)


def superellipsoid(rx, ry, rz, e1, e2, center, segs=48, rings=24):
    """Superquadric ellipsoid. e1/e2 ~0.2 => boxy, =1 => sphere."""
    verts = []
    for i in range(rings + 1):
        v = -math.pi / 2 + math.pi * i / rings
        cv, sv = math.cos(v), math.sin(v)
        for j in range(segs):
            u = -math.pi + 2 * math.pi * j / segs
            cu, su = math.cos(u), math.sin(u)
            x = rx * _sign_pow(cv, e1) * _sign_pow(cu, e2)
            y = ry * _sign_pow(sv, e1)
            z = rz * _sign_pow(cv, e1) * _sign_pow(su, e2)
            verts.append(add((x, y, z), center))
    faces = []
    for i in range(rings):
        for j in range(segs):
            a = i * segs + j
            b = i * segs + (j + 1) % segs
            c = (i + 1) * segs + j
            d = (i + 1) * segs + (j + 1) % segs
            faces.append((a, c, d))
            faces.append((a, d, b))
    return verts, faces


def ellipsoid(rx, ry, rz, center, segs=40, rings=24):
    return superellipsoid(rx, ry, rz, 1.0, 1.0, center, segs, rings)


def capsule(radius, length, center, axis="y", segs=24, rings=12):
    """Capsule (cylinder + 2 hemispheres) of total span 'length' along axis."""
    half = max(length / 2 - radius, 0.0)
    verts = []
    # build along +Y then rotate
    for i in range(rings + 1):
        v = -math.pi / 2 + math.pi * i / rings
        cv, sv = math.cos(v), math.sin(v)
        yoff = half if sv >= 0 else -half
        for j in range(segs):
            u = 2 * math.pi * j / segs
            x = radius * cv * math.cos(u)
            y = radius * sv + yoff
            z = radius * cv * math.sin(u)
            verts.append((x, y, z))
    faces = []
    for i in range(rings):
        for j in range(segs):
            a = i * segs + j
            b = i * segs + (j + 1) % segs
            c = (i + 1) * segs + j
            d = (i + 1) * segs + (j + 1) % segs
            faces.append((a, c, d))
            faces.append((a, d, b))

    def rot(p):
        x, y, z = p
        if axis == "y":
            return (x, y, z)
        if axis == "x":
            return (y, x, z)
        if axis == "z":
            return (x, z, y)
        return p

    verts = [add(rot(p), center) for p in verts]
    return verts, faces


def rounded_panel(w, h, t, corner, center, segs=8):
    """A flat rounded rectangle slab (for the face screen). Lies in XY plane,
    thickness along Z. Built as an extruded squircle outline."""
    # outline points (squircle via superellipse)
    n = 4 * segs
    outline = []
    for k in range(n):
        a = 2 * math.pi * k / n
        ca, sa = math.cos(a), math.sin(a)
        x = (w / 2) * _sign_pow(ca, 0.35)
        y = (h / 2) * _sign_pow(sa, 0.35)
        outline.append((x, y))
    verts = []
    for (x, y) in outline:
        verts.append(add((x, y, t / 2), center))   # front ring
    for (x, y) in outline:
        verts.append(add((x, y, -t / 2), center))  # back ring
    fc = len(verts)
    verts.append(add((0, 0, t / 2), center))        # front center
    bc = len(verts)
    verts.append(add((0, 0, -t / 2), center))       # back center
    faces = []
    for k in range(n):
        k2 = (k + 1) % n
        faces.append((fc, k, k2))                    # front cap
        faces.append((bc, n + k2, n + k))            # back cap
        faces.append((k, n + k, n + k2))             # side
        faces.append((k, n + k2, k2))
    return verts, faces


# ----------------------------------------------------------------------------
# assemble the robot
# ----------------------------------------------------------------------------

def build_robot():
    parts = []  # list of (name, verts, faces)

    # ---- BODY: round, slightly squashed, sits low ----
    parts.append(("body",
                  *superellipsoid(rx=33, ry=30, rz=31, e1=1.0, e2=1.0,
                                  center=(0, 38, 0), segs=56, rings=32)))

    # ---- HEAD: boxy-rounded squircle cube ----
    head_c = (0, 90, 0)
    parts.append(("head",
                  *superellipsoid(rx=30, ry=26, rz=27, e1=0.45, e2=0.45,
                                  center=head_c, segs=56, rings=32)))

    # ---- FACE SCREEN: dark rounded panel inset on the front (+Z) ----
    parts.append(("face_screen",
                  *rounded_panel(w=40, h=30, t=3.0, corner=8,
                                 center=(0, 92, 26.5))))

    # ---- EYES: two rounded pads sitting on the screen ----
    parts.append(("eye_left",
                  *superellipsoid(rx=4.5, ry=7, rz=2.2, e1=0.5, e2=0.5,
                                  center=(-8, 92, 28.2), segs=28, rings=16)))
    parts.append(("eye_right",
                  *superellipsoid(rx=4.5, ry=7, rz=2.2, e1=0.5, e2=0.5,
                                  center=(8, 92, 28.2), segs=28, rings=16)))

    # ---- SIDE BUTTON / EAR on the left of the head (-X) ----
    parts.append(("side_button",
                  *ellipsoid(rx=2.5, ry=6, rz=6, center=(-30, 90, 0),
                             segs=28, rings=16)))

    # ---- ARMS: two capsules angled outward/up ----
    # left arm (waving up)
    la, lf = capsule(radius=5.5, length=34, center=(0, 0, 0), axis="y",
                     segs=24, rings=14)
    la = _rotate_z(la, math.radians(55))
    la = [add(p, (-30, 64, 0)) for p in la]
    parts.append(("arm_left", la, lf))
    # right arm (out to the side)
    ra, rf = capsule(radius=5.5, length=34, center=(0, 0, 0), axis="y",
                     segs=24, rings=14)
    ra = _rotate_z(ra, math.radians(-70))
    ra = [add(p, (30, 60, 0)) for p in ra]
    parts.append(("arm_right", ra, rf))

    # ---- LEGS: two capsules under the body ----
    parts.append(("leg_left",
                  *capsule(radius=6, length=30, center=(-11, 14, 2), axis="y",
                           segs=24, rings=14)))
    # right leg lifted / bent (mid-step)
    rl, rlf = capsule(radius=6, length=28, center=(0, 0, 0), axis="y",
                      segs=24, rings=14)
    rl = _rotate_z(rl, math.radians(-35))
    rl = [add(p, (14, 18, 6)) for p in rl]
    parts.append(("leg_right", rl, rlf))

    # ---- FEET: ellipsoid shoes ----
    parts.append(("foot_left",
                  *ellipsoid(rx=9, ry=5.5, rz=13, center=(-12, 1.5, 4),
                             segs=32, rings=20)))
    parts.append(("foot_right",
                  *ellipsoid(rx=9, ry=5.5, rz=13, center=(26, 16, 16),
                             segs=32, rings=20)))

    return parts


def _rotate_z(verts, ang):
    c, s = math.cos(ang), math.sin(ang)
    return [(x * c - y * s, x * s + y * c, z) for (x, y, z) in verts]


# ----------------------------------------------------------------------------
# exporters
# ----------------------------------------------------------------------------

def write_obj(path, parts):
    with open(path, "w") as f:
        f.write("# MIP desktop-pet robot\n")
        offset = 0
        for name, verts, faces in parts:
            f.write(f"o {name}\n")
            f.write(f"g {name}\n")
            for v in verts:
                f.write(f"v {v[0]:.4f} {v[1]:.4f} {v[2]:.4f}\n")
            for tri in faces:
                a, b, c = tri[0] + 1 + offset, tri[1] + 1 + offset, tri[2] + 1 + offset
                f.write(f"f {a} {b} {c}\n")
            offset += len(verts)


def write_stl_binary(path, parts):
    tris = []
    for _, verts, faces in parts:
        for tri in faces:
            p0, p1, p2 = verts[tri[0]], verts[tri[1]], verts[tri[2]]
            n = norm(cross(sub(p1, p0), sub(p2, p0)))
            tris.append((n, p0, p1, p2))
    with open(path, "wb") as f:
        f.write(b"\0" * 80)
        f.write(struct.pack("<I", len(tris)))
        for n, a, b, c in tris:
            f.write(struct.pack("<3f", *n))
            f.write(struct.pack("<3f", *a))
            f.write(struct.pack("<3f", *b))
            f.write(struct.pack("<3f", *c))
            f.write(struct.pack("<H", 0))


def main():
    out_dir = os.path.join(os.path.dirname(__file__), "..", "models")
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    parts = build_robot()
    obj = os.path.join(out_dir, "robot.obj")
    stl = os.path.join(out_dir, "robot.stl")
    write_obj(obj, parts)
    write_stl_binary(stl, parts)

    nv = sum(len(v) for _, v, _ in parts)
    nf = sum(len(fc) for _, _, fc in parts)
    print(f"parts: {len(parts)}  vertices: {nv}  triangles: {nf}")
    print("wrote:", obj)
    print("wrote:", stl)


if __name__ == "__main__":
    main()
