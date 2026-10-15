# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
# Brute animation clips, authored in Blender on the Customuse auto-rigged model (owner direction 2026-10-15: "use Blender to animate").
# In-place clips (the game / viewer moves the body): Idle, Walk, Run, Stop, WallClimb, JumpCharge, JumpAir, Land.
# Legs: foot targets keyed along a stride path + Blender IK (pole) baked to FK, so stance feet stay planted at the clip's speed.
# Arms / spine / head: keyed poses in body axes (pitch forward / abduction / yaw), converted into each bone's rest frame.
# Writes <out>/brute.glb (mesh + skeleton + 8 actions, for the localhost viewer and Unreal) + <out>/clips.json (speeds for the viewer).
# usage: Blender -b --factory-startup -P tools/brute/animate_brute.py -- <rigged.fbx|glb> <out_dir>
import bpy, sys, os, json, math, re
from mathutils import Vector, Quaternion, Matrix

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
SRC, OUT = argv[0], (argv[1] if len(argv) > 1 else os.path.expanduser('~/hulk-scratch/brute_v2'))
HEIGHT = float(os.environ.get('BRUTE_HEIGHT_M', '2.6'))
os.makedirs(OUT, exist_ok=True)
FPS = 30

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.render.fps = FPS
if SRC.lower().endswith('.fbx'): bpy.ops.import_scene.fbx(filepath=SRC, automatic_bone_orientation=False, ignore_leaf_bones=False)
else: bpy.ops.import_scene.gltf(filepath=SRC)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
for o in list(bpy.data.objects):
    if o.type not in ('ARMATURE', 'MESH'): pass
for a in list(bpy.data.actions): bpy.data.actions.remove(a)
if arm.animation_data: arm.animation_data_clear()
for pb in arm.pose.bones:   # the FBX import leaves a bind-pose offset on the pose bones: start from the clean rest pose
    pb.rotation_mode = 'QUATERNION'; pb.rotation_quaternion = Quaternion(); pb.location = Vector(); pb.scale = Vector((1, 1, 1))
bpy.context.view_layer.update()

# ---- scale the whole rig to the game height (feet at z 0)
def world_bounds():
    zs = []
    for m in meshes:
        for v in m.data.vertices: zs.append((m.matrix_world @ v.co).z)
    return min(zs), max(zs)
z0, z1 = world_bounds()
k = HEIGHT / (z1 - z0)
bpy.ops.object.select_all(action='DESELECT')
for o in [arm] + [m for m in meshes if m.parent is None]: o.select_set(True)
bpy.context.view_layer.objects.active = arm
for o in [arm] + [m for m in meshes if m.parent is None]:
    o.scale = o.scale * k; o.location = o.location * k
bpy.context.view_layer.update()
z0, z1 = world_bounds(); arm.location.z -= z0
for m in meshes:
    if m.parent is None: m.location.z -= z0
bpy.context.view_layer.update()
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
print('SCALED to %.2f m (k %.3f)' % (HEIGHT, k))

# ---- bone resolution (Mixamo / Meshy / Tripo / AccuRIG / UE / generic names)
names = [b.name for b in arm.data.bones]
def norm(n): return re.sub(r'[^a-z0-9]', '', n.lower().split(':')[-1])
NB = {norm(n): n for n in names}
def find(*pats, side=None):
    for p in pats:
        for nn, n in NB.items():
            s = nn
            if side:
                if not (s.startswith(side) or s.endswith(side) or ('left' if side == 'l' else 'right') in s or s.startswith(side + 'b')): continue
                s = s.replace('left', '').replace('right', '')
            if re.fullmatch(p, s) or re.fullmatch(p, s.lstrip('lr')) or re.fullmatch(p, s.rstrip('lr')): return n
    return None
B = {}
B['hips'] = find(r'hips?', r'pelvis', r'(cc)?base(hip|pelvis)', r'root')
B['spine'] = [n for n in names if re.fullmatch(r'spine\d*|(cc)?base(waist|spine\d*)|chest|upperchest|spine0\d', norm(n))]
B['neck'] = find(r'neck\d*', r'(cc)?baseneck(twist)?\d*')
B['head'] = find(r'head', r'(cc)?basehead')
for s in ('l', 'r'):
    B['clav_' + s] = find(r'shoulder', r'clavicle', r'(cc)?baseclavicle', side=s)
    B['upper_' + s] = find(r'arm', r'upperarm', r'(cc)?baseupperarm', side=s)
    B['fore_' + s] = find(r'forearm', r'lowerarm', r'(cc)?baseforearm', side=s)
    B['hand_' + s] = find(r'hand', r'(cc)?basehand', side=s)
    B['thigh_' + s] = find(r'upleg', r'thigh', r'upperleg', r'(cc)?basethigh', side=s)
    B['calf_' + s] = find(r'leg', r'calf', r'lowerleg', r'shin', r'(cc)?basecalf', side=s)
    B['foot_' + s] = find(r'foot', r'(cc)?basefoot', side=s)
    B['toe_' + s] = find(r'toebase', r'toe\d*', r'ball', r'(cc)?basetoebase', side=s)
    B['fingers_' + s] = [n for n in names if re.search(r'(thumb|index|middle|ring|pinky|finger)', norm(n)) and
                         (('left' in norm(n)) if s == 'l' else ('right' in norm(n))) or (re.search(r'(thumb|index|middle|ring|pinky|finger)', norm(n)) and norm(n).endswith(s) and not ('left' in norm(n) or 'right' in norm(n)))]
if 'left_shoulder' in names and 'left_elbow' in names:   # SMPL-style skeleton (Customuse Humanoid Auto Rig / Cartwheel)
    B = {'hips': 'pelvis', 'spine': [n for n in ('spine1', 'spine2', 'spine3') if n in names], 'neck': 'neck', 'head': 'head'}
    for s, w in (('l', 'left'), ('r', 'right')):
        B.update({'clav_' + s: w + '_collar', 'upper_' + s: w + '_shoulder', 'fore_' + s: w + '_elbow', 'hand_' + s: w + '_wrist',
                  'thigh_' + s: w + '_hip', 'calf_' + s: w + '_knee', 'foot_' + s: w + '_ankle', 'toe_' + s: w + '_foot',
                  'fingers_' + s: [n for n in names if re.match(w + r'_(thumb|index|middle|ring|pinky)\d', n)]})
print('BONES', {k: v for k, v in B.items()})
need = ['hips', 'head', 'upper_l', 'fore_l', 'upper_r', 'fore_r', 'thigh_l', 'calf_l', 'foot_l', 'thigh_r', 'calf_r', 'foot_r']
missing = [n for n in need if not B.get(n)]
if missing: raise SystemExit('BRUTE_ANIM_FAILED missing bones %s; all bones: %s' % (missing, names))
B['spine'] = [b for b in B['spine'] if b != B['hips']] or ([B['neck']] if B['neck'] else [])

# ---- re-aim the limb / spine bones along the limb (tail = child head). The generated rig's bone axes point anywhere; IK needs the
# calf tail on the ankle. Editing rest bones does not move the skinned mesh (deformation = pose x rest^-1).
chain_pairs = [(B['hips'], (B['spine'] or [B['neck']])[0])] + list(zip(B['spine'], B['spine'][1:] + [B['neck'] or B['head']]))
if B['neck']: chain_pairs.append((B['neck'], B['head']))
for s_ in ('l', 'r'):
    chain_pairs += [(B['upper_' + s_], B['fore_' + s_]), (B['fore_' + s_], B['hand_' + s_]), (B['thigh_' + s_], B['calf_' + s_]),
                    (B['calf_' + s_], B['foot_' + s_])]
    if B.get('toe_' + s_): chain_pairs.append((B['foot_' + s_], B['toe_' + s_]))
    if B.get('clav_' + s_): chain_pairs.append((B['clav_' + s_], B['upper_' + s_]))
bpy.context.view_layer.objects.active = arm
for o in bpy.data.objects: o.select_set(o == arm)
bpy.ops.object.mode_set(mode='EDIT')
E = arm.data.edit_bones
for a_, b_ in chain_pairs:
    if a_ and b_ and a_ in E and b_ in E and (E[b_].head - E[a_].head).length > 0.02:
        E[a_].use_connect = False; E[a_].tail = E[b_].head.copy(); E[a_].roll = 0.0
hb = E[B['head']]; hb.tail = hb.head + Vector((0, 0, 0.3))
bpy.ops.object.mode_set(mode='OBJECT')

# ---- body axes in armature space
db = arm.data.bones
def head(n): return db[n].head_local.copy()
U = Vector((0, 0, 1))
toe_or_tail = lambda s: head(B['toe_' + s]) if B.get('toe_' + s) else db[B['foot_' + s]].tail_local
Fv = ((toe_or_tail('l') - head(B['foot_l'])) + (toe_or_tail('r') - head(B['foot_r']))); Fv.z = 0
F = Fv.normalized() if Fv.length > 1e-4 else Vector((0, -1, 0))
R = F.cross(U).normalized()
# sanity: the character's right hand must be on +R
if (head(B['upper_r']) - head(B['upper_l'])).dot(R) < 0: R = -R
print('AXES F', tuple(round(c, 3) for c in F), 'R', tuple(round(c, 3) for c in R))

def q_axis(ax, deg): return Quaternion(ax, math.radians(deg))
def body_rot(pitch=0.0, abd=0.0, yaw=0.0, side=1):
    """UE-style FRotator in body axes: roll (abduction, + = outward for this side) first, then pitch (+ = a hanging limb swings forward,
    + on the spine leans BACK, like UE), then yaw (+ = turn to the character's right)."""
    return q_axis(U, -yaw) @ q_axis(R, pitch) @ q_axis(F, -side * abd)
def set_rot(pb, q_arm):
    Bq = db[pb.name].matrix_local.to_quaternion()
    pb.rotation_mode = 'QUATERNION'; pb.rotation_quaternion = Bq.inverted() @ q_arm @ Bq
def set_loc(pb, v_arm):
    Bq = db[pb.name].matrix_local.to_quaternion()
    pb.location = Bq.inverted() @ v_arm

P = arm.pose.bones
legs = {}
for s in ('l', 'r'):
    hj, kn, an = head(B['thigh_' + s]), head(B['calf_' + s]), head(B['foot_' + s])
    legs[s] = dict(hip=hj, ankle=an, L=(kn - hj).length + (an - kn).length)
HIPZ = head(B['hips']).z
LEGLEN = (legs['l']['L'] + legs['r']['L']) / 2
print('LEG length %.2f m, hips %.2f m' % (LEGLEN, HIPZ))

# ---- IK rig for the legs: foot target empties + knee poles in front
bpy.context.view_layer.objects.active = arm
targets = {}
for s, sg in (('l', -1), ('r', 1)):
    t = bpy.data.objects.new('IK_foot_' + s, None); bpy.context.collection.objects.link(t); t.location = arm.matrix_world @ legs[s]['ankle']
    p = bpy.data.objects.new('IK_pole_' + s, None); bpy.context.collection.objects.link(p)
    p.location = arm.matrix_world @ (head(B['calf_' + s]) + F * 1.5)
    t.rotation_mode = 'QUATERNION'; t.rotation_quaternion = (arm.matrix_world.to_quaternion() @ db[B['foot_' + s]].matrix_local.to_quaternion())
    c = P[B['calf_' + s]].constraints.new('IK'); c.target = t; c.pole_target = p; c.chain_count = 2; c.use_tail = True
    c.pole_angle = 0.0
    cr = P[B['foot_' + s]].constraints.new('COPY_ROTATION'); cr.target = t; cr.target_space = 'WORLD'; cr.owner_space = 'WORLD'
    targets[s] = (t, p)
# pole angle calibration: rotate until the rest pose knee stays put (search)
bpy.context.view_layer.update()
for s in ('l', 'r'):
    c = P[B['calf_' + s]].constraints[-1]; best = (1e9, 0.0)
    for a in range(-180, 181, 15):
        c.pole_angle = math.radians(a); bpy.context.view_layer.update()
        d = ((arm.matrix_world @ P[B['calf_' + s]].head) - (arm.matrix_world @ head(B['calf_' + s]))).length
        if d < best[0]: best = (d, a)
    for a in range(best[1] - 14, best[1] + 15, 2):
        c.pole_angle = math.radians(a); bpy.context.view_layer.update()
        d = ((arm.matrix_world @ P[B['calf_' + s]].head) - (arm.matrix_world @ head(B['calf_' + s]))).length
        if d < best[0]: best = (d, a)
    c.pole_angle = math.radians(best[1]); print('POLE', s, best)
    bpy.context.view_layer.update()
    print('POLECHK', s, 'knee rest', tuple(round(x,2) for x in head(B['calf_' + s])), 'posed', tuple(round(x,2) for x in P[B['calf_' + s]].head), 'ankle posed', tuple(round(x,2) for x in P[B['calf_' + s]].tail), 'target', tuple(round(x,2) for x in arm.matrix_world.inverted() @ targets[s][0].location))

def reset_pose():
    for pb in P:
        pb.rotation_mode = 'QUATERNION'; pb.rotation_quaternion = Quaternion(); pb.location = Vector(); pb.scale = Vector((1, 1, 1))

def key_all(f):
    for pb in P:
        pb.keyframe_insert('rotation_quaternion', frame=f); pb.keyframe_insert('location', frame=f)
    for s in ('l', 'r'): targets[s][0].keyframe_insert('location', frame=f); targets[s][0].keyframe_insert('rotation_quaternion', frame=f)

def fist(curl):
    for s in ('l', 'r'):
        sg = 1 if s == 'r' else -1
        for n in B['fingers_' + s]:
            nn = norm(n)
            c = curl * (0.45 if 'thumb' in nn else 1.0)
            set_rot(P[n], q_axis(F, sg * c))

def pose(f, *, hip_drop=0.0, hip_fwd=0.0, hip_side=0.0, hip_roll=0.0, hip_yaw=0.0, lean=0.0, twist=0.0, side_bend=0.0, head_pitch=0.0,
         arms=None, feet=None, curl=55.0, shrug=0.0):
    """one keyed pose. arms[s] = (pitch, abd, yaw, elbow); feet[s] = (fwd, up, out) foot-target offsets (m) from the rest ankle"""
    reset_pose()
    hp = P[B['hips']]
    set_loc(hp, U * (-hip_drop) + F * hip_fwd + R * hip_side)
    set_rot(hp, q_axis(U, -hip_yaw) @ q_axis(F, -hip_roll))
    sp = B['spine']; n = max(1, len(sp))
    for name in sp: set_rot(P[name], q_axis(U, -twist / n) @ q_axis(R, lean / n) @ q_axis(F, -side_bend / n))
    # head_pitch > 0 = look up (counter a forward lean)
    if B['neck']: set_rot(P[B['neck']], q_axis(R, head_pitch * 0.4))
    set_rot(P[B['head']], q_axis(R, head_pitch * 0.6) @ q_axis(U, twist * 0.3))
    for s, sg in (('l', -1), ('r', 1)):
        a = (arms or {}).get(s, (0, 12, 0, 18))
        if B.get('clav_' + s): set_rot(P[B['clav_' + s]], q_axis(F, -sg * shrug))
        set_rot(P[B['upper_' + s]], body_rot(a[0], a[1], a[2], sg))
        set_rot(P[B['fore_' + s]], q_axis(R, a[3]))
        if B.get('hand_' + s): set_rot(P[B['hand_' + s]], q_axis(R, -a[3] * 0.15))
        ft = (feet or {}).get(s, (0, 0, 0))
        targets[s][0].location = arm_world(legs[s]['ankle'] + F * ft[0] + U * ft[1] + R * (sg * ft[2]))
        targets[s][0].rotation_quaternion = arm.matrix_world.to_quaternion() @ q_axis(R, -(ft[3] if len(ft) > 3 else 0.0)) @ db[B['foot_' + s]].matrix_local.to_quaternion()
    fist(curl)
    key_all(f)

def arm_world(v): return arm.matrix_world @ v

clips = {}
def begin(name, frames):
    act = bpy.data.actions.new(name)
    arm.animation_data_create(); arm.animation_data.action = act
    for s in ('l', 'r'):
        t = targets[s][0]; t.animation_data_create(); t.animation_data.action = bpy.data.actions.new(name + '_ik_' + s)
    bpy.context.scene.frame_start, bpy.context.scene.frame_end = 0, frames
    return act

def smooth_cycle(act):
    for fc in act.fcurves:
        for kp in fc.keyframe_points: kp.interpolation = 'BEZIER'; kp.handle_left_type = kp.handle_right_type = 'AUTO_CLAMPED'
        fc.modifiers.new('CYCLES') if False else None

def bake(name, frames):
    """bake IK + keys into plain FK bone keys on every frame (visual keying), drop the IK targets' actions"""
    bpy.context.view_layer.objects.active = arm
    for o in bpy.data.objects: o.select_set(o == arm)
    bpy.ops.object.mode_set(mode='POSE'); bpy.ops.pose.select_all(action='SELECT')
    bpy.ops.nla.bake(frame_start=0, frame_end=frames, step=1, only_selected=True, visual_keying=True, clear_constraints=False,
                     use_current_action=True, bake_types={'POSE'})
    bpy.ops.object.mode_set(mode='OBJECT')
    act = arm.animation_data.action; act.name = name
    arm.animation_data.action = None
    trk = arm.animation_data.nla_tracks.new(); trk.name = name; trk.strips.new(name, 0, act); trk.mute = True
    return act

S = LEGLEN / 1.15   # stride scale from the leg length (m)

# ======================================================================================== Idle (heavy breathing)
T = 60; begin('Idle', T)
for f, br in ((0, 0), (15, 1), (30, 0), (45, -0.6), (60, 0)):
    pose(f, hip_drop=0.06 + 0.015 * br, lean=-(10 + 2.5 * br), head_pitch=4 - 2 * br, shrug=3 + 3 * br,
         arms={'l': (6, 16 + 3 * br, -6, 28), 'r': (6, 16 + 3 * br, 6, 28)},
         feet={'l': (0.02, 0, 0.06), 'r': (-0.04, 0, 0.06)}, twist=2 * br)
clips['Idle'] = dict(label='idle, breathing', speed=0)
bake('Idle', T)

# ======================================================================================== Walk (heavy stomp, 1.2 s cycle)
def gait(name, T, speed, step_len, lift, drop, bob, lean, arm_sw, elbow, abd, sway, flight=0.0):
    """two-step cycle. Each foot: stance (moves back at the body speed, planted on the ground) then swing (lifted forward)."""
    begin(name, T)
    duty = 0.62 if flight == 0 else 0.42
    N = 8
    for i in range(N + 1):
        ph = i / N
        f = round(ph * T)
        feet = {}
        for s, off in (('l', 0.0), ('r', 0.5)):
            p = (ph + off) % 1.0
            if p < duty:   # stance: from +step/2 to -step/2
                x = step_len * (0.5 - p / duty); z = 0.0
            else:          # swing
                q = (p - duty) / (1 - duty); x = step_len * (-0.5 + q); z = lift * math.sin(math.pi * q)
            feet[s] = (x, z, 0.05)
        ang = math.sin(2 * math.pi * ph)
        up = math.cos(4 * math.pi * ph)      # two bobs per cycle (down on contact)
        pose(f, hip_drop=drop + bob * (0.5 - 0.5 * up), hip_side=sway * math.sin(2 * math.pi * ph), hip_roll=3 * math.sin(2 * math.pi * ph),
             hip_yaw=6 * ang, lean=lean, twist=-9 * ang, head_pitch=-lean * 0.6,
             arms={'l': (-arm_sw * ang + 4, abd, -4, elbow + 12 * max(0, -ang)), 'r': (arm_sw * ang + 4, abd, 4, elbow + 12 * max(0, ang))},
             feet=feet, shrug=4)
    clips[name] = dict(label='%.1f m/s' % speed, speed=speed, loop=24, dir=[0, 0, 1])
    bake(name, T)

walk_T = 36; walk_step = 0.95 * S; walk_speed = 2 * walk_step / (walk_T / FPS) * (1 / 1)
gait('Walk', walk_T, walk_speed, walk_step, lift=0.22, drop=0.07, bob=0.06, lean=-10, arm_sw=26, elbow=30, abd=18, sway=0.05)
run_T = 20; run_step = 1.55 * S; run_speed = 2 * run_step / (run_T / FPS)
gait('Run', run_T, run_speed, run_step, lift=0.45, drop=0.14, bob=0.10, lean=-26, arm_sw=52, elbow=70, abd=20, sway=0.03, flight=1)
print('SPEEDS walk %.2f m/s run %.2f m/s' % (walk_speed, run_speed))

# ======================================================================================== Stop (run -> skid -> brace -> stand)
T = 30; begin('Stop', T)
pose(0, hip_drop=0.14, lean=-24, arms={'l': (40, 20, 0, 70), 'r': (-35, 20, 0, 70)}, feet={'l': (0.5, 0.15, 0.05), 'r': (-0.4, 0.05, 0.05)})
pose(6, hip_drop=0.30, hip_fwd=-0.12, lean=8, head_pitch=-6, arms={'l': (35, 40, -10, 50), 'r': (30, 45, 10, 45)}, feet={'l': (0.75, 0, 0.12), 'r': (-0.25, 0, 0.08)})
pose(12, hip_drop=0.34, hip_fwd=-0.08, lean=4, arms={'l': (20, 38, -8, 55), 'r': (25, 40, 8, 50)}, feet={'l': (0.6, 0, 0.12), 'r': (-0.1, 0, 0.1)}, shrug=8)
pose(20, hip_drop=0.12, lean=-14, arms={'l': (8, 22, -6, 35), 'r': (8, 22, 6, 35)}, feet={'l': (0.25, 0, 0.08), 'r': (-0.05, 0, 0.07)}, shrug=6)
pose(30, hip_drop=0.06, lean=-10, head_pitch=4, arms={'l': (6, 16, -6, 28), 'r': (6, 16, 6, 28)}, feet={'l': (0.02, 0, 0.06), 'r': (-0.04, 0, 0.06)}, shrug=3)
clips['Stop'] = dict(label='skid to a stop', speed=0, once=True)
bake('Stop', T)

# ======================================================================================== WallClimb (facing the wall, hand over hand)
T = 30; begin('WallClimb', T)
for f, ph in ((0, 0), (8, 0.25), (15, 0.5), (23, 0.75), (30, 1.0)):
    a = math.sin(2 * math.pi * ph); c = math.cos(2 * math.pi * ph)
    pose(f, hip_drop=0.10 + 0.05 * c, hip_fwd=0.25, lean=-12 - 4 * c, head_pitch=-28, twist=6 * a, side_bend=5 * a,
         arms={'l': (150 + 28 * a, 22, 0, 40 - 30 * a), 'r': (150 - 28 * a, 22, 0, 40 + 30 * a)},
         feet={'l': (0.30, 0.25 + 0.30 * max(0, -a), 0.10), 'r': (0.30, 0.25 + 0.30 * max(0, a), 0.10)}, curl=70, shrug=14)
clips['WallClimb'] = dict(label='climbing a facade', speed=0, dir=[0, 1, 0])
bake('WallClimb', T)

# ======================================================================================== Jump: charge (crouch, held), air, land
T = 24; begin('JumpCharge', T)
for f, k2 in ((0, 0.0), (10, 0.85), (24, 1.0)):
    pose(f, hip_drop=0.06 + 0.55 * k2, hip_fwd=-0.10 * k2, lean=-(12 + 30 * k2), head_pitch=10 + 18 * k2,
         arms={'l': (-40 * k2, 26, -6, 30 + 20 * k2), 'r': (-40 * k2, 26, 6, 30 + 20 * k2)},
         feet={'l': (0.05, 0, 0.10 + 0.05 * k2), 'r': (-0.05, 0, 0.10 + 0.05 * k2)}, shrug=10 * k2)
clips['JumpCharge'] = dict(label='crouch / charge (hold last frame)', speed=0, once=True)
bake('JumpCharge', T)
T = 30; begin('JumpAir', T)
for f, w in ((0, 0), (15, 1), (30, 0)):
    pose(f, hip_drop=0.0, lean=-8 - 4 * w, head_pitch=-6, arms={'l': (100 + 10 * w, 40, -10, 50), 'r': (90 - 10 * w, 45, 10, 45)},
         feet={'l': (0.35, 0.55 + 0.05 * w, 0.08), 'r': (-0.25, 0.30, 0.10)}, curl=65, shrug=8)
clips['JumpAir'] = dict(label='airborne', speed=0)
bake('JumpAir', T)
T = 24; begin('Land', T)
pose(0, hip_drop=0.0, lean=-6, arms={'l': (60, 70, -10, 30), 'r': (60, 70, 10, 30)}, feet={'l': (0.1, 0.2, 0.15), 'r': (-0.1, 0.2, 0.15)})
pose(4, hip_drop=0.78, hip_fwd=0.05, lean=-48, head_pitch=34, arms={'l': (-30, 50, -10, 35), 'r': (75, 12, 8, 8)}, feet={'l': (-0.45, 0, 0.18), 'r': (0.40, 0, 0.20)}, curl=80, shrug=12)
pose(12, hip_drop=0.70, hip_fwd=0.05, lean=-42, head_pitch=30, arms={'l': (-25, 45, -10, 35), 'r': (70, 14, 8, 10)}, feet={'l': (-0.45, 0, 0.18), 'r': (0.40, 0, 0.20)}, curl=80, shrug=10)
pose(24, hip_drop=0.06, lean=-10, head_pitch=4, arms={'l': (6, 16, -6, 28), 'r': (6, 16, 6, 28)}, feet={'l': (0.02, 0, 0.06), 'r': (-0.04, 0, 0.06)})
clips['Land'] = dict(label='superhero landing', speed=0, once=True)
bake('Land', T)

# ---- drop the IK helpers, keep plain FK actions on the armature (NLA strips -> glTF animations)
for s in ('l', 'r'):
    for c in list(P[B['calf_' + s]].constraints): P[B['calf_' + s]].constraints.remove(c)
    for c in list(P[B['foot_' + s]].constraints): P[B['foot_' + s]].constraints.remove(c)
    for o in targets[s]: bpy.data.objects.remove(o)
for a in list(bpy.data.actions):
    if '_ik_' in a.name: bpy.data.actions.remove(a)
reset_pose()
for t in arm.animation_data.nla_tracks: t.mute = False

if os.environ.get('BRUTE_RENDER'):
    sc = bpy.context.scene; sc.render.engine = 'BLENDER_EEVEE'; sc.render.resolution_x = sc.render.resolution_y = 520
    w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == 'BACKGROUND'); bg.inputs[1].default_value = 1.2; bg.inputs[0].default_value = (0.5, 0.5, 0.55, 1)
    sun = bpy.data.objects.new('s', bpy.data.lights.new('s', 'SUN')); sun.data.energy = 3; sc.collection.objects.link(sun); sun.rotation_euler = (0.8, 0.2, 0.6)
    cam = bpy.data.objects.new('c', bpy.data.cameras.new('c')); cam.data.type = 'ORTHO'; cam.data.ortho_scale = 3.4; sc.collection.objects.link(cam); sc.camera = cam
    side = R  # camera on the character's right, looking at him
    cam.location = Vector((0, 0, 1.3)) + side * 6; cam.rotation_euler = (-side).to_track_quat('-Z', 'Y').to_euler()
    for t in arm.animation_data.nla_tracks: t.mute = True
    for t in arm.animation_data.nla_tracks:
        act = t.strips[0].action; arm.animation_data.action = act
        n = int(act.frame_range[1])
        for i, f in enumerate([0, n // 4, n // 2, 3 * n // 4]):
            sc.frame_set(f); sc.render.filepath = os.path.join(OUT, 'anim_%s_%d.png' % (t.name, i)); bpy.ops.render.render(write_still=True)
    arm.animation_data.action = None
    for t in arm.animation_data.nla_tracks: t.mute = False

glb = os.path.join(OUT, 'brute.glb')
for o in bpy.data.objects: o.select_set(o.type in ('ARMATURE', 'MESH'))
bpy.ops.export_scene.gltf(filepath=glb, export_format='GLB', use_selection=True, export_animations=True, export_animation_mode='NLA_TRACKS',
                          export_force_sampling=True, export_frame_range=False, export_yup=True)
fbx = os.path.join(OUT, 'brute_anim.fbx')
bpy.ops.export_scene.fbx(filepath=fbx, use_selection=True, object_types={'MESH', 'ARMATURE'}, axis_forward='X', axis_up='Z',
                         apply_scale_options='FBX_SCALE_ALL', add_leaf_bones=False, bake_anim=True, bake_anim_use_nla_strips=True,
                         bake_anim_use_all_actions=False, bake_anim_force_startend_keying=True, path_mode='COPY', embed_textures=True)
json.dump(clips, open(os.path.join(OUT, 'clips.json'), 'w'), indent=1)
print('WROTE', glb, fbx, 'clips', list(clips))
