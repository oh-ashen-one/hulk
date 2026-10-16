# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
# Retarget a motion clip from another humanoid skeleton (Meshy Text-to-Motion retarget, Mixamo-style names) onto the Brute's
# Cartwheel rig, in Blender. World-space rotation deltas per bone (source pose x source rest^-1, applied on the target rest),
# hips translation scaled by the hip-height ratio; unmapped bones (fingers) keep their rest relation.
# Writes a GLB with the target armature + mesh + one action named after the clip, which assemble_motion.py picks up.
# usage: Blender -b --factory-startup -P tools/brute/retarget_motion.py -- <target_rig.glb> <source_motion.glb> <out.glb> <ClipName>
import bpy, sys, re
from mathutils import Matrix, Quaternion, Vector

TGT, SRC, OUT, NAME = sys.argv[sys.argv.index('--') + 1:][:4]
import os
FIST = os.environ.get('BRUTE_FIST', '1') == '1'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.render.fps = 30

def imp(f):
    before = set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=f)
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
print('MAP', MAP)

ROOT = 'Hips'
sW, tW = sarm.matrix_world, tarm.matrix_world
s_rest = {b.name: (sW @ b.matrix_local).to_quaternion() for b in sarm.data.bones}
t_rest = {b.name: (tW @ b.matrix_local).to_quaternion() for b in tarm.data.bones}
tR = {b.name: b.matrix_local.to_quaternion() for b in tarm.data.bones}   # armature-space rest rotations
hip_ratio = (tW @ tarm.data.bones[ROOT].head_local).z / max(1e-3, (sW @ sarm.data.bones[ROOT].head_local).z)
s_hip0 = None
order = sorted(tarm.data.bones, key=depth)
act = bpy.data.actions.new(NAME); tarm.animation_data_create(); tarm.animation_data.action = act
tWq_inv = tW.to_quaternion().inverted()
for fr in range(f0, f1 + 1):
    bpy.context.scene.frame_set(fr)
    world = {}
    for b in order:
        sname = MAP.get(b.name)
        if sname:
            sq = (sW @ sarm.pose.bones[sname].matrix).to_quaternion()
            world[b.name] = (sq @ s_rest[sname].inverted()) @ t_rest[b.name]
        else:
            p = b.parent
            world[b.name] = (world[p.name] @ t_rest[p.name].inverted() @ t_rest[b.name]) if p else t_rest[b.name]
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
    # hips translation (world delta from the source's first frame, scaled), into the root bone's rest frame
    sh = sW @ sarm.pose.bones[ROOT].head
    if s_hip0 is None: s_hip0 = sh.copy()
    d_world = (sh - s_hip0) * hip_ratio
    d_world.z = (sh.z - (sW @ sarm.data.bones[ROOT].head_local).z) * hip_ratio
    d_arm = tW.inverted().to_3x3() @ d_world
    pr = tarm.pose.bones[ROOT]; pr.location = tR[ROOT].inverted() @ d_arm
    pr.keyframe_insert('location', frame=fr)
bpy.data.objects.remove(sarm)
for a in [a for a in bpy.data.actions if a != act]: bpy.data.actions.remove(a)
trk = tarm.animation_data.nla_tracks.new(); trk.name = NAME; st = trk.strips.new(NAME, f0, act)
if hasattr(st, 'action_slot') and hasattr(act, 'slots') and len(act.slots): st.action_slot = act.slots[0]
tarm.animation_data.action = None
for o in bpy.data.objects: o.select_set(o.type in ('ARMATURE', 'MESH'))
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True, export_animations=True, export_animation_mode='NLA_TRACKS',
                          export_force_sampling=True, export_yup=True)
print('RETARGET', NAME, 'frames', f0, f1, 'hip ratio %.2f' % hip_ratio, '->', OUT)
