"""
MIP desktop-pet robot -- multi-part, assemblable, 3D-printable body.

Generates one watertight STL per part into models/parts/. Parts connect with
"mos-baba" (male/female) snap joints:
  - shoulders : ball-and-socket (free movement, snaps in, pull hard to remove)
  - ankles    : ball-and-socket
  - heels     : pin hinge (foot splits into foot + heel + a pin)
  - neck/hips : keyed snap-peg (anti-rotation flat + retaining barb)

The face is left OPEN (a front window + an internal seating ledge) because the
whole face is a 2.4" OLED/IPS module (70.5 x 43.3 mm). A thin `face_bezel`
clips on the front to retain the screen. The head shell itself is seamless --
no mid-line -- the only opening is the front window and the bottom neck.

The body is hollow + elongated to fit a Raspberry Pi 3/4 (85x56) + fan +
battery, opened via a snap-on back panel (seam hidden at the back).

Units: millimetres. Overall height ~200 mm standing straight.
Requires: trimesh, manifold3d, numpy, scipy.
"""

import math
import os
import numpy as np
import trimesh
from trimesh import creation, transformations as tf

# ------------------------------------------------------------------ clearances
# Tune these for YOUR printer if joints are too tight/loose (typical FDM 0.3-0.4)
CLR_BALL = 0.35     # gap around ball inside socket
CLR_PEG = 0.30      # gap around snap pegs
CLR_HINGE = 0.40    # gap around hinge pin
WALL = 2.8          # shell wall thickness
SECT = 64           # cylinder/sphere tessellation


# ----------------------------------------------------------------- primitives
def _u(points):
    return np.unique(np.round(np.asarray(points, dtype=float), 5), axis=0)


def squircle(rx, ry, rz, e1, e2, center=(0, 0, 0), s=72, r=44):
    """Watertight superquadric solid via convex hull (all our shapes convex)."""
    pts = []
    for i in range(r + 1):
        v = -math.pi / 2 + math.pi * i / r
        cv, sv = math.cos(v), math.sin(v)
        for j in range(s):
            u = -math.pi + 2 * math.pi * j / s
            cu, su = math.cos(u), math.sin(u)
            x = rx * math.copysign(abs(cv) ** e1, cv) * math.copysign(abs(cu) ** e2, cu)
            y = ry * math.copysign(abs(sv) ** e1, sv)
            z = rz * math.copysign(abs(cv) ** e1, cv) * math.copysign(abs(su) ** e2, su)
            pts.append((x + center[0], y + center[1], z + center[2]))
    return trimesh.Trimesh(vertices=_u(pts)).convex_hull


def ellipsoid(rx, ry, rz, center=(0, 0, 0)):
    return squircle(rx, ry, rz, 1.0, 1.0, center)


def sphere(r, center=(0, 0, 0)):
    m = creation.icosphere(subdivisions=3, radius=r)
    m.apply_translation(center)
    return m


def box(sx, sy, sz, center=(0, 0, 0)):
    m = creation.box((sx, sy, sz))
    m.apply_translation(center)
    return m


def cyl(r, h, center=(0, 0, 0), axis="z"):
    m = creation.cylinder(radius=r, height=h, sections=SECT)
    if axis == "x":
        m.apply_transform(tf.rotation_matrix(math.pi / 2, [0, 1, 0]))
    elif axis == "y":
        m.apply_transform(tf.rotation_matrix(math.pi / 2, [1, 0, 0]))
    m.apply_translation(center)
    return m


def capsule_y(r, length, center=(0, 0, 0)):
    """Capsule along Y of total span `length` (cylinder + 2 hemispheres)."""
    h = max(length - 2 * r, 0.1)
    body = cyl(r, h, (0, 0, 0), axis="y")
    top = sphere(r, (0, h / 2, 0))
    bot = sphere(r, (0, -h / 2, 0))
    m = U([body, top, bot])
    m.apply_translation(center)
    return m


def rrect(w, h, t, r, center=(0, 0, 0), axis="z"):
    """Rounded-rectangle prism (thickness t along `axis`) via convex hull of 4
    corner cylinders. Used for the screen window / face frame (rounded corners)."""
    cyls = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            if axis == "z":
                c = (center[0] + sx * (w / 2 - r), center[1] + sy * (h / 2 - r), center[2])
            elif axis == "x":
                c = (center[0], center[1] + sx * (w / 2 - r), center[2] + sy * (h / 2 - r))
            else:  # y
                c = (center[0] + sx * (w / 2 - r), center[1], center[2] + sy * (h / 2 - r))
            cyls.append(cyl(r, t, c, axis=axis))
    return U(cyls).convex_hull


def U(meshes):
    return trimesh.boolean.union(meshes)


def D(a, b):
    return trimesh.boolean.difference([a, b])


# --------------------------------------------------------------------- joints
def male_ball(center, direction, ball_r=5.5, neck_r=3.2, neck_len=6.0):
    """Ball on a stalk. `direction` is a unit-ish axis the stalk points along
    (away from the parent part). Returns mesh to UNION onto the part."""
    d = np.array(direction, float)
    d = d / np.linalg.norm(d)
    base = np.array(center, float)
    ball_c = base + d * (neck_len + ball_r * 0.2)
    # stalk
    mid = base + d * (neck_len / 2)
    if abs(d[1]) > 0.9:
        ax = "y"
    elif abs(d[0]) > 0.9:
        ax = "x"
    else:
        ax = "z"
    stalk = cyl(neck_r, neck_len + ball_r, tuple(mid), axis=ax)
    return U([stalk, sphere(ball_r, tuple(ball_c))])


def socket(center, direction, ball_r=5.5, wall=2.4, slots=4):
    """Female ball-socket boss with a retaining mouth and flex slots ("zimti").
    Returns (boss_to_union, cut_to_subtract). `direction` points OUT of the
    opening (same side the ball comes from)."""
    d = np.array(direction, float)
    d = d / np.linalg.norm(d)
    c = np.array(center, float)
    cav_r = ball_r + CLR_BALL
    out_r = cav_r + wall
    mouth_r = ball_r - 0.7            # < ball_r so it snaps & retains
    # boss: a sphere shell centre pulled slightly back so opening faces +d
    boss = sphere(out_r, tuple(c - d * 1.0))
    cut_parts = [sphere(cav_r, tuple(c))]                       # inner cavity
    # mouth opening: cylinder from cavity outward through the wall
    if abs(d[1]) > 0.9:
        ax = "y"
    elif abs(d[0]) > 0.9:
        ax = "x"
    else:
        ax = "z"
    mouth_c = c + d * (out_r * 0.7)
    cut_parts.append(cyl(mouth_r, out_r * 1.8, tuple(mouth_c), axis=ax))
    # flex slots near the mouth rim
    for k in range(slots):
        ang = 2 * math.pi * k / slots
        # slot is a thin box radial to the opening; build along a perpendicular
        sl = box(out_r * 2.4, 0.9, out_r * 0.9)
        # orient slot plane perpendicular to d, rotate around d by ang
        R = tf.rotation_matrix(ang, d)
        sl.apply_transform(R)
        sl.apply_translation(tuple(c + d * (out_r * 0.55)))
        cut_parts.append(sl)
    return boss, U(cut_parts)


def snap_peg(center, direction, peg_r=6.0, length=12.0, barb=1.1):
    """Keyed male snap-peg (anti-rotation D-flat + retaining barb ring).
    Returns mesh to UNION onto the part. `direction` points away from part."""
    d = np.array(direction, float)
    d = d / np.linalg.norm(d)
    c = np.array(center, float)
    ax = "y" if abs(d[1]) > 0.9 else ("x" if abs(d[0]) > 0.9 else "z")
    mid = c + d * (length / 2)
    peg = cyl(peg_r, length, tuple(mid), axis=ax)
    # barb ring near the tip
    barb_c = c + d * (length - 2.2)
    ring = cyl(peg_r + barb, 1.8, tuple(barb_c), axis=ax)
    ring2 = cyl(peg_r + barb, 1.8, tuple(c + d * (length - 0.6)), axis=ax)  # taper helper
    peg = U([peg, ring])
    # D-flat: shave one side for anti-rotation
    flat = box(peg_r * 2, length * 1.4, peg_r * 2)
    # move flat so it cuts a chord on +X side (perpendicular to axis)
    if ax == "y":
        flat.apply_translation(tuple(c + np.array([peg_r + 0.0, length / 2, 0])))
    elif ax == "x":
        flat.apply_translation(tuple(c + np.array([length / 2, peg_r + 0.0, 0])))
    else:
        flat.apply_translation(tuple(c + np.array([peg_r + 0.0, 0, length / 2])))
    return D(peg, flat)


def snap_socket_cut(center, direction, peg_r=6.0, depth=12.0, barb=1.1):
    """Female cut for snap_peg: bore + barb groove + D-flat key. Returns the
    cut mesh to SUBTRACT from the part."""
    d = np.array(direction, float)
    d = d / np.linalg.norm(d)
    c = np.array(center, float)
    ax = "y" if abs(d[1]) > 0.9 else ("x" if abs(d[0]) > 0.9 else "z")
    hole_r = peg_r + CLR_PEG
    mid = c + d * (depth / 2)
    bore = cyl(hole_r, depth + 1, tuple(mid), axis=ax)
    groove = cyl(hole_r + barb + 0.1, 2.0, tuple(c + d * (depth - 2.2)), axis=ax)
    key = box(peg_r * 2, depth * 1.4, peg_r * 2)
    if ax == "y":
        key.apply_translation(tuple(c + np.array([peg_r + CLR_PEG, depth / 2, 0])))
    elif ax == "x":
        key.apply_translation(tuple(c + np.array([depth / 2, peg_r + CLR_PEG, 0])))
    else:
        key.apply_translation(tuple(c + np.array([peg_r + CLR_PEG, 0, depth / 2])))
    return U([bore, groove, key])


# ----------------------------------------------------- friction pin hinge
# A posable hinge: a central rotating "tongue" (knuckle) captured between two
# "fork" ears, held by a separate printed pin. Friction (it holds whatever pose
# you set) comes from (a) a snug bore where the tongue rides the pin and (b) the
# fork ears lightly pinching the tongue's sides.  Rotation axis is X (the robot's
# left-right axis) so legs swing fore/aft -> the bot can sit.
PIN_R = 2.0             # hinge pin radius (4 mm pin)
KN_R = 6.0              # knuckle / ear disc radius
KN_W = 7.0             # central tongue width (along the X pin axis)
EAR_W = 3.2            # each fork ear thickness
GAP_AX = 0.18          # axial friction gap between an ear face and the tongue
CLR_PIN_KN = 0.15      # tongue bore: rides the pin with light friction (holds pose)
CLR_PIN_EAR = 0.05     # ear bore: near press-fit so the pin stays put
JW = KN_W + 2 * GAP_AX + 2 * EAR_W      # total joint width along X
SWEEP = KN_R + 0.4                       # clearance radius for the tongue to rotate


def hinge_tongue(center):
    """Male rotating knuckle (a disc on the X axis with a pin bore). Returns
    (solid_to_union, bore_to_subtract)."""
    c = tuple(center)
    disc = cyl(KN_R, KN_W, c, axis="x")
    bore = cyl(PIN_R + CLR_PIN_KN, KN_W + 2, c, axis="x")
    return disc, bore


def hinge_fork(center):
    """Female fork: two ears straddling the tongue. Returns
    (ears_to_union, cuts_to_subtract). `cuts` bores the pin hole AND hollows a
    cylindrical pocket so the captured tongue can spin freely."""
    c = np.array(center, float)
    off = KN_W / 2 + GAP_AX + EAR_W / 2
    ears = U([cyl(KN_R, EAR_W, tuple(c + [s * off, 0, 0]), axis="x") for s in (-1, 1)])
    pocket = cyl(SWEEP, KN_W + 2 * GAP_AX, tuple(c), axis="x")   # room for the tongue
    pin = cyl(PIN_R + CLR_PIN_EAR, JW + 2, tuple(c), axis="x")   # pin hole thru both ears
    return ears, U([pocket, pin])


def build_hinge_pin():
    """The separate friction pin (print 4: two hips + two knees). A plain rod
    with a tiny grip head so it can be pushed in flush and pulled back out."""
    rod = cyl(PIN_R, JW - 0.2, (0, 0, 0), axis="x")
    head = cyl(PIN_R + 1.2, 1.6, (JW / 2 - 0.8, 0, 0), axis="x")
    return U([rod, head])


# ----------------------------------------------------------------- the parts
# global layout (mm), y up, origin on the ground between the feet.
# Proportions follow the WHITE reference robot (rounded-cube head, egg body,
# stubby arms, thin legs + oval shoes). No bow.
HIP_X = 13.0
SHO_Y = 116.0
SHO_X = 33.0
HIP_Y = 56.0
NECK_Y = 140.0
ANKLE_Y = 16.0
HIP_PIN_Y = 53.0        # hip hinge axis (just under the belly)
KNEE_PIN_Y = 36.0       # knee hinge axis

HEAD_C = (0.0, 172.0)
HEAD_R = (39.0, 31.0, 31.0)     # rounded cube: 78 x 62 x 62
BODY_C = 96.0
BODY_R = (37.0, 44.0, 35.0)     # egg: 74 x 88 x 70
BODY_E = (0.82, 0.92)
OPEN_W, OPEN_H = 50.0, 70.0     # back access opening (for the cover)


DISP_DY = HEAD_C[1] - 5      # display sits a bit low to leave room for the camera
CAM_Y = DISP_DY + 28         # camera hole centre (above the screen / bezel)


def build_head():
    cx, cy = HEAD_C
    rx, ry, rz = HEAD_R
    outer = squircle(rx, ry, rz, 0.5, 0.5, (cx, cy, 0))
    inner = squircle(rx - WALL, ry - WALL, rz - WALL, 0.5, 0.5, (cx, cy, 0))
    shell = D(outer, inner)
    # two small round ears, symmetric on BOTH sides (printed with the head).
    # start inside the wall so they fuse solidly, protrude ~3 mm outward.
    for s in (-1, 1):
        ear = cyl(5.5, 9.0, (s * (rx - 1.0), cy, 2), axis="x")
        shell = U([shell, ear])
    # neck: a solid collar bridges the rounded head bottom to the snap peg so it
    # connects solidly, then the peg goes down into the body; bore = cable channel
    shell = U([shell, cyl(9.0, 12, (cx, cy - ry + 5, 0), axis="y")])      # collar
    shell = U([shell, snap_peg((cx, cy - ry, 0), (0, -1, 0),
                               peg_r=8.5, length=12, barb=1.0)])
    shell = D(shell, cyl(5.0, 44, (cx, cy - ry - 2, 0), axis="y"))         # cable bore
    # display: rounded module-seat recess + rounded visible window (lowered)
    recess = rrect(72.5, 45, 9, 7, (cx, DISP_DY, rz - 1.5), axis="z")
    window = rrect(52, 38, 30, 8, (cx, DISP_DY, rz + 6), axis="z")
    shell = D(shell, recess)
    shell = D(shell, window)
    # CAMERA hole above the display -- stays clear of the bezel so it isn't covered
    shell = D(shell, cyl(3.5, 30, (cx, CAM_Y, rz), axis="z"))
    return shell


def build_face_bezel():
    """Black rounded face panel (the screen surround) that clips on the front
    and retains the display. Sized/placed to NOT cover the camera hole above it."""
    cx, _ = HEAD_C
    cz = HEAD_R[2]
    outer = rrect(60, 44, 4.5, 9, (cx, DISP_DY, cz), axis="z")
    inner = rrect(52, 38, 12, 8, (cx, DISP_DY, cz), axis="z")
    frame = D(outer, inner)
    clip_l = box(2.0, 26, 6.0, (cx - 28.0, DISP_DY, cz - 3.3))
    clip_r = box(2.0, 26, 6.0, (cx + 28.0, DISP_DY, cz - 3.3))
    return U([frame, clip_l, clip_r])


def build_body():
    cy = BODY_C
    rx, ry, rz = BODY_R
    e1, e2 = BODY_E
    outer = squircle(rx, ry, rz, e1, e2, (0, cy, 0))
    inner = squircle(rx - WALL, ry - WALL, rz - WALL, e1, e2, (0, cy, 0))
    shell = D(outer, inner)

    cuts, bosses = [], []
    # NECK socket: head peg points DOWN into the body from y=141 (shared point)
    cuts.append(snap_socket_cut((0, 141, 0), (0, -1, 0),
                                peg_r=8.5, depth=12, barb=1.0))
    # HIP hinges: a fork hangs under the belly at each hip; the thigh tongue pins
    # into it and swings fore/aft (X axis). Symmetric -> holes line up with legs.
    for sx in (-HIP_X, HIP_X):
        ears, holes = hinge_fork((sx, HIP_PIN_Y, 0))
        # web ties the ears up into the belly shell so they're anchored solidly
        web = box(JW, 14, 11, (sx, HIP_PIN_Y + 6, 0))
        bosses.append(U([ears, web]))
        cuts.append(holes)          # pin hole + rotation pocket (kept clear of web)
    # SHOULDER ball-sockets (sides), receive the arm balls
    for sx in (-1, 1):
        b, c = socket((sx * SHO_X, SHO_Y, 0), (sx, 0.12, 0), ball_r=5.5)
        bosses.append(b)
        cuts.append(c)
    shell = U([shell] + bosses)
    shell = D(shell, U(cuts))
    # BACK access: clean rectangular window through the back wall (the cover is a
    # curved cap that fills it flush -- see build_back_panel)
    shell = D(shell, box(OPEN_W, OPEN_H, 80, (0, cy, -rz - 10)))
    return shell


def build_back_panel():
    """Flush curved door that fills the back opening exactly (follows the body
    curve), with snap clips + a speaker grille of holes."""
    cy = BODY_C
    rx, ry, rz = BODY_R
    e1, e2 = BODY_E
    shell = D(squircle(rx, ry, rz, e1, e2, (0, cy, 0)),
              squircle(rx - WALL, ry - WALL, rz - WALL, e1, e2, (0, cy, 0)))
    # cap = the same curved wall section, 0.3 mm smaller all round -> flush fit
    cap = trimesh.boolean.intersection(
        [shell, box(OPEN_W - 0.6, OPEN_H - 0.6, 80, (0, cy, -rz - 10))])
    zin = -(rz - WALL)               # inner surface of the back wall
    parts = [cap]
    # snap clips: a post inward + a small barb that hooks just behind the inner rim
    hw, hh = OPEN_W / 2, OPEN_H / 2
    for (dx, dy, ox, oy, wx, wy) in [
            (0,  hh - 2, 0,  2.2, 12, 3),   # top
            (0, -hh + 2, 0, -2.2, 12, 3),   # bottom
            (hw - 2,  0,  2.2, 0, 3, 12),   # right
            (-hw + 2, 0, -2.2, 0, 3, 12)]:  # left
        post = box(wx, wy, 7.0, (dx, cy + dy, zin + 3.0))
        barb = box(wx, wy, 1.6, (dx + ox, cy + dy + oy, zin + 0.6))
        parts += [post, barb]
    panel = U(parts)
    # SPEAKER grille: concentric rings of small holes through the cap (back)
    holes = []
    for (r, n) in [(0, 1), (6, 6), (11, 12)]:
        for k in range(max(n, 1)):
            a = 2 * math.pi * k / max(n, 1)
            holes.append(cyl(1.4, 24, (r * math.cos(a), cy + r * math.sin(a), -rz),
                             axis="z"))
    return D(panel, U(holes))


def build_arm(side):
    """Rounded arm hanging from a shoulder ball, ending just above the legs."""
    length = 52.0                       # a bit above where the legs start (hip y=56)
    arm = capsule_y(6.0, length, (side * 44, SHO_Y - length / 2, 0))
    ball = male_ball((side * 40, SHO_Y, 0), (-side, 0.0, 0), ball_r=5.5)
    return U([arm, ball])


def build_thigh(side):
    """Upper leg: hinge TONGUE up into the body hip-fork, hinge FORK down at the
    knee. Swings fore/aft on the hip pin so the bot can sit."""
    sx = side * HIP_X
    hip = (sx, HIP_PIN_Y, 0)
    knee = (sx, KNEE_PIN_Y, 0)
    # main blade spans the knee..just-under-hip; full joint width so it forms the
    # knee fork ears once we carve the centre out.
    shaft = rrect(JW, 16, 11, 4.0, (sx, 41.0, 0), axis="z")        # y 33..49
    tongue, tbore = hinge_tongue(hip)
    thigh = U([shaft, tongue])
    thigh = D(thigh, tbore)                                        # hip pin bore
    # KNEE fork carved out of the blade bottom: rotation pocket + open slot + pin
    thigh = D(thigh, cyl(SWEEP, KN_W + 2 * GAP_AX, knee, axis="x"))
    thigh = D(thigh, box(KN_W + 2 * GAP_AX, 30, 2 * SWEEP + 4,
                         (sx, KNEE_PIN_Y - 13, 0)))                 # opens downward
    thigh = D(thigh, cyl(PIN_R + CLR_PIN_EAR, JW + 2, knee, axis="x"))
    return thigh


def build_shin(side):
    """Lower leg: hinge TONGUE up into the thigh knee-fork, ball DOWN into the
    foot (ankle stays a ball so the foot can still tilt)."""
    sx = side * HIP_X
    knee = (sx, KNEE_PIN_Y, 0)
    shaft = capsule_y(6.0, KNEE_PIN_Y - ANKLE_Y + 4,
                      (sx, (KNEE_PIN_Y + ANKLE_Y) / 2, 0))         # y 14..38
    tongue, tbore = hinge_tongue(knee)
    ball = male_ball((sx, ANKLE_Y + 10, 0), (0, -1, 0), ball_r=5.0, neck_len=9.0)
    shin = U([shaft, tongue, ball])
    shin = D(shin, tbore)                                          # knee pin bore
    return shin


def build_foot(side):
    """Oval shoe with an ankle ball-socket on top (foot tilts on the ankle)."""
    sx = side * HIP_X
    foot = ellipsoid(10, 7.5, 16, (sx, 7.0, 5))
    foot = D(foot, box(44, 12, 60, (sx, 7.0 - 12.8, 5)))   # flat sole at y~0.6
    b, c = socket((sx, ANKLE_Y, 0), (0, 1, 0), ball_r=5.0)
    foot = U([foot, b])
    foot = D(foot, c)
    return foot


# --------------------------------------------------------------------- driver
PARTS = {
    "head": build_head,
    "face_bezel": build_face_bezel,
    "body": build_body,
    "back_panel": build_back_panel,
    "arm_left": lambda: build_arm(-1),
    "arm_right": lambda: build_arm(1),
    "thigh_left": lambda: build_thigh(-1),
    "thigh_right": lambda: build_thigh(1),
    "shin_left": lambda: build_shin(-1),
    "shin_right": lambda: build_shin(1),
    "foot_left": lambda: build_foot(-1),
    "foot_right": lambda: build_foot(1),
    "hinge_pin": build_hinge_pin,
}


def clean(m):
    """Drop tiny boolean slivers: keep the single largest solid component."""
    comps = m.split(only_watertight=False)
    if len(comps) <= 1:
        return m
    big = max(comps, key=lambda c: abs(c.volume))
    return big


def main():
    out = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "models", "parts"))
    os.makedirs(out, exist_ok=True)
    results = {}
    for name, fn in PARTS.items():
        try:
            m = clean(fn())
            wt = m.is_watertight
            single = m.body_count == 1
            m.export(os.path.join(out, name + ".stl"))
            results[name] = (wt and single, len(m.faces), round(m.volume / 1000, 1))
            print(f"  {name:12s} watertight={wt!s:5s} bodies={m.body_count} "
                  f"tris={len(m.faces):6d} vol={results[name][2]}cm3")
        except Exception as e:
            results[name] = ("ERROR", str(e)[:60], 0)
            print(f"  {name:12s} ERROR: {e}")
    bad = [k for k, v in results.items() if v[0] is not True]
    print("\nparts OK:", sum(1 for v in results.values() if v[0] is True), "/", len(PARTS))
    if bad:
        print("NEEDS ATTENTION:", bad)


if __name__ == "__main__":
    main()
