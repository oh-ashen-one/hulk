# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
# Splice a fresh retargeted take onto the last pose of another clip (owner 2026-10-16: the Throw must start from the Lift clip's
# overhead hold, and the old Throw was soft). Builds a new clip from the take through a time map, cross-fades its first frames from
# the previous clip's end pose (per-bone world rotation slerp + hips position), and clamps the torso pitch (the generated hurl folds
# the Brute head-to-the-floor). Writes a GLB like retarget_motion.py (target armature + mesh + one NLA track) for assemble_motion.py.
# usage: Blender -b --factory-startup -P tools/brute/throw_splice.py -- <prev.glb> <prev_frame> <take_rt.glb> <out.glb> <ClipName> <map>
#   <prev_frame>: absolute action frame of the pose to start from (Brute_liftthrow.glb: Lift ends at TRIM offset 109 = frame 110)
#   <map>: comma list of out_frame:src_frame[:b] keys (absolute take frames); between two keys the take plays linearly, or with
#          ':b' on the later key the segment is a pose blend (smoothstep) from the earlier key's pose to the later key's pose.
#   env SPLICE_IN=frames of cross-fade from the previous pose (default 6), SPLICE_MAXPITCH=deg forward torso pitch clamp (default 70)
# 2026-10-16 Throw: take 01a1481b-ebf1-74b6-9dc4-f1082afe1341 (throwA, BRUTE_LEG_SPREAD=7 BRUTE_FIST=0), SPLICE_MAXPITCH=55,
#   map 0:24,10:30,15:35,22:35.7,44:75:b (lean-back load, whip, follow-through hold, pose blend up to the take's final stand)
import bpy, sys, os, math
from mathutils import Vector, Quaternion

a = sys.argv[sys.argv.index('--') + 1:]
PREV, PFR, TAKE, OUT, NAME, MAP = a[0], float(a[1]), a[2], a[3], a[4], a[5]
NIN = int(os.environ.get('SPLICE_IN', '6')); MAXP = float(os.environ.get('SPLICE_MAXPITCH', '70'))
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; sc.render.fps = 30
def imp(f):
    before = set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=f)
    new = [o for o in bpy.data.objects if o not in before]
    arm = next(o for o in new if o.type == 'ARMATURE')
    act = arm.animation_data.nla_tracks[0].strips[0].action
    for t in list(arm.animation_data.nla_tracks): arm.animation_data.nla_tracks.remove(t)
    arm.animation_data.action = act
    if hasattr(act, 'slots') and len(act.slots): arm.animation_data.action_slot = act.slots[0]
    return new, arm, act
pobjs, parm, pact = imp(PREV)
tobjs, arm, tact = imp(TAKE)
W = arm.matrix_world; Wqi = W.to_quaternion().inverted()
def depth(b): return len(b.parent_recursive)
order = sorted(arm.data.bones, key=depth)
RQ = {b.name: (W @ b.matrix_local).to_quaternion() for b in arm.data.bones}
RH = {b.name: W @ b.head_local for b in arm.data.bones}
tR = {b.name: b.matrix_local.to_quaternion() for b in arm.data.bones}
PAR = {b.name: (b.parent.name if b.parent else None) for b in arm.data.bones}
ROOT = 'Hips'
def sample(ob, f):
    fi = int(math.floor(f)); sc.frame_set(fi, subframe=f - fi)
    return ({b.name: (ob.matrix_world @ ob.pose.bones[b.name].matrix).to_quaternion() for b in order},
            ob.matrix_world @ ob.pose.bones[ROOT].head)
def fk(world, rh):
    pos = {}
    for b in order:
        p = PAR[b.name]
        pos[b.name] = rh.copy() if p is None else pos[p] + (world[p] @ RQ[p].inverted()) @ (RH[b.name] - RH[p])
    return pos
def rebuild(ws, over):
    out = {}
    for b in order:
        n = b.name; p = PAR[n]
        out[n] = over[n] if n in over else (ws[n] if p is None else out[p] @ (ws[p].inverted() @ ws[n]))
    return out
def smooth(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)
def blend(A, B, w):
    return {n: A[0][n].slerp(B[0][n], w) for n in A[0]}, A[1].lerp(B[1], w)

prev_pose = sample(parm, PFR)
for o in pobjs: bpy.data.objects.remove(o)
keys = []
for tok in MAP.split(','):
    p = tok.split(':'); keys.append((int(p[0]), float(p[1]), len(p) > 2 and p[2] == 'b'))
N = keys[-1][0]
UP = Vector((0, 0, 1))
def heading_axes(world, rh):
    pos = fk(world, rh); lat = pos['RightUpLeg'] - pos['LeftUpLeg']; lat.z = 0; lat.normalize()
    return lat, UP.cross(lat)
def pitch(v, fwd): return math.degrees(math.atan2(v.dot(fwd), v.z))
plat, pfwd = heading_axes(*prev_pose); s0 = sample(arm, keys[0][1]); tlat, tfwd = heading_axes(*s0)
print('HEADING prev %.1f take@%.1f %.1f deg' % (math.degrees(math.atan2(pfwd.y, pfwd.x)), keys[0][1], math.degrees(math.atan2(tfwd.y, tfwd.x))))
# hips: keep the previous clip's position, then follow the take's motion relative to its first mapped frame
hip_off = prev_pose[1] - s0[1]; hip_off.z = 0
frames = []
for k in range(N + 1):
    i = max(j for j in range(len(keys)) if keys[j][0] <= k) if k < N else len(keys) - 2
    k0, f0, _ = keys[i]; k1, f1, b1 = keys[i + 1]
    t = (k - k0) / max(1, k1 - k0)
    if b1: ws, rh = blend(sample(arm, f0), sample(arm, f1), smooth(t))
    else: ws, rh = sample(arm, f0 + (f1 - f0) * t)
    ws = dict(ws); rh = rh + hip_off
    # torso pitch clamp (Spine -> Neck vs vertical, along the take's heading at this frame)
    lat, fwd = heading_axes(ws, rh); pos = fk(ws, rh)
    p_ = pitch(pos['Neck'] - pos['Spine'], fwd)
    over = {}
    if p_ > MAXP:
        q = Quaternion(lat, math.radians(p_ - MAXP))
        if (q @ UP).dot(fwd) > 0: q = Quaternion(lat, -math.radians(p_ - MAXP))
        over['Spine'] = q @ ws['Spine']
        ws = rebuild(ws, over)
    if k < NIN:   # cross-fade from the previous clip's end pose
        w = smooth(k / NIN)
        ws, rh = blend(prev_pose, (ws, rh), w)
    frames.append((k, ws, rh))
    pz = fk(ws, rh)
    if k % 2 == 0 or k <= 2:
        print('F %2d src %.1f pitch %.0f%s  hands z %.2f fwd %.2f  hips z %.2f' % (k, f0 + (f1 - f0) * t if not b1 else -1, p_, ' CLAMP' if p_ > MAXP else '',
              (pz['LeftHand'].z + pz['RightHand'].z) / 2, ((pz['LeftHand'] + pz['RightHand']) / 2 - pz[ROOT]).dot(pfwd), pz[ROOT].z))

act = bpy.data.actions.new(NAME)
arm.animation_data.action = act
if hasattr(act, 'slots') and hasattr(arm.animation_data, 'action_slot') and len(act.slots): arm.animation_data.action_slot = act.slots[0]
sf0 = 1
for k, world, rh in frames:
    fr = sf0 + k
    for b in order:
        pb = arm.pose.bones[b.name]; pb.rotation_mode = 'QUATERNION'
        aq = Wqi @ world[b.name]
        if b.parent: basis = ((Wqi @ world[b.parent.name]) @ (tR[b.parent.name].inverted() @ tR[b.name])).inverted() @ aq
        else: basis = tR[b.name].inverted() @ aq
        pb.rotation_quaternion = basis; pb.keyframe_insert('rotation_quaternion', frame=fr)
    pr = arm.pose.bones[ROOT]; pr.location = tR[ROOT].inverted() @ (W.inverted().to_3x3() @ (rh - RH[ROOT])); pr.keyframe_insert('location', frame=fr)
for a_ in [a_ for a_ in bpy.data.actions if a_ != act]: bpy.data.actions.remove(a_)
arm.animation_data.action = None
trk = arm.animation_data.nla_tracks.new(); trk.name = NAME; st = trk.strips.new(NAME, sf0, act)
if hasattr(st, 'action_slot') and hasattr(act, 'slots') and len(act.slots): st.action_slot = act.slots[0]
for o in bpy.data.objects: o.select_set(o.type in ('ARMATURE', 'MESH'))
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True, export_animations=True, export_animation_mode='NLA_TRACKS',
                          export_force_sampling=True, export_yup=True)
print('SPLICE', NAME, 'frames', N + 1, '->', OUT)
