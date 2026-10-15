# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
# Brute impact-effect meshes (procedural, no external assets): writes <out>/brute_fx.fbx with
#   SM_BruteFx_Ring  open band, radius 1 m, height 1 m, base at z 0 (expanding shockwave wall; scaled per impact)
#   SM_BruteFx_Arc   120 deg piece of the same band centred on +X (thunderclap cone front)
#   SM_BruteFx_Puff  lumpy low-poly dust ball, radius ~1 m
#   SM_BruteFx_Rock  chunky asphalt rock, ~1 m
#   SM_BruteFx_Crater shallow bowl with a raised broken rim, radius 1 m (floor at z -0.12, rim up to +0.18)
# usage: Blender -b --factory-startup -P tools/brute/make_fx_meshes.py -- <out_dir>
import bpy, bmesh, sys, os, math, random
from mathutils import Vector, noise

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0] if argv else os.path.expanduser('~/hulk-scratch/brute_fx')
os.makedirs(OUT, exist_ok=True)
random.seed(1015)
bpy.ops.wm.read_factory_settings(use_empty=True)

def obj(name, bm):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(ob)
    return ob

def band(name, a0, a1, segs):
    bm = bmesh.new(); ring_lo, ring_hi = [], []
    for i in range(segs + 1):
        a = a0 + (a1 - a0) * i / segs
        ring_lo.append(bm.verts.new((math.cos(a), math.sin(a), 0.0)))
        ring_hi.append(bm.verts.new((math.cos(a) * 0.92, math.sin(a) * 0.92, 1.0)))   # slightly leaning in at the top
    for i in range(segs):
        bm.faces.new((ring_lo[i], ring_lo[i + 1], ring_hi[i + 1], ring_hi[i]))
    uv = bm.loops.layers.uv.new()
    for f in bm.faces:
        for l in f.loops:
            a = math.atan2(l.vert.co.y, l.vert.co.x); l[uv].uv = ((a - a0) / max(a1 - a0, 1e-6), l.vert.co.z)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return obj(name, bm)

band('SM_BruteFx_Ring', 0.0, 2 * math.pi, 64)
band('SM_BruteFx_Arc', -math.pi / 3, math.pi / 3, 24)

bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
for v in bm.verts:
    v.co *= 0.82 + 0.3 * noise.noise(v.co * 1.7 + Vector((3.1, 1.7, 0.4)))
    v.co.z *= 0.8
obj('SM_BruteFx_Puff', bm)

bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=1, radius=0.5)
for v in bm.verts:
    v.co = Vector((v.co.x * random.uniform(0.7, 1.3), v.co.y * random.uniform(0.7, 1.3), v.co.z * random.uniform(0.5, 0.9)))
obj('SM_BruteFx_Rock', bm)

# crater: concentric rings, bowl floor + broken rim lumps
bm = bmesh.new(); rings = []
R = [0.0, 0.35, 0.65, 0.85, 0.95, 1.05, 1.2]
Z = [-0.12, -0.11, -0.07, 0.02, 0.14, 0.08, 0.0]
N = 40
centre = bm.verts.new((0, 0, Z[0]))
for k in range(1, len(R)):
    rr = []
    for i in range(N):
        a = 2 * math.pi * i / N
        jr = R[k] * (1 + 0.08 * noise.noise(Vector((math.cos(a) * 2, math.sin(a) * 2, k))))
        jz = Z[k] + (0.06 * noise.noise(Vector((math.cos(a) * 3, math.sin(a) * 3, 9.0 + k))) if k in (4, 5) else 0.0)
        rr.append(bm.verts.new((math.cos(a) * jr, math.sin(a) * jr, jz)))
    rings.append(rr)
for i in range(N): bm.faces.new((centre, rings[0][i], rings[0][(i + 1) % N]))
for k in range(len(rings) - 1):
    for i in range(N): bm.faces.new((rings[k][i], rings[k + 1][i], rings[k + 1][(i + 1) % N], rings[k][(i + 1) % N]))
uv = bm.loops.layers.uv.new()
for f in bm.faces:
    for l in f.loops: l[uv].uv = (l.vert.co.x * 0.5 + 0.5, l.vert.co.y * 0.5 + 0.5)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
for f in bm.faces:
    if f.normal.z < 0: f.normal_flip()
obj('SM_BruteFx_Crater', bm)

bpy.ops.object.select_all(action='SELECT')
fbx = os.path.join(OUT, 'brute_fx.fbx')
bpy.ops.export_scene.fbx(filepath=fbx, use_selection=True, object_types={'MESH'}, apply_scale_options='FBX_SCALE_ALL',
                         axis_forward='X', axis_up='Z', mesh_smooth_type='FACE', add_leaf_bones=False)
print('WROTE', fbx)
