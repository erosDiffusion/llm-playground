# -*- coding: utf-8 -*-
"""
CINEMATIC DIALOGUE — "It's going to rain."
Director's build script for Blender 5.1 (EEVEE Next).

Characters: A = red cube, B = blue cube (0.4 x 0.4 x 1.6 m), colored-stick style,
each with two dark eyes so orientation reads in over-the-shoulder shots.
Ground: 80m checker plane (1m squares) so camera moves read via parallax.
Sky: Nishita sunset + warm low sun lamp; drifting cloud blobs.

Dialogue (24 fps, 312 frames = 13.0 s):
  S0 f  1- 48  A: "It's going to rain."                          wide two-shot, dolly in (35mm)
  S1 f 49- 84  B: "You think?"                                   OTS over A -> B, push-in (50mm)
  S2 f 85-132  A: "Look at those clouds. They've been building   OTS over B -> A, tilt up to sky (50mm)
                 all afternoon."
  S3 f133-180  B: "We still have an hour before sunset.          OTS over A -> B close, push-in (60mm)
                 We're fine."
  S4 f181-240  A: "An hour? It's 5:47, B. The sky doesn't        WHIP PAN from B side to A + push-in (50mm)
                 keep appointments."
  S5 f241-312  B: "...Fair point. Let's move the gear inside."   two-shot pull-back & rise (35mm)

Usage:
  blender --background --python this_file.py -- build          # build + save .blend
  blender --background --python this_file.py -- test [f ...]   # half-res PNG smoke frames
  blender --background --python this_file.py -- anim           # full-res PNG sequence
  (GUI/MCP: exec(open(this_file).read())  -> defaults to 'build')
Video encode afterwards with system ffmpeg (Blender 5.1 filtered enum blocks FFMPEG still-format):
  ffmpeg -framerate 24 -i seq/f_%04d.png -c:v libx264 -crf 18 -pix_fmt yuv420p -movflags +faststart out.mp4
"""
import bpy, math, os, sys
from mathutils import Vector

# ---------------- args ----------------
argv = sys.argv
phase = 'build'
frames = []
if '--' in argv:
    rest = argv[argv.index('--') + 1:]
    phase = rest[0] if rest else 'build'
    frames = [int(x) for x in rest[1:]]

WS = '/home/oem/Apps/deepseek-workspace'
OUTDIR = os.path.join(WS, 'generated', 'movies')
SEQDIR = os.path.join(OUTDIR, 'seq')
TESTDIR = os.path.join(OUTDIR, 'test')
BLEND = os.path.join(OUTDIR, 'weather_time_dialogue.blend')
for d in (OUTDIR, SEQDIR, TESTDIR):
    os.makedirs(d, exist_ok=True)

FPS = 24
F0, F1 = 1, 312          # 13.0 s at 24 fps

# ---------------- clean slate ----------------
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.lights,
             bpy.data.cameras, bpy.data.worlds):
    for b in list(coll):
        if b.users == 0:
            coll.remove(b)

scn = bpy.context.scene

# ---------------- film / render settings ----------------
scn.frame_start, scn.frame_end = F0, F1
scn.render.fps = FPS
scn.render.resolution_x, scn.render.resolution_y = 1920, 1080
scn.render.resolution_percentage = 100
try:
    scn.render.engine = 'BLENDER_EEVEE'   # this 5.1 build uses the legacy engine id
except Exception as e:
    print('ENGINE FAIL:', e)
ee = scn.eevee
for name, val in (('taa_render_samples', 64),
                  ('use_raytracing', True)):
    try:
        setattr(ee, name, val)
    except Exception as e:
        print('EEVEE PROP FAIL:', name, e)
scn.render.use_motion_blur = True
try:
    scn.render.motion_blur_shutter = 0.5
except Exception as e:
    print('MOTION BLUR FAIL:', e)
scn.view_settings.view_transform = 'AgX'
try:
    scn.view_settings.look = 'AgX - Punchy'
except Exception as e:
    try:
        looks = [i.identifier for i in
                 scn.view_settings.bl_rna.properties['look'].enum_items]
    except Exception:
        looks = []
    print('LOOK FAIL:', e, 'available:', looks)
scn.render.image_settings.file_format = 'PNG'
scn.render.image_settings.color_mode = 'RGB'

# ---------------- world: sunset gradient (this build's Sky node has no Nishita) ----------------
world = bpy.data.worlds.new('SunsetSky')
scn.world = world
world.use_nodes = True
nt = world.node_tree
nt.nodes.clear()
texco = nt.nodes.new('ShaderNodeTexCoord')
sep = nt.nodes.new('ShaderNodeSeparateXYZ')
mr = nt.nodes.new('ShaderNodeMapRange')
mr.inputs['From Min'].default_value = 0.0     # horizon
mr.inputs['From Max'].default_value = 0.6     # zenith-ish
ramp = nt.nodes.new('ShaderNodeValToRGB')
cr = ramp.color_ramp
cr.elements[0].position = 0.0
cr.elements[0].color = (1.0, 0.48, 0.20, 1.0)     # horizon glow
e1 = cr.elements.new(0.18); e1.color = (0.62, 0.30, 0.32, 1.0)   # mauve band
e2 = cr.elements.new(0.55); e2.color = (0.13, 0.17, 0.34, 1.0)   # dusk blue
cr.elements[-1].position = 1.0
cr.elements[-1].color = (0.04, 0.07, 0.20, 1.0)     # zenith
bg = nt.nodes.new('ShaderNodeBackground')
out = nt.nodes.new('ShaderNodeOutputWorld')
nt.links.new(texco.outputs['Generated'], sep.inputs['Vector'])
nt.links.new(sep.outputs['Z'], mr.inputs['Value'])
nt.links.new(mr.outputs['Result'], ramp.inputs['Fac'])
nt.links.new(ramp.outputs['Color'], bg.inputs['Color'])
nt.links.new(bg.outputs['Background'], out.inputs['Surface'])

# ---------------- warm low sun lamp (front-left of camera) ----------------
sun_data = bpy.data.lights.new('Sun', 'SUN')
sun_data.energy = 3.0
sun_data.color = (1.0, 0.78, 0.55)
try:
    sun_data.angle = math.radians(1.2)
except Exception:
    pass
sun_obj = bpy.data.objects.new('Sun', sun_data)
scn.collection.objects.link(sun_obj)
v_from = Vector((-0.45, -0.9, 0.14)).normalized()   # light arrives from front-left, ~8 deg elevation
sun_obj.rotation_euler = v_from.to_track_quat('Z', 'Y').to_euler()

# ---------------- materials helper ----------------
def new_mat(name, color, rough):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*color, 1.0)
    b.inputs['Roughness'].default_value = rough
    return m

# ---------------- ground: 80m checker plane, 1m squares ----------------
bpy.ops.mesh.primitive_plane_add(size=80, location=(0, 0, 0))
ground = bpy.context.active_object
ground.name = 'Ground'
gm = bpy.data.materials.new('GroundMat')
gm.use_nodes = True
gnt = gm.node_tree
gb = gnt.nodes['Principled BSDF']
texco = gnt.nodes.new('ShaderNodeTexCoord')
checker = gnt.nodes.new('ShaderNodeTexChecker')
checker.inputs['Scale'].default_value = 1.0
checker.inputs['Color1'].default_value = (0.30, 0.32, 0.35, 1.0)
checker.inputs['Color2'].default_value = (0.24, 0.26, 0.29, 1.0)
gnt.links.new(texco.outputs['Object'], checker.inputs['Vector'])
gnt.links.new(checker.outputs['Color'], gb.inputs['Base Color'])
gb.inputs['Roughness'].default_value = 0.85
ground.data.materials.append(gm)

# ---------------- characters: A red, B blue (facing each other) ----------------
def make_char(name, color, base):
    bpy.ops.mesh.primitive_cube_add(size=1, location=base)
    o = bpy.context.active_object
    o.name = name
    o.scale = (0.4, 0.4, 1.6)
    bpy.ops.object.transform_apply(scale=True)
    o.data.materials.append(new_mat(name + 'Mat', color, 0.35))
    sign = 1 if name == 'A' else -1          # A faces +X, B faces -X
    eye_mat = new_mat('EyeMat', (0.02, 0.02, 0.02), 0.2)
    for i, dy in enumerate((-0.09, 0.09)):
        bpy.ops.mesh.primitive_uv_sphere_add(
            radius=0.035, location=(base[0] + sign * 0.205, base[1] + dy, 1.35))
        e = bpy.context.active_object
        e.name = '%s_eye%d' % (name, i)
        e.data.materials.append(eye_mat)
        bpy.ops.object.select_all(action='DESELECT')
        e.select_set(True)
        o.select_set(True)
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.parent_set(type='OBJECT', keep_transform=True)
    return o

charA = make_char('CharA', (0.72, 0.06, 0.05), (-1.0, 0.0, 0.8))
charB = make_char('CharB', (0.03, 0.28, 0.85), (1.0, 0.0, 0.8))

# ---------------- clouds (drift +X over the scene) ----------------
CLOUDS = [
    ((-5, 3, 8.5),   (3.5, 2.5, 1.1), 0.93),   # hero cloud for S2 tilt-up
    ((-10, -4, 13),  (5.0, 3.0, 1.4), 0.90),
    ((-3, -9, 16),   (6.0, 4.0, 1.7), 0.88),
    ((5, -6, 14),    (4.5, 3.0, 1.3), 0.92),
    ((10, -11, 18),  (7.0, 4.0, 2.0), 0.87),
    ((15, -3, 15),   (4.0, 2.5, 1.2), 0.91),
    ((2, -14, 20),   (6.0, 3.0, 1.5), 0.86),
    ((-8, 12, 6),    (4.0, 2.0, 0.9), 0.95),   # low sunset clouds for S5 ending
    ((6, 14, 5),     (3.5, 2.0, 0.8), 0.94),
]
cloud_objs = []
for i, (loc, scale, shade) in enumerate(CLOUDS):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1, location=loc)
    c = bpy.context.active_object
    c.name = 'Cloud%d' % i
    c.scale = scale
    c.data.materials.append(
        new_mat('CloudMat%d' % i, (shade, shade, min(1.0, shade + 0.03)), 1.0))
    cloud_objs.append(c)

# ---------------- camera rig ----------------
tgt = bpy.data.objects.new('CamTarget', None)
scn.collection.objects.link(tgt)
cam_data = bpy.data.cameras.new('Cam')
cam_data.lens = 50
cam_data.dof.use_dof = True
cam_data.dof.focus_object = tgt
cam = bpy.data.objects.new('Cam', cam_data)
scn.collection.objects.link(cam)
con = cam.constraints.new('TRACK_TO')
con.target = tgt
con.track_axis = 'TRACK_NEGATIVE_Z'
con.up_axis = 'UP_Y'
scn.camera = cam

# ---------------- shot table (all positions computed for safe full-frame coverage) ----------------
def lerp(a, b, t):
    return a + (b - a) * t

def lerp3(a, b, t):
    return (lerp(a[0], b[0], t), lerp(a[1], b[1], t), lerp(a[2], b[2], t))

def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)

SHOTS = [
    dict(f0=1,   f1=48,  lens=35, fstop=4.0,
         P0=(0, -7.2, 2.3),   P1=(0, -4.4, 1.75),
         T0=(0, 0, 1.25),     T1=(0, 0, 1.15)),
    dict(f0=49,  f1=84,  lens=50, fstop=2.8,
         P0=(-0.62, -2.05, 1.52), P1=(-0.58, -1.82, 1.50),
         T0=(1.0, 0, 1.18),   T1=(1.0, 0, 1.18)),
    dict(f0=85,  f1=132, lens=50, fstop=2.8,
         P0=(0.62, -2.0, 1.5), P1=(0.60, -1.95, 1.52),
         T0=(-1.0, 0, 1.18),  T1=(-1.0, 0, 3.4)),
    dict(f0=133, f1=180, lens=60, fstop=2.0,
         P0=(-0.72, -1.42, 1.5), P1=(-0.70, -1.22, 1.49),
         T0=(1.0, 0, 1.2),    T1=(1.0, 0, 1.2)),
    dict(f0=181, f1=240, lens=50, fstop=2.4, whip=True,
         WP0=(0.9, -2.6, 1.6),   WP1=(-0.9, -2.3, 1.5),
         WT0=(1.0, 0, 1.2),      WT1=(-1.0, 0, 1.2),
         pushY=-2.0),
    dict(f0=241, f1=312, lens=35, fstop=4.0,
         P0=(0, -4.3, 1.7),   P1=(0, -6.9, 2.5),
         T0=(0, 0, 1.2),      T1=(0, 0, 1.35)),
]

def cam_state(f):
    for s in SHOTS:
        if s['f0'] <= f <= s['f1']:
            if s.get('whip'):
                w_end = s['f0'] + 8          # 9-frame whip swing
                if f <= w_end:
                    t = smooth((f - s['f0']) / 8.0)
                    P = lerp3(s['WP0'], s['WP1'], t)
                    T = lerp3(s['WT0'], s['WT1'], t)
                else:
                    t = smooth((f - w_end) / (s['f1'] - w_end))
                    P = (s['WP1'][0], lerp(s['WP1'][1], s['pushY'], t), s['WP1'][2])
                    T = s['WT1']
            else:
                t = smooth((f - s['f0']) / (s['f1'] - s['f0']))
                P = lerp3(s['P0'], s['P1'], t)
                T = lerp3(s['T0'], s['T1'], t)
            # subtle handheld micro-wobble (few mm, low frequency)
            P = (P[0] + 0.003 * math.sin(f * 0.37 + 1.7),
                 P[1] + 0.003 * math.cos(f * 0.29 + 0.4),
                 P[2] + 0.002 * math.sin(f * 0.53))
            return s['lens'], s['fstop'], P, T
    raise RuntimeError('no shot covers frame %d' % f)

# ---------------- character performance ----------------
SPEECH = {
    'A': [(1, 48), (85, 132), (181, 240)],
    'B': [(49, 84), (133, 180), (241, 312)],
}

def char_pose(char, f):
    """Returns (rot_y lean/sway, z bob offset above base 0.8)."""
    sign = 1.0 if char == 'A' else -1.0      # A faces +X: positive rotY leans toward B
    env, bob = 0.0, 0.0
    for fs, fe in SPEECH[char]:
        if fs <= f <= fe:
            e = min(1.0, (f - fs) / 5.0, (fe - f) / 5.0)
            env = max(env, e)
            bob += 0.015 * e * math.sin(
                math.pi * 4 * (f - fs) / (fe - fs) + (0.9 if char == 'A' else 2.3))
    sway = 0.012 * math.sin(2 * math.pi * (f - 1) / 80 + (0.0 if char == 'A' else 2.1))
    return sign * 0.05 * env + sway, bob

# ---------------- bake animation (per-frame keys = full control) ----------------
BASE = {'A': (-1.0, 0.0), 'B': (1.0, 0.0)}
CHARS = {'A': charA, 'B': charB}

for f in range(F0, F1 + 1):
    lens, fstop, P, T = cam_state(f)
    cam.location = P
    tgt.location = T
    cam.data.lens = lens
    cam.data.dof.aperture_fstop = fstop
    cam.keyframe_insert('location', frame=f)
    tgt.keyframe_insert('location', frame=f)
    cam.data.keyframe_insert('lens', frame=f)
    cam.data.dof.keyframe_insert('aperture_fstop', frame=f)
    for char, obj in CHARS.items():
        ry, bob = char_pose(char, f)
        bx, by = BASE[char]
        obj.location = (bx, by, 0.8 + bob)
        obj.rotation_euler = (0.0, ry, 0.0)
        obj.keyframe_insert('location', frame=f)
        obj.keyframe_insert('rotation_euler', frame=f)

for c in cloud_objs:
    c.keyframe_insert('location', frame=F0)
    c.location.x += 1.5
    c.keyframe_insert('location', frame=F1)

scn.frame_set(F0)
print('SCENE BUILT: objects=%d phase=%s' % (len(bpy.data.objects), phase))

# ---------------- phases ----------------
if phase == 'build':
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
    print('BUILD OK ->', BLEND)
elif phase == 'test':
    scn.render.resolution_percentage = 50
    for f in (frames or [24, 70, 118, 160, 186, 225, 300]):
        scn.frame_set(f)
        scn.render.filepath = os.path.join(TESTDIR, 'f_%04d' % f)
        bpy.ops.render.render(write_still=True)
        print('TEST FRAME', f, 'done')
    print('TEST DONE')
elif phase == 'anim':
    scn.frame_set(F0)
    scn.render.filepath = os.path.join(SEQDIR, 'f_')
    bpy.ops.render.render(animation=True)
    print('ANIM DONE ->', SEQDIR)
else:
    print('UNKNOWN PHASE:', phase)
