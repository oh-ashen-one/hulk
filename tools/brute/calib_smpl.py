# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
# Calibrate a direct retarget from Meshy Text-to-Motion RAW clips (SMPL-H skeleton, motion_url FBX, free download) onto the
# Brute's Cartwheel rig, so new clips skip the Animation API "apply" step (3 credits each).
# Uses one clip that exists both ways: the raw SMPL FBX and the same motion after Meshy apply + retarget_motion.py (target rig).
# For every mapped bone the world-space offset C = smpl_world^-1 @ target_world is constant across frames (verified 0.0 deg on the
# climbA pair for all body bones); hands are not constant in the apply path (Meshy's 24-bone rig drops the wrist), so the hand
# offset is derived from the forearm offset + both rests (wrist at its rest relation to the elbow -> hand at rest to the forearm).
# Hips: target hip height = a * smpl pelvis height + b, horizontal travel scaled by a (least squares over the frames).
# usage: Blender -b --factory-startup -P tools/brute/calib_smpl.py -- <raw_smpl.fbx> <same_clip_retargeted.glb> <out_calib.json>
import bpy, sys, math, json, os

RAW, RT, OUT = sys.argv[sys.argv.index('--') + 1:][:3]
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; sc.render.fps = 30

def imp(f):
    b = set(bpy.data.objects)
    if f.lower().endswith('.fbx'): bpy.ops.import_scene.fbx(filepath=f)
    else: bpy.ops.import_scene.gltf(filepath=f)
    return next(o for o in bpy.data.objects if o not in b and o.type == 'ARMATURE')
s = imp(RAW); t = imp(RT)
if t.animation_data and not t.animation_data.action and t.animation_data.nla_tracks:
    t.animation_data.action = t.animation_data.nla_tracks[0].strips[0].action
MAP = {'Hips': 'Pelvis', 'Spine': 'Spine1', 'Spine1': 'Spine2', 'Spine2': 'Spine3', 'Neck': 'Neck', 'Head': 'Head'}
for side, S in (('Left', 'L'), ('Right', 'R')):
    MAP.update({side + 'Shoulder': S + '_Collar', side + 'Arm': S + '_Shoulder', side + 'ForeArm': S + '_Elbow', side + 'Hand': S + '_Wrist',
                side + 'UpLeg': S + '_Hip', side + 'Leg': S + '_Knee', side + 'Foot': S + '_Ankle', side + 'ToeBase': S + '_Foot'})
OFF = 1   # raw FBX starts at frame 1, the retargeted GLB at frame 0
def wq(arm, b): return (arm.matrix_world @ arm.pose.bones[b].matrix).to_quaternion()
def rq(arm, b): return (arm.matrix_world @ arm.data.bones[b].matrix_local).to_quaternion()
C, dev = {}, {}
frames = list(range(0, int(t.animation_data.action.frame_range[1]) - 2, 3))
for tb, sb in MAP.items():
    qs = []
    for k in frames:
        sc.frame_set(k + OFF); a = wq(s, sb)
        sc.frame_set(k); b = wq(t, tb)
        qs.append(a.inverted() @ b)
    m = qs[len(qs) // 2]
    d = max(math.degrees(min(m.rotation_difference(q).angle, 2 * math.pi - m.rotation_difference(q).angle)) for q in qs)
    C[tb] = list(m); dev[tb] = round(d, 2)
from mathutils import Quaternion
# Refinement: the climbA chain (Meshy apply -> rest-delta retarget) carries constant per-bone rest mismatches (head tipped ~44 deg,
# left arm ~34 deg off, feet pitched ~64 deg). Swing each bone so its segment (joint -> mapped child joint) points the same way
# as the SMPL segment; the twist about the segment is kept from the calibration. Ends (head, hands, toes) are derived from the
# refined parent assuming SMPL rest relation == target rest relation (head: relative to the chest).
def rp(arm, b): return arm.matrix_world @ arm.data.bones[b].head_local
SEGS = [('Hips', 'Spine'), ('Spine', 'Spine1'), ('Spine1', 'Spine2'), ('Spine2', 'Neck'), ('Neck', 'Head')]
for side in ('Left', 'Right'):
    SEGS += [(side + 'Shoulder', side + 'Arm'), (side + 'Arm', side + 'ForeArm'), (side + 'ForeArm', side + 'Hand'),
             (side + 'UpLeg', side + 'Leg'), (side + 'Leg', side + 'Foot'), (side + 'Foot', side + 'ToeBase')]
seg_err = {}
# Axial bones also carry a TWIST error from the chain (the Brute's bind pose faces +X, the clips -Y: pelvis came out ~80-90 deg
# yawed against the legs, chest ~25-40 deg). They get a full two-vector alignment instead: up = own segment, lateral = hip line
# (Hips, Spine), mean of hip + collar lines (Spine1), collar line (Spine2, Neck), each expressed in the bone's local rest frame.
from mathutils import Matrix
def frame(up, lat):
    up = up.normalized(); lat = (lat - lat.dot(up) * up).normalized(); f = up.cross(lat)
    return Matrix((lat, up, f)).transposed()   # columns: lat, up, fwd
def lat_s(kind):
    hip = (rp(s, 'R_Hip') - rp(s, 'L_Hip')).normalized(); col = (rp(s, 'R_Collar') - rp(s, 'L_Collar')).normalized()
    return {'hip': hip, 'col': col, 'mix': (hip + col).normalized()}[kind]
def lat_t(kind):
    hip = (rp(t, 'RightUpLeg') - rp(t, 'LeftUpLeg')).normalized(); col = (rp(t, 'RightShoulder') - rp(t, 'LeftShoulder')).normalized()
    return {'hip': hip, 'col': col, 'mix': (hip + col).normalized()}[kind]
AXIAL = {'Hips': 'hip', 'Spine': 'hip', 'Spine1': 'mix', 'Spine2': 'col', 'Neck': 'col'}
if os.environ.get('BRUTE_CALIB_REFINE', '1') == '1':
    for b, c in SEGS:
        if b in AXIAL:
            qs, qt = rq(s, MAP[b]), rq(t, b)
            Fs = frame(qs.inverted() @ (rp(s, MAP[c]) - rp(s, MAP[b])), qs.inverted() @ lat_s(AXIAL[b]))
            Ft = frame(qt.inverted() @ (rp(t, c) - rp(t, b)), qt.inverted() @ lat_t(AXIAL[b]))
            Cn = (Fs @ Ft.transposed()).to_quaternion()
            seg_err[b] = 'axial %.1f' % math.degrees(Quaternion(C[b]).rotation_difference(Cn).angle)
            C[b] = list(Cn); continue
        Cb = Quaternion(C[b])
        ds = rq(s, MAP[b]).inverted() @ (rp(s, MAP[c]) - rp(s, MAP[b])).normalized()   # SMPL segment, in the SMPL bone frame
        dt = rq(t, b).inverted() @ (rp(t, c) - rp(t, b)).normalized()                 # target segment, in the target bone frame
        want = Cb.inverted() @ ds
        seg_err[b] = round(math.degrees(dt.angle(want)), 1)
        C[b] = list(Cb @ dt.rotation_difference(want))
def derive(child, parent):
    cp = Quaternion(C[parent])
    return list(rq(s, MAP[child]).inverted() @ rq(s, MAP[parent]) @ cp @ rq(t, parent).inverted() @ rq(t, child))
for side, S in (('Left', 'L'), ('Right', 'R')):
    C[side + 'Hand'] = derive(side + 'Hand', side + 'ForeArm'); dev[side + 'Hand'] = 'derived'
    if seg_err: C[side + 'ToeBase'] = derive(side + 'ToeBase', side + 'Foot'); dev[side + 'ToeBase'] = 'derived'
# head: relative to the CHEST rest (the Brute's rest neck is hunched forward; relative to the swung neck the face tips up)
if seg_err: C['Head'] = derive('Head', 'Spine2'); dev['Head'] = 'derived from chest'
print('CALIB segment swing (deg)', seg_err)
# hips: least squares t = a*s + b on height, then horizontal ratio
xs, ys, hs, ht = [], [], [], []
for k in frames:
    sc.frame_set(k + OFF); ps = s.matrix_world @ s.pose.bones['Pelvis'].head
    sc.frame_set(k); pt = t.matrix_world @ t.pose.bones['Hips'].head
    hs.append(ps.copy()); ht.append(pt.copy())
n = len(hs); mz = sum(p.z for p in hs) / n; mtz = sum(p.z for p in ht) / n
var = sum((p.z - mz) ** 2 for p in hs)
a = sum((hs[i].z - mz) * (ht[i].z - mtz) for i in range(n)) / max(1e-9, var); b = mtz - a * mz
dh = [((hs[i] - hs[0]).xy.length, (ht[i] - ht[0]).xy.length) for i in range(n)]
ah = sum(x * y for x, y in dh) / max(1e-9, sum(x * x for x, y in dh))
res = max(abs(a * hs[i].z + b - ht[i].z) for i in range(n))
json.dump(dict(map=MAP, C=C, seg_swing_deg=seg_err, hip_a=a, hip_b=b, hip_h=ah, hip_resid=res, dev_deg=dev,
               target_world=[list(r) for r in t.matrix_world], src_world=[list(r) for r in s.matrix_world]), open(OUT, 'w'), indent=1)
print('CALIB dev', dev); print('CALIB hips a %.4f b %.4f horiz %.4f resid %.4f' % (a, b, ah, res)); print('WROTE', OUT)
