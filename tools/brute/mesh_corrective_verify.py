# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
# Verify bench for the Brute corrective shape keys: plays the brute_v5 clips on a rig glb, drives every CorrArm* shape key from
# mesh_corrective_lib.weights() (the exact game mapping), measures armpit-region folds / stretch and renders armpit close-ups.
# usage: Blender -b --factory-startup -P tools/brute/mesh_corrective_verify.py -- <rig.glb> <out_dir> [--zero] [--norender]
#        [--frames frames.json] [--views front,back,side]
#   --zero: keep every shape key at 0 (equivalence check)
import bpy, sys, os, json, math
import numpy as np
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mesh_common as C
import mesh_corrective_lib as K

argv = sys.argv[sys.argv.index('--') + 1:]
RIG, OUT = argv[0], argv[1]
ZERO = '--zero' in argv
NORENDER = '--norender' in argv
FRAMES_IN = argv[argv.index('--frames') + 1] if '--frames' in argv else None
VIEWS = argv[argv.index('--views') + 1].split(',') if '--views' in argv else ['front', 'back', 'side']
RES = int(os.environ.get('MESH_RES', '640'))
os.makedirs(OUT, exist_ok=True)

C.reset()
acts = C.load_anim_actions()
arm, me, objs = C.load_rig(RIG)
for o in objs:
    if o not in (arm, me): bpy.data.objects.remove(o)
C.rest_pose(arm); bpy.context.view_layer.update()
sc = bpy.context.scene
C.weld_mesh(me)   # engine-equivalent smooth shading (see mesh_poses.py); shape-key deltas are identical across seam splits
keys = {kb.name: kb for kb in me.data.shape_keys.key_blocks} if me.data.shape_keys else {}
print('SHAPE KEYS', list(keys))

W, names = C.weights(me)
rest = C.rest_co(me)
T = C.tris(me)
E = C.edges(me)
g = names.index
# armpit / lat / deltoid region per side (metrics only): vertices carrying both arm-chain and torso weight, + 2 rings
def region(side):
    a = W[:, [g(side + 'Arm'), g(side + 'ForeArm')]].sum(1)
    t = W[:, [g('Spine'), g('Spine1'), g('Spine2'), g(side + 'Shoulder')]].sum(1)
    m = (a > 0.08) & (t > 0.08)
    for _ in range(2):
        mm = m.copy(); mm[E[m[E[:, 0]], 1]] = True; mm[E[m[E[:, 1]], 0]] = True; m = mm
    return m
VREG = {s: region(s) for s in ('Left', 'Right')}
TREG = {s: VREG[s][T].all(1) for s in VREG}
EREG = {s: VREG[s][E].all(1) for s in VREG}
print('REGION tris L %d R %d' % (TREG['Left'].sum(), TREG['Right'].sum()))
L0 = np.linalg.norm(rest[E[:, 0]] - rest[E[:, 1]], axis=1)
# triangle adjacency for geometric creases (two neighbouring triangles facing opposite ways: dot of normals < -0.3)
_e = np.sort(np.concatenate([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]]), 1); _t = np.tile(np.arange(len(T)), 3)
_o = np.lexsort((_e[:, 1], _e[:, 0])); _e, _t = _e[_o], _t[_o]; _s = (_e[1:] == _e[:-1]).all(1)
TA = np.stack([_t[:-1][_s], _t[1:][_s]], 1)
TAREG = {s: TREG[s][TA].all(1) for s in TREG}
TW = W[T].sum(1); tdom = TW.argmax(1)

def tri_n(co):
    n = np.cross(co[T[:, 1]] - co[T[:, 0]], co[T[:, 2]] - co[T[:, 0]])
    return n / np.maximum(1e-12, np.linalg.norm(n, axis=1, keepdims=True))
N0 = tri_n(rest)
# per-triangle bind frame for the deformation gradient (in-plane singular values = texture stretch proxy)
def tri_frame(co):
    e1 = co[T[:, 1]] - co[T[:, 0]]; e2 = co[T[:, 2]] - co[T[:, 0]]
    u = e1 / np.maximum(1e-12, np.linalg.norm(e1, axis=1, keepdims=True))
    n = np.cross(e1, e2); n /= np.maximum(1e-12, np.linalg.norm(n, axis=1, keepdims=True)); v = np.cross(n, u)
    return np.stack([np.stack([(e1 * u).sum(1), (e1 * v).sum(1)], 1), np.stack([(e2 * u).sum(1), (e2 * v).sum(1)], 1)], 2)  # (T,2,2) cols e1,e2
B0 = tri_frame(rest); B0inv = np.linalg.inv(B0 + np.eye(2) * 1e-12)

def bone_def(n):
    pb = arm.pose.bones[n]; b = arm.data.bones[n]
    return np.array((arm.matrix_world @ pb.matrix @ b.matrix_local.inverted() @ arm.matrix_world.inverted()).to_3x3())

def drive(f=None):
    w = {} if ZERO else K.weights(arm)
    for n, kb in keys.items(): kb.value = w.get(n, 0.0)
    return w

def measure():
    co = C.eval_co(me)
    R = np.stack([bone_def(n) for n in names])
    Ne = np.einsum('tij,tj->ti', R[tdom], N0); Ne /= np.maximum(1e-12, np.linalg.norm(Ne, axis=1, keepdims=True))
    nn = tri_n(co); dot = (nn * Ne).sum(1); cr = (nn[TA[:, 0]] * nn[TA[:, 1]]).sum(1)
    sv = np.linalg.svd(np.einsum('tij,tjk->tik', tri_frame(co), B0inv), compute_uv=False)  # (T,2): s1 >= s2
    r = np.linalg.norm(co[E[:, 0]] - co[E[:, 1]], axis=1) / np.maximum(1e-9, L0)
    s = {}
    for side in ('Left', 'Right'):
        m = TREG[side]; em = EREG[side]; k = side[0]
        s[k] = dict(crease=int((cr[TAREG[side]] < -0.3).sum()), folded=int((dot[m] < 0).sum()), sheared=int((dot[m] < 0.5).sum()),
                    stretch_gt1_5=int((sv[m, 0] > 1.5).sum()), stretch_gt2=int((sv[m, 0] > 2.0).sum()),
                    aniso_gt2=int((sv[m, 0] / np.maximum(1e-9, sv[m, 1]) > 2.0).sum()),
                    compress_lt0_6=int((sv[m, 1] < 0.6).sum()), s1_p99=float(np.percentile(sv[m, 0], 99)), s1_max=float(sv[m, 0].max()),
                    edge_max=float(r[em].max()), area_ratio_min=float((sv[m, 0] * sv[m, 1]).min()))
    return s, co

def bpos(n): return np.array(arm.matrix_world @ arm.pose.bones[n].head)
def fr(a): return int(round(a.frame_range[0])), int(round(a.frame_range[1]))

if FRAMES_IN:
    poses = json.load(open(FRAMES_IN))
else:
    ct = C.clip_times(); poses = []
    def scan(clip, key, lim=None):
        a = acts[clip]; C.assign(arm, a); f0, f1 = fr(a); vals = []
        for f in range(f0, (lim or f1) + 1): sc.frame_set(f); vals.append((key(), f))
        return vals
    hz = lambda: max(bpos('LeftHand')[2], bpos('RightHand')[2])
    side_hi = lambda: 'Left' if K.elevation(arm, 'Left') >= K.elevation(arm, 'Right') else 'Right'
    def add(name, clip, f):
        C.assign(arm, acts[clip]); sc.frame_set(f); poses.append((name, clip, f, side_hi()))
    add('Lift_overhead', 'Lift', max(scan('Lift', hz))[1])
    a = acts['Smash']; fh = fr(a)[0] + round(ct.get('Smash', {}).get('hit', 1.17) * 30)
    add('Smash_overhead', 'Smash', max(scan('Smash', hz, fh - 1))[1])
    add('Uppercut_extended', 'Uppercut', max(scan('Uppercut', hz))[1])
    a = acts['Clap']; fh = fr(a)[0] + round(ct.get('Clap', {}).get('hit', 0.7) * 30)
    add('Clap_wide', 'Clap', max(scan('Clap', lambda: np.linalg.norm(bpos('LeftHand') - bpos('RightHand')), fh - 1))[1])
    add('Throw_windup', 'Throw', max(scan('Throw', hz))[1])
    add('WallAttach_overhead', 'WallAttach', max(scan('WallAttach', hz))[1])
    add('Idle', 'Idle', 60)
    json.dump(poses, open(os.path.join(OUT, 'frames.json'), 'w'), indent=0)

stats = {}
for pname, clip, f, side in poses:
    C.assign(arm, acts[clip]); sc.frame_set(f); w = drive(); bpy.context.view_layer.update()
    s, _ = measure(); s['frame'] = f; s['side'] = side; s['elev'] = [K.elevation(arm, 'Left'), K.elevation(arm, 'Right')]; s['w'] = w
    stats[pname] = s
    print('%-20s f%3d elev L%5.1f R%5.1f w %s  L crease %3d R crease %3d | L fold %3d shear %3d s1>1.5 %3d s1>2 %3d p99 %.2f max %.2f | R fold %3d shear %3d s1>1.5 %3d s1>2 %3d p99 %.2f max %.2f' % (
        pname, f, s['elev'][0], s['elev'][1], {k: round(v, 2) for k, v in w.items()}, s['L']['crease'], s['R']['crease'],
        s['L']['folded'], s['L']['sheared'], s['L']['stretch_gt1_5'], s['L']['stretch_gt2'], s['L']['s1_p99'], s['L']['s1_max'],
        s['R']['folded'], s['R']['sheared'], s['R']['stretch_gt1_5'], s['R']['stretch_gt2'], s['R']['s1_p99'], s['R']['s1_max']))
# aggregate over every frame of the arm-raising clips (+ Idle/Walk as controls)
agg = {}
for clip in (os.environ.get('CORR_AGG', 'Lift,Smash,Throw,Uppercut,WallAttach,Clap,Land,Jump,PunchR,Slap,Run,Idle,Walk').split(',') if os.environ.get('CORR_AGG', 'x') else []):
    a = acts[clip]; C.assign(arm, a); f0, f1 = fr(a); acc = dict(frames=0, crease=0, folded=0, sheared=0, stretch_gt1_5=0, stretch_gt2=0, aniso_gt2=0, compress_lt0_6=0, s1_max=0.0)
    for f in range(f0, f1 + 1, 2):
        sc.frame_set(f); drive(); bpy.context.view_layer.update(); s, _ = measure(); acc['frames'] += 1
        for k in ('L', 'R'):
            for q in ('crease', 'folded', 'sheared', 'stretch_gt1_5', 'stretch_gt2', 'aniso_gt2', 'compress_lt0_6'): acc[q] += s[k][q]
            acc['s1_max'] = max(acc['s1_max'], s[k]['s1_max'])
    agg[clip] = acc
    print('AGG %-10s %s' % (clip, {k: (round(v / acc['frames'], 1) if k not in ('frames', 's1_max') else round(v, 2)) for k, v in acc.items()}))
stats['_agg'] = agg
json.dump(stats, open(os.path.join(OUT, 'stats.json'), 'w'), indent=1)
if NORENDER: sys.exit(0)

# ---------- render (same look as mesh_poses.py)
sc.render.engine = 'BLENDER_EEVEE' if 'BLENDER_EEVEE' in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE_NEXT'
sc.render.resolution_x = RES; sc.render.resolution_y = RES
sc.view_settings.view_transform = 'AgX'
try: sc.eevee.taa_render_samples = 32
except Exception: pass
wd = bpy.data.worlds.new('w'); sc.world = wd; wd.use_nodes = True
wd.node_tree.nodes['Background'].inputs[0].default_value = (0.32, 0.33, 0.36, 1); wd.node_tree.nodes['Background'].inputs[1].default_value = 0.6
def light(name, loc, energy, size, color=(1, 1, 1)):
    l = bpy.data.lights.new(name, 'AREA'); l.energy = energy; l.color = color; l.size = size
    o = bpy.data.objects.new(name, l); sc.collection.objects.link(o); o.location = loc
    o.rotation_euler = (Vector((0, 0, 0.1)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); return o
lrig = bpy.data.objects.new('lrig', None); sc.collection.objects.link(lrig)
for lo_ in (light('key', (3.0, -2.2, 2.6), 450, 2.5), light('fill', (2.5, 3.0, 1.0), 180, 3.0, (0.9, 0.95, 1.0)),
            light('rim', (-3.0, 0.5, 2.8), 400, 2.0, (1.0, 0.97, 0.9)), light('under', (0.5, 0.0, -2.0), 120, 3.0)):
    lo_.parent = lrig
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam; cam.data.lens = 50

def shoot(path, view, side):
    co = C.eval_co(me)
    hip = bone_def('Hips') @ np.array([1.0, 0, 0]); fa = math.atan2(hip[1], hip[0])
    lrig.rotation_euler = (0, 0, fa); lrig.location = (co[:, 0].mean(), co[:, 1].mean(), 0)
    # armpit centre: between the shoulder joint and the upper chest side, a bit down the arm
    pa, pf, ps = bpos(side + 'Arm'), bpos(side + 'ForeArm'), bpos('Spine2')
    ctr = 0.55 * pa + 0.15 * pf + 0.30 * ps
    lat = pa - ps; lat -= np.dot(lat, [0, 0, 1]) * np.array([0, 0, 1.0])
    la = math.atan2(lat[1], lat[0])
    # side = from the arm's side, swung 35 deg towards the front, slightly below (looking up into the armpit)
    sgn = 1 if math.sin(la - fa) > 0 else -1
    ang = {'front': fa, 'back': fa + math.pi, 'side': la - sgn * math.radians(35)}[view]
    dz = {'front': 0.05, 'back': 0.05, 'side': -0.12}[view]
    d = np.array([math.cos(ang), math.sin(ang), dz]); d /= np.linalg.norm(d)
    ext = (rest[:, 2].max() - rest[:, 2].min()) * 0.30
    dist = ext / (2 * math.tan(cam.data.angle_y / 2)) + 0.2
    cam.location = Vector((ctr + d * dist).tolist()); cam.rotation_euler = (Vector(ctr.tolist()) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    cam.data.clip_start = 0.01
    sc.render.filepath = path; bpy.ops.render.render(write_still=True)

for pname, clip, f, side in poses:
    C.assign(arm, acts[clip]); sc.frame_set(f); drive(); bpy.context.view_layer.update()
    for v in VIEWS: shoot(os.path.join(OUT, '%s_%s.png' % (pname, v)), v, side)
print('DONE', OUT)
