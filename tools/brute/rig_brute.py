# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
# Brute body, skinned: the Customuse GLB stays ONE continuous mesh, bound to an 11-bone armature with smooth weights (no cuts, no
# gaps). The game drives these bones from its procedural pose (BruteCharacter.cpp: joint components -> UPoseableMeshComponent).
# Writes <out>/brute_skel.fbx (+ T_Brute_*.png maps) and unreal/WebHomage/Config/BruteRig.json (joints in UE cm, bone names, rest
# arm abduction). usage: Blender -b --factory-startup -P tools/brute/rig_brute.py -- <brute.glb> <out_dir> [height_m]
import bpy, bmesh, sys, os, json, math
from mathutils import Vector
from mathutils.geometry import intersect_point_line

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
GLB = argv[0] if argv else os.path.expanduser('~/hulk-scratch/customuse/brute.glb')
OUT = argv[1] if len(argv) > 1 else os.path.expanduser('~/hulk-scratch/brute_skel')
HM = float(argv[2]) if len(argv) > 2 else 2.6
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.makedirs(OUT, exist_ok=True)

# landmarks, normalised (z: 0 feet .. 1 top; +Y = the character's LEFT, it faces +X): measured from the slice profile of the mesh
L = dict(hips=(0.0, 0.0, 0.34), spine=(0.0, 0.0, 0.47), neck=(0.01, 0.0, 0.805), top=(0.01, 0.0, 1.0),
         sh=(-0.05, 0.235, 0.735), el=(-0.02, 0.33, 0.55), fist=(0.08, 0.39, 0.37),
         hipj=(0.0, 0.085, 0.32), knee=(0.0, 0.10, 0.14), ankle=(0.03, 0.12, 0.03))
LEG_CUT, HEAD_CUT, HEAD_HALF, SPINE_CUT = 0.30, 0.80, 0.12, 0.47
ARM_Y_HI, ARM_Y_LO, ARM_Z_SPLIT, ARM_Z_MIN = 0.20, 0.17, 0.54, 0.33
EL_N = (0.447, -0.894)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
for o in list(bpy.data.objects):
    if o.type != 'MESH': bpy.data.objects.remove(o)
src = [o for o in bpy.data.objects if o.type == 'MESH'][0]
src.name = 'SK_Brute'; src.data.name = 'SK_Brute'
bpy.context.view_layer.objects.active = src; src.select_set(True)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
me = src.data
zs = [v.co.z for v in me.vertices]; z0, z1 = min(zs), max(zs); RH = z1 - z0
xs = [v.co.x for v in me.vertices if (v.co.z - z0) / RH > 0.45 and abs(v.co.y) < 0.1 * RH]
x0 = sum(xs) / len(xs); S = HM / RH
for v in me.vertices: v.co = Vector(((v.co.x - x0) * S, v.co.y * S, (v.co.z - z0) * S))
me.update()
# the generated mesh is split along every UV seam (and carries tiny loose slivers): weld coincident vertices so one surface gets one
# weight (split seams pull apart under skinning), and drop loose islands of a handful of faces
bm = bmesh.new(); bm.from_mesh(me)
nv0 = len(bm.verts)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0008)
bm.faces.ensure_lookup_table()
seen = set(); dead = []
for f in bm.faces:
    if f.index in seen: continue
    isl = []; stack = [f]; seen.add(f.index)
    while stack:
        g = stack.pop(); isl.append(g)
        for e in g.edges:
            for h in e.link_faces:
                if h.index not in seen: seen.add(h.index); stack.append(h)
    if len(isl) < 40: dead += isl
bmesh.ops.delete(bm, geom=dead, context='FACES')
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
print('WELD verts %d -> %d, removed %d sliver faces' % (nv0, len(bm.verts), len(dead)))
bm.to_mesh(me); bm.free(); me.update()
P = {k: Vector((a * HM, b * HM, c * HM)) for k, (a, b, c) in L.items()}
def side_pt(k, s): p = P[k].copy(); p.y *= s; return p

# ---- armature: bone -> (head, tail, parent)
bones = {'pelvis': (P['hips'], P['spine'], None), 'spine': (P['spine'], P['neck'], 'pelvis'), 'head': (P['neck'], P['top'], 'spine')}
for s, t in ((1, 'l'), (-1, 'r')):
    bones['upperarm_' + t] = (side_pt('sh', s), side_pt('el', s), 'spine')
    bones['forearm_' + t] = (side_pt('el', s), side_pt('fist', s), 'upperarm_' + t)
    bones['thigh_' + t] = (side_pt('hipj', s), side_pt('knee', s), 'pelvis')
    bones['shin_' + t] = (side_pt('knee', s), side_pt('ankle', s), 'thigh_' + t)
arm_data = bpy.data.armatures.new('BruteSkeleton'); arm = bpy.data.objects.new('BruteSkeleton', arm_data)
bpy.context.collection.objects.link(arm)
bpy.context.view_layer.objects.active = arm; bpy.ops.object.mode_set(mode='EDIT')
eb = {}
for n in ('pelvis', 'spine', 'head', 'upperarm_l', 'forearm_l', 'upperarm_r', 'forearm_r', 'thigh_l', 'shin_l', 'thigh_r', 'shin_r'):
    h, t, par = bones[n]
    b = arm_data.edit_bones.new(n); b.head = h; b.tail = t; b.roll = 0.0
    if par: b.parent = eb[par]; b.use_connect = False
    eb[n] = b
bpy.ops.object.mode_set(mode='OBJECT')

# ---- weights: region prior (same lateral / height rules as the old cut) + inverse-distance blend to the nearby bones
def part_of(v):
    z = v.co.z / HM; s = 'l' if v.co.y >= 0 else 'r'
    if z < LEG_CUT: return ('shin_' if z < 0.14 else 'thigh_') + s
    if z >= ARM_Z_MIN and abs(v.co.y) / HM > (ARM_Y_HI if z >= ARM_Z_SPLIT else ARM_Y_LO):
        fe = (abs(v.co.y) - P['el'].y) * EL_N[0] + (v.co.z - P['el'].z) * EL_N[1]
        return ('forearm_' if fe > 0 else 'upperarm_') + s
    if z >= HEAD_CUT and abs(v.co.y) < HEAD_HALF * HM: return 'head'
    return 'spine' if z >= SPINE_CUT else 'pelvis'
CAND = {'pelvis': ['pelvis', 'spine', 'thigh_l', 'thigh_r'], 'spine': ['spine', 'pelvis', 'head', 'upperarm_l', 'upperarm_r'], 'head': ['head', 'spine']}
for t in ('l', 'r'):
    CAND['upperarm_' + t] = ['upperarm_' + t, 'spine', 'forearm_' + t]
    CAND['forearm_' + t] = ['forearm_' + t, 'upperarm_' + t]
    CAND['thigh_' + t] = ['thigh_' + t, 'pelvis', 'shin_' + t]
    CAND['shin_' + t] = ['shin_' + t, 'thigh_' + t]
def seg_dist(p, a, b):
    q, f = intersect_point_line(p, a, b); f = min(max(f, 0.0), 1.0)
    return (p - (a + (b - a) * f)).length
groups = {n: src.vertex_groups.new(name=n) for n in bones}
hist = {}
for v in me.vertices:
    prim = part_of(v)
    ws = {}
    for n in CAND[prim]:
        h, t, _ = bones[n]
        d = seg_dist(v.co, h, t) * (0.7 if n == prim else 1.0) + 0.02
        ws[n] = 1.0 / d ** 4
    top = sorted(ws.items(), key=lambda kv: -kv[1])[:3]
    tot = sum(w for _, w in top)
    for n, w in top:
        if w / tot > 0.01: groups[n].add([v.index], w / tot, 'REPLACE')
    hist[prim] = hist.get(prim, 0) + 1
print('REGIONS', sorted(hist.items()))
# smooth the weights a little across neighbours so joints bend softly
bpy.context.view_layer.objects.active = src
for o in bpy.data.objects: o.select_set(o == src)
bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
try:
    bpy.ops.object.vertex_group_smooth(group_select_mode='ALL', factor=0.5, repeat=2, expand=0.0)
    bpy.ops.object.vertex_group_normalize_all(lock_active=False)
except Exception as ex: print('smooth skipped:', ex)
bpy.ops.object.mode_set(mode='OBJECT')
mod = src.modifiers.new('Armature', 'ARMATURE'); mod.object = arm
src.parent = arm
unweighted = sum(1 for v in me.vertices if not v.groups)
print('UNWEIGHTED', unweighted)

# deformation self-test: raise both arms 90 deg forward + bend knees, measure the longest edge stretch (tears would explode it)
bpy.context.view_layer.objects.active = arm; bpy.ops.object.mode_set(mode='POSE')
for n, ax, ang in (('upperarm_l', 'X', 80), ('upperarm_r', 'X', 80), ('forearm_l', 'X', 40), ('thigh_l', 'X', 50), ('shin_l', 'X', -60)):
    pb = arm.pose.bones[n]; pb.rotation_mode = 'XYZ'; pb.rotation_euler = (math.radians(ang), 0, 0)
bpy.ops.object.mode_set(mode='OBJECT')
dg = bpy.context.evaluated_depsgraph_get(); ev = src.evaluated_get(dg).to_mesh()
mx = 0.0
for e in me.edges:
    a0, b0 = me.vertices[e.vertices[0]].co, me.vertices[e.vertices[1]].co
    a1, b1 = ev.vertices[e.vertices[0]].co, ev.vertices[e.vertices[1]].co
    r0 = (a0 - b0).length
    if r0 > 1e-4: mx = max(mx, (a1 - b1).length / r0)
print('MAX_EDGE_STRETCH %.2f (a torn / unweighted mesh would show >> 3)' % mx)
src.evaluated_get(dg).to_mesh_clear()
if os.environ.get('BRUTE_RENDER'):
    sc = bpy.context.scene; sc.render.engine = 'BLENDER_EEVEE'; sc.render.resolution_x = sc.render.resolution_y = 800
    w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == 'BACKGROUND'); bg.inputs[1].default_value = 1.2; bg.inputs[0].default_value = (0.5, 0.5, 0.55, 1)
    sun = bpy.data.objects.new('s', bpy.data.lights.new('s', 'SUN')); sun.data.energy = 3; sc.collection.objects.link(sun); sun.rotation_euler = (0.8, 0.2, 0.6)
    cam = bpy.data.objects.new('c', bpy.data.cameras.new('c')); cam.data.type = 'ORTHO'; cam.data.ortho_scale = 3.2; sc.collection.objects.link(cam); sc.camera = cam
    for name, ang in (('front', 0), ('side', 90), ('q', 40)):
        a = math.radians(ang); cam.location = (math.cos(a) * 6, math.sin(a) * 6, 1.3); cam.rotation_euler = (math.pi / 2, 0, a + math.pi / 2)
        sc.render.filepath = os.path.join(OUT, 'pose_%s.png' % name); bpy.ops.render.render(write_still=True)
bpy.context.view_layer.objects.active = arm; bpy.ops.object.mode_set(mode='POSE')
for pb in arm.pose.bones: pb.rotation_euler = (0, 0, 0)
bpy.ops.object.mode_set(mode='OBJECT')

for img in bpy.data.images:
    kind = 'BaseColor' if img.name.startswith('Color') else 'Normal' if img.name.startswith('Normal') else 'ORM' if img.name.startswith('ORM') else None
    if not kind: continue
    img.filepath_raw = os.path.join(OUT, 'T_Brute_%s.png' % kind); img.file_format = 'PNG'; img.save()
for o in bpy.data.objects: o.select_set(o in (src, arm))
fbx = os.path.join(OUT, 'brute_skel.fbx')
bpy.ops.export_scene.fbx(filepath=fbx, use_selection=True, object_types={'MESH', 'ARMATURE'}, path_mode='STRIP', embed_textures=False,
                         apply_scale_options='FBX_SCALE_ALL', axis_forward='X', axis_up='Z', mesh_smooth_type='FACE', add_leaf_bones=False,
                         bake_anim=False, use_armature_deform_only=True, armature_nodetype='NULL')
print('WROTE', fbx)

def ue(v): return [round(v.x * 100, 2), round(-v.y * 100, 2), round(v.z * 100, 2)]
sh, el = P['sh'], P['el']
rest_abd = math.degrees(math.atan2(el.y - sh.y, sh.z - el.z))
JOINT = {'Pelvis': 'pelvis', 'Torso': 'spine', 'Head': 'head', 'UpperArm_L': 'upperarm_l', 'Forearm_L': 'forearm_l', 'UpperArm_R': 'upperarm_r',
         'Forearm_R': 'forearm_r', 'Thigh_L': 'thigh_l', 'Shin_L': 'shin_l', 'Thigh_R': 'thigh_r', 'Shin_R': 'shin_r'}
rig = {'height_cm': HM * 100, 'source': os.path.basename(GLB), 'skeletal': True, 'arm_rest_abd_deg': round(rest_abd, 2),
       'joints': {k: ue(bones[b][0]) for k, b in JOINT.items()}, 'bones': JOINT}
cfg = os.path.join(REPO, 'unreal', 'WebHomage', 'Config', 'BruteRig.json')
json.dump(rig, open(cfg, 'w'), indent=1)
print('WROTE', cfg, 'arm rest abduction %.1f deg' % rest_abd)
