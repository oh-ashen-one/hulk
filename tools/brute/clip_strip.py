# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
# Contact strips + hand/foot telemetry for Brute clips (Blender, Workbench, headless). For every clip (NLA track) of the GLB:
# N frames from a fixed front-3/4 camera framed on the clip's whole motion, plain background, time stamp per tile, and a JSON
# with per-frame hand/foot world positions (used to find each attack's contact frame).
# usage: Blender -b --factory-startup -P tools/brute/clip_strip.py -- <in.glb> <out_dir> [Clip,Clip,...] [frames=6] [az_deg=35]
import bpy, sys, os, json, math
from mathutils import Vector

a = sys.argv[sys.argv.index('--') + 1:]
GLB, OUT = a[0], a[1]
ONLY = a[2].split(',') if len(a) > 2 and a[2] not in ('', 'all') else None
N = int(a[3]) if len(a) > 3 else 6
AZ = math.radians(float(a[4]) if len(a) > 4 else 35)
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; sc.render.fps = 30
if GLB.lower().endswith('.fbx'): bpy.ops.import_scene.fbx(filepath=GLB)
else: bpy.ops.import_scene.gltf(filepath=GLB)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
meshes = [o for o in bpy.data.objects if o.type == 'MESH' and any(m.type == 'ARMATURE' for m in o.modifiers)]
for o in [o for o in bpy.data.objects if o.type == 'MESH' and o not in meshes]: bpy.data.objects.remove(o)
tracks = {t.name: t.strips[0].action for t in arm.animation_data.nla_tracks} if arm.animation_data else {}
if not tracks and arm.animation_data and arm.animation_data.action: tracks = {'raw': arm.animation_data.action}
for t in list(arm.animation_data.nla_tracks): arm.animation_data.nla_tracks.remove(t)
sc.render.engine = 'BLENDER_WORKBENCH'
sh = sc.display.shading; sh.light = 'STUDIO'; sh.color_type = 'TEXTURE'; sh.show_shadows = True; sh.show_cavity = True
sc.render.resolution_x, sc.render.resolution_y = 420, 560
w = bpy.data.worlds.new('w'); sc.world = w; sc.display.shading.background_type = 'VIEWPORT'
sh.background_type = 'VIEWPORT'; sh.background_color = (0.62, 0.66, 0.72)
sc.render.film_transparent = False
if os.environ.get('STRIP_GROUND', '1') == '1':   # ground plane at z=0 so contact / floating / sinking is visible
    bpy.ops.mesh.primitive_plane_add(size=12, location=(0, 0, 0))
    gp = bpy.context.active_object; gp.name = 'ground'
    gm = bpy.data.materials.new('ground'); gm.diffuse_color = (0.33, 0.35, 0.38, 1); gp.data.materials.append(gm)
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
cam.data.lens = 50
BONES = ['L_Wrist', 'R_Wrist', 'LeftHand', 'RightHand', 'LeftFoot', 'RightFoot', 'Hips', 'Head', 'LeftToeBase', 'RightToeBase']
def bbox():
    dg = bpy.context.evaluated_depsgraph_get(); pts = []
    for m in meshes:
        e = m.evaluated_get(dg); me = e.to_mesh()
        vs = me.vertices; step = max(1, len(vs) // 400)
        pts += [e.matrix_world @ vs[i].co for i in range(0, len(vs), step)]
        e.to_mesh_clear()
    return pts
import subprocess
summary = {}
for name, act in tracks.items():
    if ONLY and name not in ONLY: continue
    arm.animation_data.action = act
    if hasattr(act, 'slots') and len(act.slots): arm.animation_data.action_slot = act.slots[0]
    f0, f1 = (int(round(x)) for x in act.frame_range)
    tele = []; pts = []
    for fr in range(f0, f1 + 1):
        sc.frame_set(fr)
        tele.append({b: list(arm.matrix_world @ arm.pose.bones[b].head) for b in BONES if b in arm.pose.bones})
        if (fr - f0) % 6 == 0 or fr == f1: pts += bbox()
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    c = (lo + hi) / 2; size = max((hi - lo).length, 1e-3)
    # front = -Y (glTF +Z): camera in front, rotated AZ toward +X, slightly above
    d = Vector((math.sin(AZ), -math.cos(AZ), float(os.environ.get("STRIP_ELEV", "0.15")))).normalized()
    cam.location = c + d * size * 1.4
    cam.rotation_euler = (c - cam.location).to_track_quat('-Z', 'Y').to_euler()
    picks = [round(f0 + i * (f1 - f0) / (N - 1)) for i in range(N)]
    tiles = []
    for fr in picks:
        sc.frame_set(fr); p = os.path.join(OUT, '_%s_%03d.png' % (name, fr)); sc.render.filepath = p
        bpy.ops.render.render(write_still=True); tiles.append((p, fr))
    # label + stitch with the system Python's PIL (Blender's Python has none); 2 rows when > 4 tiles
    stitch = """
import sys, json
from PIL import Image, ImageDraw, ImageFont
a = json.loads(sys.argv[1]); ims = [Image.open(p).convert('RGB') for p, _ in a['tiles']]
try: font = ImageFont.load_default(size=22)
except TypeError: font = ImageFont.load_default()
for im, (_, lab) in zip(ims, a['tiles']): ImageDraw.Draw(im).text((10, 8), lab, fill=(0, 0, 0), font=font)
W, H = ims[0].size; cols = (len(ims) + 1) // 2 if len(ims) > 4 else len(ims); rows = (len(ims) + cols - 1) // cols
s = Image.new('RGB', (W * cols, H * rows), 'white')
for i, im in enumerate(ims): s.paste(im, ((i % cols) * W, (i // cols) * H))
s.save(a['out'], quality=88)
"""
    subprocess.run([os.environ.get('SYS_PYTHON', '/opt/homebrew/bin/python3'), '-c', stitch, json.dumps(dict(
        tiles=[(p, '%s f%d t=%.2fs' % (name, fr - f0, (fr - f0) / 30)) for p, fr in tiles], out=os.path.join(OUT, 'strip_%s.jpg' % name)))], check=True)
    for p, fr in tiles: os.remove(p)
    summary[name] = dict(f0=f0, f1=f1, dur=round((f1 - f0) / 30, 3), tele=tele)
    print('STRIP', name, f0, f1, os.path.join(OUT, 'strip_%s.jpg' % name))
json.dump(summary, open(os.path.join(OUT, 'tele.json'), 'w'))
