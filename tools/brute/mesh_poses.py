# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
# Pose test bench for the Brute skin: applies the assembled brute_v5 clips to a rigged glb (same 52-bone skeleton),
# picks the hardest frames automatically, measures deformation quality vs bind and renders them (EEVEE, textured, studio light).
# usage: Blender -b --factory-startup -P tools/brute/mesh_poses.py -- <rig.glb> <out_dir> [--norender] [--frames frames.json]
#   writes <out_dir>/stats.json, <out_dir>/frames.json (chosen frames; pass to the "after" run to render the SAME frames),
#   <out_dir>/<pose>_<view>.png
import bpy, sys, os, json, math
import numpy as np
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mesh_common as C

argv = sys.argv[sys.argv.index('--') + 1:]
RIG, OUT = argv[0], argv[1]
NORENDER = '--norender' in argv
FRAMES_IN = argv[argv.index('--frames') + 1] if '--frames' in argv else None
RES = int(os.environ.get('MESH_RES', '720'))
os.makedirs(OUT, exist_ok=True)

C.reset()
acts = C.load_anim_actions()
arm, me, objs = C.load_rig(RIG)
for o in objs:
    if o not in (arm, me): bpy.data.objects.remove(o)
C.rest_pose(arm)
bpy.context.view_layer.update()
sc = bpy.context.scene
if '--weld' in argv:
    # engine-equivalent shading: merge the glTF UV-seam vertex splits (UVs stay per corner) and keep smooth per-position
    # normals; otherwise Blender rebuilds normals per UV island under deformation (island-shaped facets no engine shows)
    C.weld_mesh(me)
W, names = C.weights(me)
rest = C.rest_co(me)
wid, nW = C.weld_map(rest)
if '--weights' in argv:  # try a welded weight matrix from mesh_fix.py without exporting a glb
    W = np.load(argv[argv.index('--weights') + 1])[wid]; C.set_weights(me, W, names)
E = C.edges(me)
# unique welded edges
we = np.sort(wid[E], 1); _, ue = np.unique(we, axis=0, return_index=True); E = E[ue]
T = C.tris(me)
L0 = np.linalg.norm(rest[E[:, 0]] - rest[E[:, 1]], axis=1)
A0 = C.tri_area(rest, T)
def tri_normals(co):
    n = np.cross(co[T[:, 1]] - co[T[:, 0]], co[T[:, 2]] - co[T[:, 0]])
    return n / np.maximum(1e-12, np.linalg.norm(n, axis=1, keepdims=True))
N0 = tri_normals(rest)
H = rest[:, 2].max() - rest[:, 2].min()
# region labels (by dominant bone of the triangle)
TW = W[T].sum(1)  # (nT, G)
tdom = TW.argmax(1)
def g(n): return names.index(n)
REG = {
    'shoulder': [g(s + x) for s in ('Left', 'Right') for x in ('Shoulder', 'Arm')] + [g('Spine2'), g('Neck')],
    'elbow': [g(s + x) for s in ('Left', 'Right') for x in ('ForeArm',)],
    'hand': [j for j, n in enumerate(names) if 'Hand' in n],
    'head': [g('Head')],
    'legs': [j for j, n in enumerate(names) if 'Leg' in n or 'Foot' in n or 'Toe' in n],
    'torso': [g('Hips'), g('Spine'), g('Spine1')],
}
treg = {k: np.isin(tdom, v) for k, v in REG.items()}
# shoulder neighbourhood: triangles with any weight on Shoulder/Arm AND torso (the deltoid/trap/pec blend zone)
sh_cols = [g(s + x) for s in ('Left', 'Right') for x in ('Shoulder', 'Arm')]
treg['shoulder_blend'] = (TW[:, sh_cols].sum(1) > 0.15) & (TW[:, [g('Spine2'), g('Spine1'), g('Neck')]].sum(1) > 0.15)
el_cols = [g(s + x) for s in ('Left', 'Right') for x in ('Arm', 'ForeArm')]
treg['elbow_blend'] = (TW[:, [g('LeftArm'), g('RightArm')]].sum(1) > 0.15) & (TW[:, [g('LeftForeArm'), g('RightForeArm')]].sum(1) > 0.15)
# edge region: shoulder blend if either vertex has shoulder-ish + torso weights
VW = W
vsh = (VW[:, sh_cols].sum(1) > 0.1) & (VW[:, [g('Spine2'), g('Spine1'), g('Neck')]].sum(1) > 0.1)
esh = vsh[E[:, 0]] | vsh[E[:, 1]]

def bone_def(n):
    pb = arm.pose.bones[n]; b = arm.data.bones[n]
    return np.array((arm.matrix_world @ pb.matrix @ b.matrix_local.inverted() @ arm.matrix_world.inverted()).to_3x3())

def measure():
    co = C.eval_co(me)
    L = np.linalg.norm(co[E[:, 0]] - co[E[:, 1]], axis=1); r = L / np.maximum(1e-9, L0)
    A = C.tri_area(co, T); ar = A / np.maximum(1e-12, A0)
    Nn = tri_normals(co)
    # expected normal = rest normal rotated by the dominant bone (rigid); dot < 0 => folded through, < 0.5 => strongly sheared
    R = np.stack([bone_def(n) for n in names])  # (G,3,3)
    Ne = np.einsum('tij,tj->ti', R[tdom], N0)
    Ne /= np.maximum(1e-12, np.linalg.norm(Ne, axis=1, keepdims=True))
    dot = (Nn * Ne).sum(1)
    s = dict(edge_p1=float(np.percentile(r, 1)), edge_p99=float(np.percentile(r, 99)), edge_min=float(r.min()), edge_max=float(r.max()),
             edges_stretch_gt1_5=int((r > 1.5).sum()), edges_compress_lt0_6=int((r < 0.6).sum()),
             sh_edge_min=float(r[esh].min()), sh_edge_max=float(r[esh].max()), sh_edges_bad=int(((r < 0.6) | (r > 1.5))[esh].sum()),
             tri_area_min=float(ar.min()), tris_collapsed_lt0_3=int((ar < 0.3).sum()),
             folded=int((dot < 0).sum()), sheared=int((dot < 0.5).sum()))
    for k, m in treg.items():
        s['folded_' + k] = int((dot[m] < 0).sum()); s['sheared_' + k] = int((dot[m] < 0.5).sum()); s['collapsed_' + k] = int((ar[m] < 0.3).sum())
    s['_score'] = s['folded'] * 3 + s['sheared'] + s['edges_compress_lt0_6'] + s['edges_stretch_gt1_5']
    return s, co

def bpos(n): return arm.matrix_world @ arm.pose.bones[n].head

def clip_range(a):
    return int(round(a.frame_range[0])), int(round(a.frame_range[1]))

# ---------- frame selection
if FRAMES_IN:
    poses = json.load(open(FRAMES_IN))
else:
    ct = C.clip_times(); poses = []
    def scan(clip, key):
        a = acts[clip]; C.assign(arm, a); f0, f1 = clip_range(a); vals = []
        for f in range(f0, f1 + 1):
            sc.frame_set(f); vals.append((key(), f))
        return vals
    hz = lambda: max(bpos('LeftHand').z, bpos('RightHand').z)
    poses.append(('Uppercut_extended', 'Uppercut', max(scan('Uppercut', hz))[1]))
    sep = lambda: (bpos('LeftHand') - bpos('RightHand')).length
    a = acts['Clap']; f0, _ = clip_range(a); fh = f0 + round(ct.get('Clap', {}).get('hit', 0.7) * 30)
    wide = [v for v in scan('Clap', sep) if v[1] < fh]
    poses.append(('Clap_wide', 'Clap', max(wide)[1])); poses.append(('Clap_impact', 'Clap', fh))
    poses.append(('Lift_overhead', 'Lift', max(scan('Lift', hz))[1]))
    a = acts['Smash']; f0, _ = clip_range(a); fh = f0 + round(ct.get('Smash', {}).get('hit', 1.17) * 30)
    poses.append(('Smash_overhead', 'Smash', max(v for v in scan('Smash', hz) if v[1] < fh)[1]))
    poses.append(('Smash_impact', 'Smash', fh))
    poses.append(('Land_crouch', 'Land', min(scan('Land', lambda: bpos('Hips').z))[1]))
    poses.append(('Run_stride', 'Run', max(scan('Run', lambda: (bpos('LeftFoot') - bpos('RightFoot')).length))[1]))
    poses.append(('WallAttach_overhead', 'WallAttach', max(scan('WallAttach', hz))[1]))
    a = acts['StopLunge']; poses.append(('StopLunge_coil', 'StopLunge', clip_range(a)[1]))
    poses.append(('Throw_windup', 'Throw', max(scan('Throw', hz))[1]))
    poses.append(('Jump_launch', 'Jump', min(scan('Jump', lambda: bpos('Hips').z))[1]))
    poses.append(('Fall_spread', 'Fall', max(scan('Fall', sep))[1]))
    poses.append(('PunchR_extended', 'PunchR', clip_range(acts['PunchR'])[0] + 30))
    # worst frame of every clip by the deformation score (sampled every 2nd frame)
    for clip, a in sorted(acts.items()):
        C.assign(arm, a); f0, f1 = clip_range(a); best = None
        for f in range(f0, f1 + 1, 2):
            sc.frame_set(f); s, _ = measure()
            if best is None or s['_score'] > best[0]: best = (s['_score'], f)
        poses.append(('%s_worst' % clip, clip, best[1]))
    json.dump(poses, open(os.path.join(OUT, 'frames.json'), 'w'), indent=0)

# ---------- measure every pose + all frames summary
stats = {}
C.rest_pose(arm); arm.animation_data_create(); arm.animation_data.action = None
for pb in arm.pose.bones: pb.matrix_basis = Matrix()
sc.frame_set(1); bpy.context.view_layer.update()
stats['bind'], _ = measure()
for pname, clip, f in poses:
    C.assign(arm, acts[clip]); sc.frame_set(f); s, _ = measure(); s['clip'] = clip; s['frame'] = f; stats[pname] = s
# whole-library aggregate (every 2nd frame of every clip)
agg = dict(frames=0, folded=0, sheared=0, edges_bad=0, sh_edges_bad=0, folded_shoulder_blend=0, folded_elbow_blend=0, folded_head=0, collapsed=0)
for clip, a in sorted(acts.items()):
    C.assign(arm, a); f0, f1 = clip_range(a)
    for f in range(f0, f1 + 1, 2):
        sc.frame_set(f); s, _ = measure(); agg['frames'] += 1
        agg['folded'] += s['folded']; agg['sheared'] += s['sheared']; agg['edges_bad'] += s['edges_compress_lt0_6'] + s['edges_stretch_gt1_5']
        agg['sh_edges_bad'] += s['sh_edges_bad']; agg['folded_shoulder_blend'] += s['folded_shoulder_blend']; agg['folded_elbow_blend'] += s['folded_elbow_blend']
        agg['folded_head'] += s['folded_head']; agg['collapsed'] += s['tris_collapsed_lt0_3']
stats['_all_frames'] = agg
json.dump(stats, open(os.path.join(OUT, 'stats.json'), 'w'), indent=1)
for k, s in stats.items():
    if k.startswith('_'): print('AGG', s); continue
    print('%-22s fold %4d shear %4d  edge %.2f..%.2f bad %4d  sh %.2f..%.2f shbad %3d  fold sh/el/head %d/%d/%d collapsed %d' % (
        k, s['folded'], s['sheared'], s['edge_min'], s['edge_max'], s['edges_stretch_gt1_5'] + s['edges_compress_lt0_6'],
        s['sh_edge_min'], s['sh_edge_max'], s['sh_edges_bad'], s['folded_shoulder_blend'], s['folded_elbow_blend'], s['folded_head'], s['tris_collapsed_lt0_3']))
if NORENDER: sys.exit(0)

# ---------- render
sc.render.engine = 'BLENDER_EEVEE' if 'BLENDER_EEVEE' in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE_NEXT'
sc.render.resolution_x = RES; sc.render.resolution_y = int(RES * 4 / 3); sc.render.film_transparent = False
sc.view_settings.view_transform = 'AgX'
try: sc.eevee.taa_render_samples = 32
except Exception: pass
wd = bpy.data.worlds.new('w'); sc.world = wd; wd.use_nodes = True
wd.node_tree.nodes['Background'].inputs[0].default_value = (0.32, 0.33, 0.36, 1); wd.node_tree.nodes['Background'].inputs[1].default_value = 0.6
def light(name, typ, loc, energy, size=2.0, color=(1, 1, 1)):
    l = bpy.data.lights.new(name, typ); l.energy = energy; l.color = color
    if typ == 'AREA': l.size = size
    o = bpy.data.objects.new(name, l); sc.collection.objects.link(o); o.location = loc
    d = Vector((0, 0, 0.1)) - Vector(loc); o.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler(); return o
# character faces +X in this rig's space (toes at +x)
lrig = bpy.data.objects.new('lrig', None); sc.collection.objects.link(lrig)
for lo_ in (light('key', 'AREA', (3.0, -2.2, 2.6), 450, 2.5), light('fill', 'AREA', (2.5, 3.0, 1.0), 180, 3.0, (0.9, 0.95, 1.0)),
            light('rim', 'AREA', (-3.0, 0.5, 2.8), 400, 2.0, (1.0, 0.97, 0.9))):
    lo_.parent = lrig
# ground
bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, rest[:, 2].min()))
gm = bpy.data.materials.new('ground'); gm.use_nodes = True; gm.node_tree.nodes['Principled BSDF'].inputs[0].default_value = (0.18, 0.18, 0.19, 1)
bpy.context.object.data.materials.append(gm)
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
cam.data.lens = 50
VIEWS = {'front': 0, 'q34': 40, 'side': 90, 'back': 180, 'bq34': 220, 'shf': 30, 'shb': 200, 'hdf': 35, 'hdb': 160, 'hds': 100}
UPPER = np.isin(W.argmax(1), REG['shoulder'])
HEADV = np.isin(W.argmax(1), REG['head'] + [g('Neck')])
def facing():
    """character forward (+X at bind) rotated by the Hips pose, flattened"""
    R = bone_def('Hips'); f = R @ np.array([1.0, 0, 0]); a = math.atan2(f[1], f[0]); return a
def shoot(path, view, co):
    fa = facing(); ang = math.radians(VIEWS[view]) + fa
    lrig.rotation_euler = (0, 0, fa); lrig.location = (co[:, 0].mean(), co[:, 1].mean(), 0)
    sel = co[UPPER] if view in ('shf', 'shb') else (co[HEADV] if view.startswith('hd') else co)
    lo, hi = sel.min(0), sel.max(0); ctr = Vector(((lo + hi) / 2).tolist())
    ext = max(hi[2] - lo[2], 0.75 * max(hi[0] - lo[0], hi[1] - lo[1]))
    dist = ext * 1.08 / (2 * math.tan(cam.data.angle_y / 2)) + 0.3
    d = Vector((math.cos(ang), math.sin(ang), 0.25 if view in ('shf', 'shb') else (0.35 if view.startswith('hd') else 0.12))).normalized()
    cam.location = ctr + d * dist; cam.rotation_euler = (ctr - cam.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = path; bpy.ops.render.render(write_still=True)

C.rest_pose(arm); arm.animation_data_create(); arm.animation_data.action = None; sc.frame_set(1)
co = C.eval_co(me)
for v in ('front', 'q34', 'side', 'back'):
    shoot(os.path.join(OUT, 'bind_%s.png' % v), v, co)
for pname, clip, f in poses:
    C.assign(arm, acts[clip]); sc.frame_set(f); co = C.eval_co(me)
    for v in (os.environ.get('MESH_VIEWS', 'q34,bq34,shf,shb').split(',')):
        shoot(os.path.join(OUT, '%s_%s.png' % (pname, v)), v, co)
print('DONE', OUT)
