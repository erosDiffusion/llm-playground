# Blender Director - "Alley Corner" chase scene (v2/v3 minimal Workbench rules)
# Woman flees between buildings, turns left into a small street, is cornered
# in an open-front building by three men. 8 shots, 341 frames @ 24fps = 14.2s.
# Phases (CLI): -- build | -- test [frames] | -- anim
# Functions are also callable directly from the GUI via MCP exec().

import bpy, math, os, sys

FPS = 24
TOTAL = 341
PI = math.pi

OUT_DIR = "/home/oem/Apps/deepseek-workspace/generated/movies/2026-09-04/alley-corner"

# ---------------- colors (every object a different flat color) ----------------
COL = {
    "ground": (0.10, 0.10, 0.12),
    "W":  (1.00, 0.35, 0.05),   # woman - orange
    "M1": (0.05, 0.55, 0.15),   # man in front - green
    "M2": (0.45, 0.10, 0.80),   # follower A - purple
    "M3": (0.95, 0.85, 0.05),   # follower B - yellow
    "eyes": (0.02, 0.02, 0.02),
    "B_N1": (0.45, 0.45, 0.50), "B_N2": (0.55, 0.50, 0.45), "B_N3": (0.40, 0.48, 0.55),
    "B_S1": (0.50, 0.42, 0.42), "B_S2": (0.42, 0.50, 0.45), "B_S3": (0.52, 0.45, 0.52),
    "B_W":  (0.48, 0.48, 0.42), "B_E":  (0.40, 0.44, 0.40),
    "T_back": (0.60, 0.30, 0.25), "T_left": (0.35, 0.40, 0.55),
    "T_right": (0.55, 0.45, 0.30), "T_roof": (0.30, 0.30, 0.33),
    "C1": (0.00, 0.50, 0.50), "C2": (0.65, 0.05, 0.45),
    "C3": (0.45, 0.28, 0.10), "C4": (0.40, 0.45, 0.10),
}

# ---------------- helpers ----------------
def _lerp(a, b, u): return a + (b - a) * u
def _smooth(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * (3.0 - 2.0 * u)

def flat_mat(name, rgb):
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
        m.use_nodes = False
        m.diffuse_color = (rgb[0], rgb[1], rgb[2], 1.0)
    return m

def make_box(name, center, dims, color_key):
    bpy.ops.mesh.primitive_cube_add(size=2, location=center)
    ob = bpy.context.active_object
    ob.name = name
    ob.scale = (dims[0] / 2.0, dims[1] / 2.0, dims[2] / 2.0)
    m = flat_mat(name, COL[color_key])
    ob.data.materials.clear()
    ob.data.materials.append(m)
    return ob

def _rot_z(v, th):
    c, s = math.cos(th), math.sin(th)
    return (v[0] * c - v[1] * s, v[0] * s + v[1] * c, v[2])

def make_char(name, loc, yaw):
    body = make_box(name, loc, (0.4, 0.4, 1.6), name)
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    # eyes on the +Y (front) face, z ~1.35
    bpy.context.view_layer.update()
    for i, sx in enumerate((-0.07, 0.07)):
        off = _rot_z((sx, 0.21, 0.55), yaw)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.05,
            location=(loc[0] + off[0], loc[1] + off[1], loc[2] + off[2]))
        eye = bpy.context.active_object
        eye.name = f"{name}_eye{i}"
        m = flat_mat("eyes", COL["eyes"])
        eye.data.materials.clear()
        eye.data.materials.append(m)
        bpy.context.view_layer.update()
        eye.parent = body
        eye.matrix_parent_inverse = body.matrix_world.inverted()
    return body

def wipe():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for bl in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras,
               bpy.data.lights, bpy.data.curves):
        for b in list(bl):
            if b.users == 0:
                bl.remove(b)

def build_scene():
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.render.resolution_x = 1920
    sc.render.resolution_y = 1080
    sc.render.fps = FPS
    sc.frame_start = 1
    sc.frame_end = TOTAL

    # ground (visible, solid color)
    bpy.ops.mesh.primitive_plane_add(size=80, location=(0, 10, 0))
    g = bpy.context.active_object
    g.name = "Ground"
    m = flat_mat("ground", COL["ground"])
    g.data.materials.clear(); g.data.materials.append(m)

    # main street buildings (street along X at y=0, x -30..30)
    make_box("B_N1", (-15, 9, 4.5), (12, 6, 9), "B_N1")
    make_box("B_N2", (0, 9, 3.5), (14, 6, 7), "B_N2")
    make_box("B_N3", (18, 9, 5), (12, 6, 10), "B_N3")
    make_box("B_S1", (-15, -9, 4), (12, 6, 8), "B_S1")
    make_box("B_S2", (2, -9, 4.75), (14, 6, 9.5), "B_S2")
    make_box("B_S3", (19, -9, 3.5), (10, 6, 7), "B_S3")
    # small street side walls (x 5..11 corridor, y 6..24)
    make_box("B_W", (2.5, 15, 3), (5, 18, 6), "B_W")
    make_box("B_E", (13.5, 15, 3.75), (5, 18, 7.5), "B_E")
    # target building: open front at y=24, interior x 3..13, y 24..32
    make_box("T_back", (8, 31.75, 3), (10, 0.5, 6), "T_back")
    make_box("T_left", (3.25, 28, 3), (0.5, 8, 6), "T_left")
    make_box("T_right", (12.75, 28, 3), (0.5, 8, 6), "T_right")
    make_box("T_roof", (8, 28, 6.25), (10, 8, 0.5), "T_roof")

    # parked cars (cubes, each different color)
    make_box("C1", (-16, 5.0, 0.75), (4.2, 1.9, 1.5), "C1")
    make_box("C2", (-7, 5.0, 0.75), (4.2, 1.9, 1.5), "C2")
    make_box("C3", (14, -5.0, 0.75), (4.2, 1.9, 1.5), "C3")
    make_box("C4", (-24, -5.0, 0.75), (4.2, 1.9, 1.5), "C4")

    # characters: W runs from x=-24; M1 waits at end of small street; M2/M3 follow
    make_char("W", (-24, -1.5, 0.8), -PI / 2)
    make_char("M1", (8, 26, 0.8), PI)
    make_char("M2", (-28, -0.6, 0.8), -PI / 2)
    make_char("M3", (-29.5, -2.4, 0.8), -PI / 2)

    # camera + tracking target
    tgt = bpy.data.objects.new("TGT", None)
    tgt.empty_display_size = 0.3
    sc.collection.objects.link(tgt)
    cd = bpy.data.cameras.new("CamData")
    cam = bpy.data.objects.new("Cam", cd)
    sc.collection.objects.link(cam)
    con = cam.constraints.new("TRACK_TO")
    con.target = tgt
    con.track_axis = "TRACK_NEGATIVE_Z"
    con.up_axis = "UP_Y"
    cd.dof.use_dof = True
    cd.dof.focus_object = tgt
    cd.dof.aperture_fstop = 4.0
    sc.camera = cam

# ---------------- character motion (pure functions of t) ----------------
def char_W(t):
    if t <= 3.4:
        x = -24 + 10 * t; y = -1.5; moving = True
        yaw = _lerp(-PI / 2, 0, _smooth((t - 3.2) / 0.4))
    elif t <= 6.0:
        x = 8.0; y = -1.5 + (t - 3.4) * 9.8077; moving = True
        yaw = _lerp(-PI / 2, 0, _smooth((t - 3.2) / 0.4))
    elif t <= 7.4:
        u = _smooth((t - 6.0) / 1.4)
        x = 8.0; y = 24 + 6.5 * u; moving = True
        yaw = _lerp(0, PI, _smooth((t - 7.0) / 0.8))
    else:
        x = 8.0; y = 30.5; moving = False; yaw = PI
    ru = _smooth((t - 12.4) / 0.6)          # fight-ready crouch
    sz = 1 - 0.28 * ru
    cz = 0.8 * sz + (0.05 * math.sin(2 * PI * 3.2 * t) if moving else 0.0)
    lean = (0.15 if moving else 0.0) + 0.22 * ru
    return dict(loc=(x, y, cz), rot=(lean, 0, yaw), scale=(1, 1, sz))

def char_M1(t):
    u = _smooth((t - 7.4) / 1.0)            # steps in to block
    return dict(loc=(8.0, 26 + 1.5 * u, 0.8), rot=(0, 0, PI), scale=(1, 1, 1))

def char_M2(t):
    if t <= 4.2:
        x = -28 + 9.5 * t; y = -0.6; moving = True
        yaw = _lerp(-PI / 2, 0, _smooth((t - 4.0) / 0.4))
    elif t <= 7.6:
        x = 8.0; y = -0.6 + 25.2 * ((t - 4.2) / 3.4); moving = True; yaw = 0.0
    elif t <= 9.2:
        u = _smooth((t - 7.6) / 1.0)
        y = 24.6 + 3.9 * u
        x = _lerp(8.0, 6.3, _smooth((t - 8.6) / 0.6))
        moving = True
        yaw = _lerp(0, PI, _smooth((t - 8.8) / 0.8))
    else:
        x = 6.3; y = 28.5; moving = False; yaw = PI
    cz = 0.8 + (0.05 * math.sin(2 * PI * 3.2 * t + 1.7) if moving else 0.0)
    lean = 0.15 if moving else 0.0
    return dict(loc=(x, y, cz), rot=(lean, 0, yaw), scale=(1, 1, 1))

def char_M3(t):
    if t <= 4.5:
        x = -29.5 + 9.4 * t; y = -2.4; moving = True
        yaw = _lerp(-PI / 2, 0, _smooth((t - 4.3) / 0.4))
    elif t <= 7.9:
        x = 8.0; y = -2.4 + 27.0 * ((t - 4.5) / 3.4); moving = True; yaw = 0.0
    elif t <= 9.5:
        u = _smooth((t - 7.9) / 1.0)
        y = 24.6 + 3.9 * u
        x = _lerp(8.0, 9.7, _smooth((t - 8.9) / 0.6))
        moving = True
        yaw = _lerp(0, PI, _smooth((t - 9.0) / 0.8))
    else:
        x = 9.7; y = 28.5; moving = False; yaw = PI
    cz = 0.8 + (0.05 * math.sin(2 * PI * 3.2 * t + 3.1) if moving else 0.0)
    lean = 0.15 if moving else 0.0
    return dict(loc=(x, y, cz), rot=(lean, 0, yaw), scale=(1, 1, 1))

CHARS = {"W": char_W, "M1": char_M1, "M2": char_M2, "M3": char_M3}

# ---------------- camera shot table ----------------
def cam_pose(f, t):
    w = char_W(t)
    wx, wy = w["loc"][0], w["loc"][1]
    if f <= 62:      # S0 side track on main street
        cam = (wx + 3.5, -4.8, 2.2); tgt = (wx, wy, 1.0); L, fs = 35, 4.0
    elif f <= 71:    # S1a whip pan at the corner
        u = _smooth((f - 63) / 9.0)
        cam = (10.5, -3.5, 2.3)
        t0 = (-24 + 10 * 2.58 + 4.0, -1.5, 1.0); t1 = (8.0, 6.0, 1.0)
        tgt = tuple(_lerp(a, b, u) for a, b in zip(t0, t1)); L, fs = 35, 4.0
    elif f <= 120:   # S1b follow down the small street
        cam = (8.0, max(wy - 6.0, -4.0), 2.6); tgt = (wx, wy, 1.0); L, fs = 35, 4.0
    elif f <= 156:   # S2 M1 reveal, push-in
        u = _smooth((f - 121) / 36.0)
        cam = (8.0, _lerp(19.5, 21.0, u), 1.7); tgt = (8.0, 26.0, 1.2); L, fs = 60, 2.8
    elif f <= 192:   # S3 followers closing in
        u = _smooth((f - 157) / 36.0)
        m2 = char_M2(t); m3 = char_M3(t)
        cam = (8.0, _lerp(23.2, 22.4, u), 1.9)
        tgt = ((m2["loc"][0] + m3["loc"][0]) / 2.0,
               (m2["loc"][1] + m3["loc"][1]) / 2.0, 1.0); L, fs = 50, 2.8
    elif f <= 230:   # S4 dolly into the building
        u = _smooth((f - 193) / 38.0)
        cam = (8.0, _lerp(20.0, 24.6, u), _lerp(2.2, 2.0, u))
        tgt = (wx, wy, 1.0); L, fs = 35, 4.0
    elif f <= 273:   # S5 OTS M1 ("you can't escape now")
        cam = (6.8, 30.9, 1.75); tgt = (8.0, 27.5, 1.25); L, fs = 50, 2.0
    elif f <= 297:   # S6 the two men grin
        cam = (8.0, 25.4, 1.6); tgt = (8.0, 28.5, 1.1); L, fs = 50, 2.8
    else:            # S7 W close-up ("we'll see", readies)
        u = _smooth((f - 298) / 43.0)
        cam = (8.0, _lerp(29.0, 29.5, u), 1.3); tgt = (8.0, 30.4, 1.0); L, fs = 50, 2.0
    # micro handheld wobble
    cam = (cam[0] + 0.003 * math.sin(2 * PI * f / 7.0),
           cam[1] + 0.003 * math.cos(2 * PI * f / 9.0), cam[2])
    return cam, tgt, L, fs

def anim():
    sc = bpy.context.scene
    cam = bpy.data.objects["Cam"]
    cd = cam.data
    tgt = bpy.data.objects["TGT"]
    for f in range(1, TOTAL + 1):
        sc.frame_set(f)
        t = (f - 1) / FPS
        for name, fn in CHARS.items():
            p = fn(t)
            ob = bpy.data.objects[name]
            ob.location = p["loc"]
            ob.rotation_euler = p["rot"]
            ob.scale = p["scale"]
            ob.keyframe_insert("location", frame=f)
            ob.keyframe_insert("rotation_euler", frame=f)
            ob.keyframe_insert("scale", frame=f)
        c, tg, L, fs = cam_pose(f, t)
        cam.location = c
        tgt.location = tg
        cd.lens = L
        cd.dof.aperture_fstop = fs
        cam.keyframe_insert("location", frame=f)
        tgt.keyframe_insert("location", frame=f)
        cd.keyframe_insert("lens", frame=f)
        cd.keyframe_insert("dof.aperture_fstop", frame=f)

def test(frames, outdir=None):
    outdir = outdir or os.path.join(OUT_DIR, "test")
    os.makedirs(outdir, exist_ok=True)
    sc = bpy.context.scene
    for f in frames:
        sc.frame_set(f)
        sc.render.filepath = os.path.join(outdir, f"f_{f:04d}.png")
        bpy.ops.render.render(write_still=True)
        print("rendered", f)

if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if not args:
        print("usage: -- build | -- test [frames] | -- anim"); raise SystemExit(1)
    if args[0] == "build":
        wipe(); build_scene(); print("built", len(bpy.data.objects), "objects")
    elif args[0] == "anim":
        anim(); print("animated", TOTAL, "frames")
    elif args[0] == "test":
        fr = [int(x) for x in args[1:]] or [30, 90, 140, 175, 210, 250, 285, 320]
        test(fr)
