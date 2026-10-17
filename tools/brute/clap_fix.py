# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
# Thunderclap rebuilt from a retargeted Meshy take (owner 2026-10-16: "hands do not meet palm-to-palm, slow"). Generated clap
# takes never brought the palms together, so the body (legs, stance, torso, head) is taken from the take (time-remapped) and the
# arms are posed procedurally in Blender: wind up far out to the sides and slightly back, then a fast accelerating swing (shoulder
# arc, nearly straight arms, 2-bone IK) to flat palm-to-palm contact straight in front of the chest, a short hold with a forward
# lean, then the hands part and lower. Palms lead the swing (palm normal = arc tangent); forearm / upper-arm twist follows the hand.
# The palm normal and hand thickness come from the bind pose (finger curl side, skinned hand vertices).
# usage: Blender -b --factory-startup -P tools/brute/clap_fix.py -- <take_rt.glb> <out.glb> [ClipName=Clap]
#   env CLAP_SRC=a,b   source frame range of the take used for the body (default 8,44), CLAP_CONTACT=frame (default 21),
#       CLAP_HEAD_DOWN=deg head pitch vs the bind pose (default -40 = eyes forward on the hunched Brute)
# 2026-10-16 Clap: take 01a1481b-ebf0-7116-a942-9a5eee327283 (clapA), retargeted with BRUTE_LEG_SPREAD=12 BRUTE_YAW_LOCK=1 BRUTE_FIST=0
import bpy, sys, os, math
from mathutils import Vector, Quaternion, Matrix

a = sys.argv[sys.argv.index('--') + 1:]
SRC, OUT = a[0], a[1]
NAME = a[2] if len(a) > 2 else 'Clap'
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; sc.render.fps = 30
bpy.ops.import_scene.gltf(filepath=SRC)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
meshes = [o for o in bpy.data.objects if o.type == 'MESH' and any(m.type == 'ARMATURE' for m in o.modifiers)]
sact = arm.animation_data.nla_tracks[0].strips[0].action
for t in list(arm.animation_data.nla_tracks): arm.animation_data.nla_tracks.remove(t)
arm.animation_data.action = sact
if hasattr(sact, 'slots') and len(sact.slots): arm.animation_data.action_slot = sact.slots[0]
sf0 = int(round(sact.frame_range[0]))
W = arm.matrix_world; Wq = W.to_quaternion()
def depth(b): return len(b.parent_recursive)
order = sorted(arm.data.bones, key=depth)
RQ = {b.name: (W @ b.matrix_local).to_quaternion() for b in arm.data.bones}
RH = {b.name: W @ b.head_local for b in arm.data.bones}
tR = {b.name: b.matrix_local.to_quaternion() for b in arm.data.bones}
PAR = {b.name: (b.parent.name if b.parent else None) for b in arm.data.bones}
ROOT = 'Hips'

def sample(f):
    fi = int(math.floor(f)); sc.frame_set(fi, subframe=f - fi)
    world = {b.name: (W @ arm.pose.bones[b.name].matrix).to_quaternion() for b in order}
    return world, arm.pose.bones[ROOT].location.copy(), W @ arm.pose.bones[ROOT].head
def fk(world, root_head):
    pos = {}
    for b in order:
        p = PAR[b.name]
        pos[b.name] = root_head.copy() if p is None else pos[p] + (world[p] @ RQ[p].inverted()) @ (RH[b.name] - RH[p])
    return pos
def rebuild(world_src, over):
    """world rotations top-down: overridden bones absolute, all others keep their source parent-relative rotation"""
    out = {}
    for b in order:
        n = b.name; p = PAR[n]
        if n in over: out[n] = over[n]
        elif p is None: out[n] = world_src[n]
        else: out[n] = out[p] @ (world_src[p].inverted() @ world_src[n])
    return out
def smooth(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)

# ---- bind-pose hand frame: finger axis f (wrist -> middle knuckle), palm normal n (side the fingers curl to), thickness
HAND = {}
for s in ('Left', 'Right'):
    w_ = RH[s + 'Hand']; k_ = RH[s + 'HandMiddle1']
    f = (k_ - w_).normalized()
    tip = W @ arm.data.bones[s + 'HandMiddle2'].tail_local
    c = (tip - k_); c -= c.dot(f) * f
    across = RH[s + 'HandIndex1'] - RH[s + 'HandPinky1']; across -= across.dot(f) * f
    n = f.cross(across).normalized()
    if n.dot(c) < 0: n = -n
    # skinned vertices of the hand (palm + fingers): extent along n (palm side positive)
    pr = []
    for m in meshes:
        gi = {g.index for g in m.vertex_groups if g.name == s + 'Hand'}   # palm only (no thumb / fingers)
        for v in m.data.vertices:
            wsum = sum(g.weight for g in v.groups if g.group in gi)
            if wsum > 0.6:
                q = m.matrix_world @ v.co - w_
                if 0 <= q.dot(f) <= (k_ - w_).length * 1.1: pr.append(q.dot(n))
    HAND[s] = dict(f=f, n=n, palm=max(pr) if pr else 0.06, back=min(pr) if pr else -0.06)
    print('HAND', s, 'curl %.2f' % c.length, 'palm off %.3f back %.3f verts %d' % (HAND[s]['palm'], HAND[s]['back'], len(pr)))
L1 = {s: (RH[s + 'ForeArm'] - RH[s + 'Arm']).length for s in ('Left', 'Right')}
L2 = {s: (RH[s + 'Hand'] - RH[s + 'ForeArm']).length for s in ('Left', 'Right')}

def frame_from(f, n):
    """rotation taking the bind hand frame (f_rest, n_rest) to (f, n)"""
    def M(x, y):
        x = x.normalized(); y = (y - y.dot(x) * x).normalized(); z = x.cross(y)
        return Matrix((x, y, z)).transposed()
    return (M(f, n) @ M(HAND_s['f'], HAND_s['n']).inverted()).to_quaternion()

def ik_arm(s, world, pos, T, n_des, pole, f_over=None, fw=0.0):
    """2-bone IK of s arm to wrist target T with palm normal n_des; returns overrides for Arm, ForeArm, Hand. f_over / fw: finger
    axis to bend the wrist toward (0 = straight wrist along the forearm)"""
    global HAND_s; HAND_s = HAND[s]
    S = pos[s + 'Arm']; l1, l2 = L1[s], L2[s]
    dv = T - S; d = min(dv.length, (l1 + l2) * 0.999); u = dv.normalized()
    pn = pole - pole.dot(u) * u; pn.normalize()
    ca = max(-1.0, min(1.0, (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d)))
    E = S + l1 * (ca * u + math.sqrt(1 - ca * ca) * pn); T2 = S + u * d
    f_des = (T2 - E).normalized()
    if f_over is not None and fw > 0: f_des = f_des.slerp(f_over.normalized(), fw)
    Hq = frame_from(f_des, n_des)
    hand = Hq @ RQ[s + 'Hand']
    fore0 = Hq @ RQ[s + 'ForeArm']
    off = (fore0 @ RQ[s + 'ForeArm'].inverted()) @ (RH[s + 'Hand'] - RH[s + 'ForeArm'])
    fore = off.rotation_difference(T2 - E) @ fore0
    up0 = fore @ RQ[s + 'ForeArm'].inverted() @ RQ[s + 'Arm']
    off = (up0 @ RQ[s + 'Arm'].inverted()) @ (RH[s + 'ForeArm'] - RH[s + 'Arm'])
    up = off.rotation_difference(E - S) @ up0
    return {s + 'Arm': up, s + 'ForeArm': fore, s + 'Hand': hand}

# ---- timing (output frames, 30 fps)
cs = os.environ.get('CLAP_SRC', '8,44').split(',')
SA, SB = float(cs[0]), float(cs[1])
K_LOAD, K_SWING = 6, 15            # arms fling out from hanging by K_LOAD; slow load (arms drawing back) until K_SWING
K_HIT = int(os.environ.get('CLAP_CONTACT', '21'))   # palm contact (swing K_SWING -> K_HIT, accelerating)
K_HOLD = K_HIT + 12                # hold the clap 0.4 s
K_END = K_HOLD + 14                # hands part and lower
N = K_END
REACH = 0.94
HEAD_DOWN = float(os.environ.get('CLAP_HEAD_DOWN', '-40'))   # deg: head pitch vs the bind pose (eyes forward)

w0, _, rh0 = sample(sf0 + SA)
p0 = fk(w0, rh0)
lat = p0['RightUpLeg'] - p0['LeftUpLeg']; lat.z = 0; lat.normalize()   # character left -> right
# 2026-10-17 (owner: "one arm leads the other by ~1 frame"; the bind / take are not symmetric, the right shoulder sits ~6 cm ahead):
# the right arm is re-solved every frame to the exact mirror image (about the sagittal plane at the hips) of the left wrist, elbow and
# palm, so both palms travel and land on the same frame, flat palm to palm (palm normals = the lateral axis, wrists bent back). Weight: a small rise while loading, then the hips drop into the impact (knees give, feet stay planted)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import anim_lib as AL
AL.bind(arm, sact)
ORIG = rh0.copy()
DIP = float(os.environ.get('CLAP_DIP', '0.06')) * AL.leg_len()
UP = Vector((0, 0, 1)); FWD = UP.cross(lat); BACK = -FWD
print('FRAME lat', tuple(round(x, 2) for x in lat), 'fwd', tuple(round(x, 2) for x in FWD))
def pitch_in(v, fwd): return math.degrees(math.atan2(v.dot(fwd), v.z))
def pitch_of(v): return pitch_in(v, FWD)
_q1 = Quaternion(lat, math.radians(1.0))
if (_q1 @ UP).dot(FWD) < 0: _q1 = Quaternion(lat, -math.radians(1.0))
def pitch_fwd(deg): return Quaternion(_q1.axis, _q1.angle * deg)   # + deg tips the top toward FWD
# bind-pose references (the bind faces its own direction): torso pitch and head-axis pitch of the neutral Brute
_rl = RH['RightUpLeg'] - RH['LeftUpLeg']; _rl.z = 0; _rl.normalize(); _rf = UP.cross(_rl)
TORSO0 = pitch_in(RH['Neck'] - RH['Spine'], _rf)
HEAD0 = pitch_in(RQ['Head'] @ Vector((0, 1, 0)), _rf)
print('BIND torso pitch %.1f head pitch %.1f' % (TORSO0, HEAD0))

act = bpy.data.actions.new(NAME)
arm.animation_data.action = None
keys = []
for k in range(N + 1):
    fsrc = sf0 + SA + (SB - SA) * k / N
    ws, hloc, rhead = sample(fsrc)
    feet0 = {s_: fk(ws, rhead)[s_ + 'Foot'] for s_ in ('Left', 'Right')}
    # hips: rise a little while the arms load, drop hard into the impact (2 frames), recover over 14
    if k <= K_SWING: dz = 0.25 * DIP * smooth(k / K_SWING)
    elif k <= K_HIT: dz = 0.25 * DIP * (1 - smooth((k - K_SWING) / (K_HIT - K_SWING)))
    elif k <= K_HIT + 2: dz = -DIP * smooth((k - K_HIT) / 2)
    else: dz = -DIP * (1 - smooth((k - K_HIT - 2) / 14))
    rhead = rhead + Vector((0, 0, dz))
    ws = rebuild(ws, {})
    for s_ in ('Left', 'Right'):
        ws = rebuild(ws, AL.leg_ik(ws, rhead, s_, feet0[s_]))
    # torso lean (about the hips-level lateral axis, at the Spine bone): back while loading, forward into the clap
    if k <= K_SWING: lean = -6 * smooth(k / K_SWING)
    elif k <= K_HIT: lean = -6 + 22 * smooth((k - K_SWING) / (K_HIT - K_SWING))
    elif k <= K_HOLD: lean = 16 - 2 * (k - K_HIT) / (K_HOLD - K_HIT)
    else: lean = 14 - 8 * smooth((k - K_HOLD) / (K_END - K_HOLD))
    # lean is the TARGET torso pitch (Spine -> Neck vs vertical, + = forward); the take's own pitch is taken out first
    base = rebuild(ws, {})
    pb_ = fk(base, rhead)
    src_pitch = pitch_of(pb_['Neck'] - pb_['Spine'])
    ql = pitch_fwd(lean + TORSO0 - src_pitch)
    over = {'Spine': ql @ base['Spine']}
    world = rebuild(ws, over)
    # head: eyes forward (head bone axis back to its bind pitch relative to vertical, + HEAD_UP down-look offset)
    hp = pitch_of(world['Head'] @ Vector((0, 1, 0)))
    over['Neck'] = pitch_fwd(HEAD0 + HEAD_DOWN - hp) @ world['Neck']
    world = rebuild(ws, over)
    pos = fk(world, rhead)
    mid = (pos['LeftArm'] + pos['RightArm']) / 2
    # body-relative axes this frame (the lean tilts the shoulder frame)
    fwd_b = pitch_fwd(lean) @ FWD; up_b = pitch_fwd(lean) @ UP
    for s in ('Left', 'Right'):
        S = pos[s + 'Arm']; L = L1[s] + L2[s]
        out = S - mid; out -= out.dot(up_b) * up_b; h = out.length; out.normalize()
        d_w1 = (out + BACK * 0.28 + up_b * 0.10).normalized()      # arms far out to the sides
        d_w2 = (out + BACK * 0.48 + up_b * 0.14).normalized()      # loaded: drawn further back, chest open
        gap = (HAND[s]['palm'] + HAND['Right' if s == 'Left' else 'Left']['palm']) * 0.98
        zc = -0.06 * L
        lat_off = max(0.0, h - gap / 2)
        fc = math.sqrt(max(1e-4, (REACH * L) ** 2 - lat_off ** 2 - zc ** 2))
        Tc = mid + fwd_b * fc + up_b * zc + out * (gap / 2)
        sgn = 1 if s == 'Right' else -1
        Tc = Tc - ((Tc - ORIG).dot(lat) - sgn * gap / 2) * lat          # palm surfaces meet exactly on the mirror plane
        n_hit = -sgn * lat                                               # flat palm, facing the other palm
        f_hit = fwd_b * 0.8 + up_b * 0.55; f_hit = (f_hit - f_hit.dot(n_hit) * n_hit).normalized()   # fingers forward-up
        d_c = (Tc - S).normalized()
        d_rel = (fwd_b * 0.55 - up_b * 1.0 + out * 0.30).normalized()
        axis = d_w2.cross(d_c).normalized(); th = d_w2.angle(d_c)
        tang_c = axis.cross(d_c).normalized()   # palm normal at contact (direction of travel = toward the other palm)
        if k <= K_SWING:
            d0 = (-up_b + out * 0.35 + fwd_b * 0.12).normalized()        # hanging at the sides (idle-like start)
            d = d_w1.slerp(d_w2, smooth((k - K_LOAD) / (K_SWING - K_LOAD))) if k > K_LOAD else d0.slerp(d_w1, smooth(k / K_LOAD))
            rch = 0.95
            ax_ = d.cross(d_c).normalized(); n = ax_.cross(d).normalized(); fw_ = 0.0
        elif k <= K_HIT:
            u = ((k - K_SWING) / (K_HIT - K_SWING)) ** 2       # accelerating: fastest at the impact
            d = Quaternion(axis, th * u) @ d_w2; rch = REACH
            n = axis.cross(d).normalized()
            fw_ = smooth((k - K_SWING) / (K_HIT - K_SWING)); n = n.slerp(n_hit, fw_)
        elif k <= K_HOLD:
            d = d_c; rch = REACH; n = n_hit; fw_ = 1.0
        else:
            v = smooth((k - K_HOLD) / (K_END - K_HOLD))
            d = d_c.slerp(d_rel, v); rch = REACH - 0.06 * v
            n = n_hit.slerp(-out, v * 0.3); fw_ = 1.0 - v
        T = Tc if K_HIT <= k <= K_HOLD else S + d * rch * L
        pole = (-up_b + BACK * 0.35 + out * 0.6).normalized()
        o = ik_arm(s, world, pos, T, n, pole, f_hit, fw_)
        over.update(o)
        # open flat palms: straighten the four fingers in line with the hand (the bind fingers are curled)
        wf = 1.0 if k <= K_HOLD else 1.0 - 0.6 * smooth((k - K_HOLD) / (K_END - K_HOLD))
        hw = rebuild(ws, over)
        hand_dir = (hw[s + 'Hand'] @ RQ[s + 'Hand'].inverted()) @ HAND[s]['f']
        for fn in ('Index', 'Middle', 'Ring', 'Pinky'):
            for seg in ('', '1', '2'):
                bn = s + 'Hand' + fn + seg
                cur = hw[bn]
                # segment direction from the joint positions (bone axes of the imported rig need not follow the finger)
                ch = [c.name for c in arm.data.bones[bn].children]
                seg_rest = (RH[ch[0]] if ch else W @ arm.data.bones[bn].tail_local) - RH[bn]
                bd = (cur @ RQ[bn].inverted()) @ seg_rest
                q = bd.rotation_difference(hand_dir)
                over[bn] = Quaternion().slerp(q, wf) @ cur
                hw = rebuild(ws, over)
    world = rebuild(ws, over)
    # right arm = mirror image of the left wrist / elbow / palm positions
    def mir(p): return p - 2 * (p - ORIG).dot(lat) * lat
    def mirv(v): return v - 2 * v.dot(lat) * lat
    pz_ = fk(world, rhead)
    nL = (world['LeftHand'] @ RQ['LeftHand'].inverted()) @ HAND['Left']['n']
    o = ik_arm('Right', world, pz_, mir(pz_['LeftHand']), mirv(nL), mir(pz_['LeftForeArm']) - pz_['RightArm'])
    world = rebuild(world, o)
    if k in (0, K_HIT): print('HEADPITCH k %d hp %.1f' % (k, pitch_of(world['Head'] @ Vector((0, 1, 0)))))
    pz_ = fk(world, rhead); mL = pz_['LeftHand'] - ORIG; mR = pz_['RightHand'] - ORIG
    if k % 3 == 0 or K_SWING <= k <= K_HIT + 1:
        print('SYM k %2d  wrist lateral L %+.3f R %+.3f  fwd L %.3f R %.3f  z L %.3f R %.3f' % (k, mL.dot(lat), mR.dot(lat), mL.dot(FWD), mR.dot(FWD), pz_['LeftHand'].z, pz_['RightHand'].z))
    hloc = tR[ROOT].inverted() @ (W.inverted().to_3x3() @ (rhead - RH[ROOT]))
    keys.append((k, world, hloc))
    if k in (0, K_SWING, K_HIT, K_HOLD, N):
        pz = fk(world, rhead)
        print('K %2d src %.1f lean %+.0f  wristgap %.3f  wrist z %.2f  shoulder z %.2f  fwd %.2f' % (
            k, fsrc, lean, (pz['LeftHand'] - pz['RightHand']).length, (pz['LeftHand'].z + pz['RightHand'].z) / 2,
            (pz['LeftArm'].z + pz['RightArm'].z) / 2, ((pz['LeftHand'] + pz['RightHand']) / 2 - pz['Hips']).dot(FWD)))

arm.animation_data.action = act
if hasattr(act, 'slots') and hasattr(arm.animation_data, 'action_slot') and len(act.slots): arm.animation_data.action_slot = act.slots[0]
Wqi = Wq.inverted()
for k, world, hloc in keys:
    fr = sf0 + k
    for b in order:
        pb = arm.pose.bones[b.name]; pb.rotation_mode = 'QUATERNION'
        aq = Wqi @ world[b.name]
        if b.parent:
            basis = ((Wqi @ world[b.parent.name]) @ (tR[b.parent.name].inverted() @ tR[b.name])).inverted() @ aq
        else: basis = tR[b.name].inverted() @ aq
        pb.rotation_quaternion = basis; pb.keyframe_insert('rotation_quaternion', frame=fr)
    pr = arm.pose.bones[ROOT]; pr.location = hloc; pr.keyframe_insert('location', frame=fr)
for a_ in [a_ for a_ in bpy.data.actions if a_ != act]: bpy.data.actions.remove(a_)
arm.animation_data.action = None
trk = arm.animation_data.nla_tracks.new(); trk.name = NAME; st = trk.strips.new(NAME, sf0, act)
if hasattr(st, 'action_slot') and hasattr(act, 'slots') and len(act.slots): st.action_slot = act.slots[0]
for o in bpy.data.objects: o.select_set(o.type in ('ARMATURE', 'MESH'))
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True, export_animations=True, export_animation_mode='NLA_TRACKS',
                          export_force_sampling=True, export_yup=True)
print('CLAPFIX', NAME, 'frames', N + 1, 'contact frame', K_HIT, '(%.2f s)' % (K_HIT / 30), '->', OUT)
