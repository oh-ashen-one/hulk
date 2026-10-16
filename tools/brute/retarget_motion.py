# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
# Retarget a motion clip from another humanoid skeleton (Meshy Text-to-Motion retarget, Mixamo-style names) onto the Brute's
# Cartwheel rig, in Blender. World-space rotation deltas per bone (source pose x source rest^-1, applied on the target rest),
# hips translation scaled by the hip-height ratio; unmapped bones (fingers) keep their rest relation.
# Writes a GLB with the target armature + mesh + one action named after the clip, which assemble_motion.py picks up.
# Also accepts the RAW Text-to-Motion FBX (SMPL-H skeleton, free download via meshy_motion.py motion ... out.fbx): calibrated offsets
# from tools/brute/calib_smpl.py (env BRUTE_SMPL_CALIB, default ~/hulk-scratch/meshy/attacks/smpl_calib.json).
# usage: Blender -b --factory-startup -P tools/brute/retarget_motion.py -- <target_rig.glb> <source_motion.glb|.fbx> <out.glb> <ClipName>
import bpy, sys, re
from mathutils import Matrix, Quaternion, Vector

TGT, SRC, OUT, NAME = sys.argv[sys.argv.index('--') + 1:][:4]
import os
FIST = os.environ.get('BRUTE_FIST', '1') == '1'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.render.fps = 30

def imp(f):
    before = set(bpy.data.objects)
    if f.lower().endswith('.fbx'): bpy.ops.import_scene.fbx(filepath=f)
    else: bpy.ops.import_scene.gltf(filepath=f)
    new = [o for o in bpy.data.objects if o not in before]
    for o in [o for o in new if o.type == 'MESH' and not any(m.type == 'ARMATURE' for m in o.modifiers)]: new.remove(o); bpy.data.objects.remove(o)
    return new
tobjs = imp(TGT); tarm = next(o for o in tobjs if o.type == 'ARMATURE')
if tarm.animation_data:
    for t in list(tarm.animation_data.nla_tracks): tarm.animation_data.nla_tracks.remove(t)
    tarm.animation_data.action = None
for pb in tarm.pose.bones: pb.matrix_basis.identity()
for a in list(bpy.data.actions): bpy.data.actions.remove(a)
sobjs = imp(SRC); sarm = next(o for o in sobjs if o.type == 'ARMATURE')
for o in [o for o in sobjs if o.type == 'MESH']: bpy.data.objects.remove(o)
sact = sarm.animation_data.action
f0, f1 = (int(round(x)) for x in sact.frame_range)

def norm(n): return re.sub(r'[^a-z0-9]', '', n.lower())
SB = {norm(b.name): b.name for b in sarm.data.bones}
ALIAS = {'spine': ['spine02', 'spine'], 'spine1': ['spine01', 'spine1'], 'spine2': ['spine', 'spine2', 'chest'], 'neck': ['neck'], 'head': ['head']}
spine_src = [b.name for b in sarm.data.bones if re.fullmatch(r'spine\d*', norm(b.name))]
# order the source spine chain from the hips up
def depth(b): return len(b.parent_recursive)
spine_src.sort(key=lambda n: depth(sarm.data.bones[n]))
spine_tgt = sorted([b.name for b in tarm.data.bones if re.fullmatch(r'spine\d*', norm(b.name))], key=lambda n: depth(tarm.data.bones[n]))
MAP = {}
for i, t in enumerate(spine_tgt):
    if spine_src: MAP[t] = spine_src[min(i, len(spine_src) - 1)] if len(spine_tgt) <= len(spine_src) else spine_src[min(len(spine_src) - 1, round(i * (len(spine_src) - 1) / max(1, len(spine_tgt) - 1)))]
for b in tarm.data.bones:
    if b.name in MAP: continue
    n = norm(b.name)
    if n in SB and not n.startswith('spine'): MAP[b.name] = SB[n]
SMPL = 'Pelvis' in sarm.data.bones and 'L_Hip' in sarm.data.bones
if SMPL:
    # raw Meshy Text-to-Motion clip (SMPL-H skeleton, the free motion_url FBX): use the calibrated per-bone world offsets
    # (tools/brute/calib_smpl.py) instead of the rest-pose delta -- the SMPL rest is a T-pose, the Brute's bind pose is not.
    import json
    CAL = json.load(open(os.path.expanduser(os.environ.get('BRUTE_SMPL_CALIB', '~/hulk-scratch/meshy/attacks/smpl_calib.json'))))
    MAP = dict(CAL['map']); CQ = {k: Quaternion(v) for k, v in CAL['C'].items()}
print('MAP', 'SMPL' if SMPL else '', MAP)

ROOT = 'Hips'
sW, tW = sarm.matrix_world, tarm.matrix_world
s_rest = {b.name: (sW @ b.matrix_local).to_quaternion() for b in sarm.data.bones}
t_rest = {b.name: (tW @ b.matrix_local).to_quaternion() for b in tarm.data.bones}
tR = {b.name: b.matrix_local.to_quaternion() for b in tarm.data.bones}   # armature-space rest rotations
hip_ratio = CAL['hip_a'] if SMPL else (tW @ tarm.data.bones[ROOT].head_local).z / max(1e-3, (sW @ sarm.data.bones[ROOT].head_local).z)
s_hip0 = None
order = sorted(tarm.data.bones, key=depth)
act = bpy.data.actions.new(NAME); tarm.animation_data_create(); tarm.animation_data.action = act
tWq_inv = tW.to_quaternion().inverted()
# env BRUTE_YAW_DAMP=k (0..1): remove k x the pelvis heading change from pelvis + upper body (feet stay planted);
# BRUTE_YAW_LOCK=1: remove ALL heading change from the whole body (+ root travel), so the clip ends facing where it started.
import math
YAW_LOCK = os.environ.get('BRUTE_YAW_LOCK', '0') == '1'
YAW_K = 1.0 if YAW_LOCK else float(os.environ.get('BRUTE_YAW_DAMP', '0'))
LEGS = re.compile(r'(UpLeg|Leg|Foot|ToeBase)$')
LAT_REST = ((tW @ tarm.data.bones['RightUpLeg'].head_local) - (tW @ tarm.data.bones['LeftUpLeg'].head_local)).normalized()
yaw_prev, yaw_rel = None, 0.0
SPREAD = math.radians(float(os.environ.get('BRUTE_LEG_SPREAD', '0')))   # env BRUTE_LEG_SPREAD=deg: wider brute stance
GROUND = SMPL and os.environ.get('BRUTE_GROUND', '1') == '1'
_ap = os.environ.get('BRUTE_ARM_PITCH', '')   # 'deg,a,b,c,d': lower both arms by deg, ramp a->b, hold to c, ramp out by d (frames)
ARM_PITCH = math.radians(float(_ap.split(',')[0])) if _ap else 0
AP_WIN = [int(x) for x in _ap.split(',')[1:5]] if _ap else None
ARM_SET = [b.name for a in ('LeftArm', 'RightArm') for b in [tarm.data.bones[a]] + list(tarm.data.bones[a].children_recursive)]
Z_OFF = float(os.environ.get('BRUTE_Z_OFFSET', '0'))   # constant hips lift (airborne loops: keep the feet off the viewer floor)
if GROUND:
    SF = ['L_Foot', 'R_Foot', 'L_Ankle', 'R_Ankle']; TF = ['LeftFoot', 'RightFoot', 'LeftToeBase', 'RightToeBase']
    t_rest_low = {b: (tW @ tarm.data.bones[b].head_local).z for b in TF}
    s_rest_low = {b: (sW @ sarm.data.bones[b].head_local).z for b in SF}
    FLOOR = min((m.matrix_world @ v.co).z for m in tobjs if m.type == 'MESH' for v in m.data.vertices)
    # joint margins above the floor (target units ~ m): wrist (the Brute's fist is ~0.27 deep), head, knee (kneeling)
    KEEP_UP = {'LeftHand': 0.27, 'RightHand': 0.27, 'Head': 0.3, 'LeftLeg': 0.08, 'RightLeg': 0.08}
    g_raise = []
REST_H = {b.name: tW @ b.head_local for b in tarm.data.bones}
def fk(world, d_world):
    pos = {}
    for b in order:
        if b.parent is None: pos[b.name] = REST_H[b.name] + d_world
        else:
            p = b.parent.name
            pos[b.name] = pos[p] + (world[p] @ t_rest[p].inverted()) @ (REST_H[b.name] - REST_H[p])
    return pos
for fr in range(f0, f1 + 1):
    bpy.context.scene.frame_set(fr)
    world = {}
    for b in order:
        sname = MAP.get(b.name)
        if sname:
            sq = (sW @ sarm.pose.bones[sname].matrix).to_quaternion()
            world[b.name] = (sq @ CQ[b.name]) if SMPL else (sq @ s_rest[sname].inverted()) @ t_rest[b.name]
        else:
            p = b.parent
            world[b.name] = (world[p.name] @ t_rest[p.name].inverted() @ t_rest[b.name]) if p else t_rest[b.name]
    if YAW_K:
        # pelvis heading (hip line) relative to the first frame, unwrapped; take YAW_K of it out of the body (legs keep theirs
        # unless YAW_LOCK, so planted feet stay planted while the over-rotated torso/pelvis turns less)
        lat = world[ROOT] @ t_rest[ROOT].inverted() @ LAT_REST
        yaw = math.atan2(lat.y, lat.x)
        if yaw_prev is None: yaw_prev, yaw_rel = yaw, 0.0
        yaw_rel += (yaw - yaw_prev + math.pi) % (2 * math.pi) - math.pi; yaw_prev = yaw
        Yq = Quaternion((0, 0, 1), -YAW_K * yaw_rel)
        for n in world:
            if YAW_LOCK or not LEGS.search(n): world[n] = Yq @ world[n]
    if ARM_PITCH:
        # lower (or raise) both arms together about the shoulder line in a frame window -- e.g. the generated clap meets at face
        # height; pitching both arms about the same lateral axis keeps the hands together and moves the contact to the chest
        k_ = fr - f0; a_, b_, c_, d_ = AP_WIN
        w_ = 0 if k_ <= a_ or k_ >= d_ else 1 if b_ <= k_ <= c_ else ((k_ - a_) / max(1, b_ - a_) if k_ < b_ else (d_ - k_) / max(1, d_ - c_))
        w_ = w_ * w_ * (3 - 2 * w_)
        if w_ > 0:
            p_ = fk(world, Vector())
            lat_ = (p_['RightArm'] - p_['LeftArm']).normalized()
            v_ = (p_['LeftHand'] + p_['RightHand']) / 2 - (p_['LeftArm'] + p_['RightArm']) / 2
            q_ = Quaternion(lat_, ARM_PITCH * w_)
            if (q_ @ v_).z > v_.z: q_ = Quaternion(lat_, -ARM_PITCH * w_)
            for n in ARM_SET: world[n] = q_ @ world[n]
    if SPREAD:
        # widen the stance: swing each whole leg (thigh + shin) outward about the pelvis forward axis; feet keep their world
        # rotation, so they stay flat
        lat = (world[ROOT] @ t_rest[ROOT].inverted() @ LAT_REST); lat.z = 0; lat.normalize()   # left -> right
        fwd = Vector((0, 0, 1)).cross(lat)
        for side, out in (('Left', -lat), ('Right', lat)):
            q = Quaternion(fwd, SPREAD)
            if (q @ Vector((0, 0, -1))).dot(out) < 0: q = Quaternion(fwd, -SPREAD)
            for n in (side + 'UpLeg', side + 'Leg'): world[n] = q @ world[n]
    # hips translation (world delta from the source's first frame, scaled), into the root bone's rest frame
    sh = sW @ sarm.pose.bones[MAP[ROOT] if SMPL else ROOT].head
    if s_hip0 is None: s_hip0 = sh.copy()
    if SMPL:
        d_world = (sh - s_hip0) * CAL['hip_h']
        d_world.z = CAL['hip_a'] * sh.z + CAL['hip_b'] - (tW @ tarm.data.bones[ROOT].head_local).z
    else:
        d_world = (sh - s_hip0) * hip_ratio
        d_world.z = (sh.z - (sW @ sarm.data.bones[ROOT].head_local).z) * hip_ratio
    if YAW_K and YAW_LOCK: d_world.xy = (Yq @ Vector((d_world.x, d_world.y, 0))).xy
    d_world.z += Z_OFF
    if GROUND:
        # 1) feet: lowest target foot joint at (source foot clearance x scale) above its rest height (the Brute's legs are shorter
        #    than the hip-height ratio assumes; jumps survive). 2) nothing else through the floor: if a wrist / head / knee would
        #    sink below its margin, raise the hips and re-solve both legs (2-bone IK, same knee plane) so the feet stay planted.
        clear = min((sW @ sarm.pose.bones[b].head).z - s_rest_low[b] for b in SF) * CAL['hip_a']
        pos = fk(world, d_world)
        d_world.z += clear - min(pos[b].z - t_rest_low[b] for b in TF)
        pos = fk(world, d_world)
        need = max(m - (pos[b].z - FLOOR) for b, m in KEEP_UP.items())
        if need > 0:
            raise_v = Vector((0, 0, need)); d_world += raise_v; g_raise.append(need)
            for side in ('Left', 'Right'):
                A = pos[side + 'UpLeg'] + raise_v; K = pos[side + 'Leg']; T = pos[side + 'Foot']
                l1 = (K - pos[side + 'UpLeg']).length; l2 = (T - K).length
                dv = T - A; d = min(dv.length, (l1 + l2) * 0.999); u = dv.normalized()
                pole = (K - A) - (K - A).dot(u) * u
                pole = pole.normalized() if pole.length > 1e-6 else Vector((0, 0, 1)).cross(u).normalized()
                ca = max(-1.0, min(1.0, (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d)))
                K2 = A + l1 * (ca * u + math.sqrt(1 - ca * ca) * pole); T2 = A + u * d
                world[side + 'UpLeg'] = (K - pos[side + 'UpLeg']).rotation_difference(K2 - A) @ world[side + 'UpLeg']
                world[side + 'Leg'] = (T - K).rotation_difference(T2 - K2) @ world[side + 'Leg']
    for b in order:
        pb = tarm.pose.bones[b.name]; pb.rotation_mode = 'QUATERNION'
        arm_q = tWq_inv @ world[b.name]
        if b.parent:
            p_arm = tWq_inv @ world[b.parent.name]
            rest_rel = tR[b.parent.name].inverted() @ tR[b.name]
            basis = (p_arm @ rest_rel).inverted() @ arm_q
        else:
            basis = tR[b.name].inverted() @ arm_q
        if FIST and b.name not in MAP and re.search(r'(thumb|index|middle|ring|pinky)', b.name.lower()):
            # the source skeleton has no fingers: close the hands into fists (curl about the bone's local X)
            ang = (0.55 if 'thumb' in b.name.lower() else 1.0) * 1.35
            ax = {'X': (1, 0, 0), '-X': (-1, 0, 0), 'Z': (0, 0, 1), '-Z': (0, 0, -1)}[os.environ.get('BRUTE_FIST_AXIS', 'Z')]
            basis = Quaternion(ax, ang)
        pb.rotation_quaternion = basis
        pb.keyframe_insert('rotation_quaternion', frame=fr)
    d_arm = tW.inverted().to_3x3() @ d_world
    pr = tarm.pose.bones[ROOT]; pr.location = tR[ROOT].inverted() @ d_arm
    pr.keyframe_insert('location', frame=fr)
if GROUND: print('GROUND raised %d frames (max %.3f) to keep wrists/head/knees above the floor' % (len(g_raise), max(g_raise or [0])))
bpy.data.objects.remove(sarm)
for a in [a for a in bpy.data.actions if a != act]: bpy.data.actions.remove(a)
trk = tarm.animation_data.nla_tracks.new(); trk.name = NAME; st = trk.strips.new(NAME, f0, act)
if hasattr(st, 'action_slot') and hasattr(act, 'slots') and len(act.slots): st.action_slot = act.slots[0]
tarm.animation_data.action = None
for o in bpy.data.objects: o.select_set(o.type in ('ARMATURE', 'MESH'))
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True, export_animations=True, export_animation_mode='NLA_TRACKS',
                          export_force_sampling=True, export_yup=True)
print('RETARGET', NAME, 'frames', f0, f1, 'hip ratio %.2f' % hip_ratio, '->', OUT)
