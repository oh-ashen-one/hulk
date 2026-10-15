# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
# Brute body: cut the single Customuse/Tripo GLB of the Brute (rest pose, arms angled down, facing +X in Blender) into 11 rigid parts
# for the procedural rig in Source/WebHomage/Brute/BruteCharacter.cpp, each with its origin at its joint; the arms are rotated about the
# shoulder so they hang straight down at rest (the rig's ShAbd then means real abduction). Writes:
#   <out>/brute_parts.fbx               11 mesh objects SM_Brute_<Part> (metres, embedded textures)
#   unreal/WebHomage/Config/BruteRig.json   joint positions (UE cm, feet origin, X forward, Y right) read by the pawn at runtime
# usage: Blender -b --factory-startup -P tools/brute/segment_brute.py -- <brute.glb> <out_dir> [height_m]
import bpy, bmesh, sys, os, json, math
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
GLB = argv[0] if argv else os.path.expanduser('~/hulk-scratch/customuse/brute.glb')
OUT = argv[1] if len(argv) > 1 else os.path.expanduser('~/hulk-scratch/brute_parts')
HM = float(argv[2]) if len(argv) > 2 else 2.6
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.makedirs(OUT, exist_ok=True)

# landmarks, normalised (z: 0 feet .. 1 top; y: raw lateral / raw height; +Y = the character's LEFT, it faces +X), measured from the
# slice profile of the generated mesh (tools/brute/README: shoulder top ~.80, armpit ~.68, fists .36-.48 at |y| .30-.48, crotch .265)
L = dict(hips=(0.0, 0.0, 0.34), spine=(0.0, 0.0, 0.47), neck=(0.01, 0.0, 0.805), sh=(-0.05, 0.235, 0.735), el=(-0.02, 0.33, 0.55),
         hipj=(0.0, 0.085, 0.32), knee=(0.0, 0.10, 0.14))
LEG_CUT, KNEE_CUT, SPINE_CUT, HEAD_CUT, HEAD_HALF = 0.30, 0.14, 0.47, 0.80, 0.12
# arms vs torso: the slice profile has a clean lateral gap (torso half-width <= .187, arm inner edge >= .21 above z .54; torso <= .15 below)
ARM_Y_HI, ARM_Y_LO, ARM_Z_SPLIT, ARM_Z_MIN = 0.20, 0.17, 0.54, 0.33
EL_N = (0.447, -0.894)  # elbow cut plane normal in (|y|, z): along the shoulder->elbow axis

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
src = [o for o in bpy.data.objects if o.type == 'MESH'][0]
bpy.context.view_layer.objects.active = src
src.select_set(True)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
me = src.data
zs = [v.co.z for v in me.vertices]; z0, z1 = min(zs), max(zs); RH = z1 - z0
xs = [v.co.x for v in me.vertices if (v.co.z - z0) / RH > 0.45 and abs(v.co.y) < 0.1 * RH]
x0 = sum(xs) / len(xs)
S = HM / RH
for v in me.vertices:
    v.co = Vector(((v.co.x - x0) * S, v.co.y * S, (v.co.z - z0) * S))
me.update()
P = {k: Vector((a * HM, b * HM, c * HM)) for k, (a, b, c) in L.items()}

bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
N = len(bm.verts)
def nz(v): return v.co.z / HM
def side(v): return 1 if v.co.y >= 0 else -1   # +1 = left

part = [None] * N
# legs: below the hip cut, split by side; shins below the knee cut
for v in bm.verts:
    if nz(v) < LEG_CUT:
        part[v.index] = ('Shin_' if nz(v) < KNEE_CUT else 'Thigh_') + ('L' if side(v) > 0 else 'R')
# arms: everything beyond the torso's lateral envelope (raw lateral / raw height, compared in normalised units)
arm = {1: set(), -1: set()}
for v in bm.verts:
    if part[v.index] is not None or nz(v) < ARM_Z_MIN: continue
    if abs(v.co.y) / HM > (ARM_Y_HI if nz(v) >= ARM_Z_SPLIT else ARM_Y_LO): arm[side(v)].add(v.index)
for s in (1, -1): print('arm side %+d: %d verts (%.1f %%)' % (s, len(arm[s]), 100.0 * len(arm[s]) / N))
for s, ids in arm.items():
    for i in ids:
        v = bm.verts[i]
        fe = (abs(v.co.y) - P['el'].y) * EL_N[0] + (v.co.z - P['el'].z) * EL_N[1]
        part[i] = ('Forearm_' if fe > 0 else 'UpperArm_') + ('L' if s > 0 else 'R')
for v in bm.verts:
    if part[v.index] is None:
        z = nz(v)
        part[v.index] = 'Head' if (z >= HEAD_CUT and abs(v.co.y) < HEAD_HALF * HM) else ('Torso' if z >= SPINE_CUT else 'Pelvis')

face_part = []
for f in bm.faces:
    cnt = {}
    for v in f.verts: cnt[part[v.index]] = cnt.get(part[v.index], 0) + 1
    face_part.append(max(cnt, key=cnt.get))
bm.free()

# arm straightening: rotate each arm about its shoulder so the shoulder->elbow axis hangs straight down
def arm_rot(s):
    sh = Vector((P['sh'].x, s * P['sh'].y, P['sh'].z)); el = Vector((P['el'].x, s * P['el'].y, P['el'].z))
    d = el - sh; phi = math.atan(d.y / d.z)
    return sh, Matrix.Rotation(phi, 4, 'X'), el
pivots = {'Pelvis': P['hips'], 'Torso': P['spine'], 'Head': P['neck']}
rots = {}
for s, tag in ((1, 'L'), (-1, 'R')):
    sh, R, el = arm_rot(s)
    el2 = sh + (R @ (el - sh).to_4d()).to_3d()
    pivots['UpperArm_' + tag] = sh; pivots['Forearm_' + tag] = el2
    rots['UpperArm_' + tag] = rots['Forearm_' + tag] = (sh, R)
    pivots['Thigh_' + tag] = Vector((P['hipj'].x, s * P['hipj'].y, P['hipj'].z))
    pivots['Shin_' + tag] = Vector((P['knee'].x, s * P['knee'].y, P['knee'].z))

objs = []
for name in sorted(set(face_part)):
    ob = src.copy(); ob.data = src.data.copy(); ob.name = 'SM_Brute_' + name; ob.data.name = ob.name
    bpy.context.collection.objects.link(ob)
    b2 = bmesh.new(); b2.from_mesh(ob.data); b2.faces.ensure_lookup_table()
    bmesh.ops.delete(b2, geom=[f for f, p in zip(b2.faces, face_part) if p != name], context='FACES')
    if name in rots:
        sh, R = rots[name]
        for v in b2.verts: v.co = sh + (R @ (v.co - sh).to_4d()).to_3d()
    pv = pivots[name]
    for v in b2.verts: v.co -= pv
    b2.to_mesh(ob.data); b2.free()
    vs = [v.co for v in ob.data.vertices]
    print('PART %-12s verts %6d  min (%.2f %.2f %.2f) max (%.2f %.2f %.2f)' % (name, len(vs), *[min(c[i] for c in vs) for i in range(3)], *[max(c[i] for c in vs) for i in range(3)]))
    objs.append(ob)
bpy.data.objects.remove(src)

bpy.ops.object.select_all(action='DESELECT')
for ob in objs: ob.select_set(True)
# textures as plain PNGs (Interchange cannot read FBX-embedded payloads); Scripts/build_brute.py builds M_Brute from them
for img in bpy.data.images:
    kind = 'BaseColor' if img.name.startswith('Color') else 'Normal' if img.name.startswith('Normal') else 'ORM' if img.name.startswith('ORM') else None
    if not kind: continue
    img.filepath_raw = os.path.join(OUT, 'T_Brute_%s.png' % kind); img.file_format = 'PNG'; img.save()
    print('WROTE', img.filepath_raw)
fbx = os.path.join(OUT, 'brute_parts.fbx')
bpy.ops.export_scene.fbx(filepath=fbx, use_selection=True, object_types={'MESH'}, path_mode='STRIP', embed_textures=False,
                         apply_scale_options='FBX_SCALE_ALL', axis_forward='X', axis_up='Z', mesh_smooth_type='FACE', add_leaf_bones=False)
print('WROTE', fbx)

# joints for the UE rig: Blender metres (+Y left) -> UE cm (+Y right)
def ue(v): return [round(v.x * 100, 2), round(-v.y * 100, 2), round(v.z * 100, 2)]
rig = {'height_cm': HM * 100, 'source': os.path.basename(GLB), 'joints': {k: ue(v) for k, v in pivots.items()},
       'parts': {('SM_Brute_' + k): k for k in pivots}}
cfg = os.path.join(REPO, 'unreal', 'WebHomage', 'Config', 'BruteRig.json')
json.dump(rig, open(cfg, 'w'), indent=1)
print('WROTE', cfg)
