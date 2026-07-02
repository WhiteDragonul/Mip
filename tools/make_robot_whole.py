"""
MIP robot -- single fused model (all parts united into ONE watertight solid).

This is the "all-in-one" version: a static pose, printable in one piece (or as
a display model). It reuses the same proportions as the multi-part build but
overlaps the shapes at the joints and unions them, so the result is a single
connected body -- not separate pieces.

The face is still left open (display window), and the body/head stay hollow so
it can still house electronics if you want. Output: models/robot_whole.stl
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

import make_robot_parts as P
from make_robot_parts import (squircle, box, cyl, sphere, U, D, capsule_y,
                              WALL, HIP_X, SHO_X, SHO_Y, HIP_Y, NECK_Y, ANKLE_Y)


def build_whole(hollow=True):
    cy_body = 103.0
    rx, ry, rz = 38.0, 47.0, 34.0
    body = squircle(rx, ry, rz, 0.72, 0.85, (0, cy_body, 0))

    # HEAD (wide), overlapping the body neck so they fuse
    hcx, hcy = 0.0, 173.0
    hrx, hry, hrz = 40.0, 28.0, 25.0
    head = squircle(hrx, hry, hrz, 0.5, 0.5, (hcx, hcy, 0))
    neck = cyl(11, 30, (0, (hcy - hry + NECK_Y) / 2, 0), axis="y")  # bridge to body

    # ARMS overlapping the shoulders
    arms = []
    for s in (-1, 1):
        ax = s * (SHO_X + 12)
        arm = capsule_y(6.5, 30, (ax, SHO_Y - 6, 0))
        bridge = cyl(5.0, 30, (s * (SHO_X - 4), SHO_Y, 0), axis="x")  # fuse to body
        arms += [arm, bridge]

    # LEGS overlapping the hips, straight
    legs = []
    for s in (-1, 1):
        lx = s * HIP_X
        leg = capsule_y(7.5, (HIP_Y - ANKLE_Y) + 8, (lx, (HIP_Y + ANKLE_Y) / 2, 0))
        legs.append(leg)

    # FEET + HEELS fused
    feet = []
    for s in (-1, 1):
        fx = s * HIP_X
        foot = P.ellipsoid(11, 7.5, 17, (fx, 7.5, 4))
        foot = D(foot, box(40, 10, 60, (fx, 7.5 - 12, 4)))   # flat sole
        heel = P.ellipsoid(10, 7.5, 9, (fx, 7.0, -14))
        heel = D(heel, box(40, 10, 60, (fx, 7.0 - 12, 0)))
        feet += [foot, heel]

    solid = U([body, head, neck] + arms + legs + feet)

    # carve the display window in the face
    window = box(54, 40, 30, (hcx, hcy, hrz + 6))
    recess = box(72.5, 45, 8, (hcx, hcy, hrz - 1.0))
    solid = D(solid, recess)
    solid = D(solid, window)

    if hollow:
        # hollow head + body so it isn't a heavy brick (open at the neck/face)
        inner_body = squircle(rx - WALL, ry - WALL, rz - WALL, 0.72, 0.85, (0, cy_body, 0))
        inner_head = squircle(hrx - WALL, hry - WALL, hrz - WALL, 0.5, 0.5, (hcx, hcy, 0))
        cavity = U([inner_body, inner_head])
        solid = D(solid, cavity)

    return solid


def main():
    out = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "models"))
    os.makedirs(out, exist_ok=True)
    m = build_whole(hollow=True)
    path = os.path.join(out, "robot_whole.stl")
    m.export(path)
    print(f"watertight={m.is_watertight}  bodies={m.body_count}  "
          f"tris={len(m.faces)}  vol={m.volume/1000:.1f}cm3")
    print("wrote", path)
    # also an OBJ for easy viewing
    m.export(os.path.join(out, "robot_whole.obj"))


if __name__ == "__main__":
    main()
