# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
# Mirror a retargeted Brute clip left <-> right (e.g. PunchL from PunchR), in Blender. The mirror plane is the character's
# sagittal plane at the first frame (normal = hip line). Per bone: world rotation of the opposite-side bone reflected
# (M R M, quaternion (w, -v + 2(v.n)n)), with a rest correction so the mirrored rest equals the rest; hips path reflected.
# usage: Blender -b --factory-startup -P tools/brute/mirror_clip.py -- <in_clip.glb> <out.glb> <NewClipName>
import bpy, sys, re
from mathutils import Quaternion, Vector

SRC, OUT, NAME = sys.argv[sys.argv.index('--') + 1:][:3]
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; sc.render.fps = 30
bpy.ops.import_scene.gltf(filepath=SRC)
for o in [o for o in bpy.data.objects if o.type == 'MESH' and not any(m.type == 'ARMATURE' for m in o.modifiers)]: bpy.data.objects.remove(o)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
tr = arm.animation_data.nla_tracks[0]; src = tr.strips[0].action
arm.animation_data.nla_tracks.remove(tr); arm.animation_data.action = src
if hasattr(src, 'slots') and len(src.slots): arm.animation_data.action_slot = src.slots[0]
f0, f1 = (int(round(x)) for x in src.frame_range)
W = arm.matrix_world; Wq = W.to_quaternion()
def swap(n):
    if n.startswith('Left'): return 'Right' + n[4:]
    if n.startswith('Right'): return 'Left' + n[5:]
    return n
bones = list(arm.data.bones)
def depth(b): return len(b.parent_recursive)
order = sorted(bones, key=depth)
sc.frame_set(f0)
nrm = (W @ arm.pose.bones['RightUpLeg'].head) - (W @ arm.pose.bones['LeftUpLeg'].head); nrm.z = 0; nrm.normalize()
c0 = (W @ arm.pose.bones['Hips'].head).copy()
def mq(q):
    v = Vector((q.x, q.y, q.z)); v2 = -v + 2 * v.dot(nrm) * nrm
    return Quaternion((q.w, v2.x, v2.y, v2.z))
def mp(p): return p - 2 * (p - c0).dot(nrm) * nrm
# the bind pose faces another way than the clip (bind +X, clips -Y): turn the rest reference into the clip's facing first, so the
# mirrored delta does not also mirror that turn (which flips the facing)
lat_b = (W @ arm.data.bones['RightUpLeg'].head_local) - (W @ arm.data.bones['LeftUpLeg'].head_local); lat_b.z = 0; lat_b.normalize()
G = lat_b.rotation_difference(nrm)
rest = {b.name: G @ (W @ b.matrix_local).to_quaternion() for b in bones}
tR = {b.name: b.matrix_local.to_quaternion() for b in bones}
corr = {b.name: mq(rest[swap(b.name)]).inverted() @ rest[b.name] for b in bones}
frames = {}
for fr in range(f0, f1 + 1):
    sc.frame_set(fr)
    wq = {pb.name: (W @ pb.matrix).to_quaternion() for pb in arm.pose.bones}
    frames[fr] = ({b.name: mq(wq[swap(b.name)]) @ corr[b.name] for b in bones}, mp(W @ arm.pose.bones['Hips'].head))
act = bpy.data.actions.new(NAME); arm.animation_data.action = act
Winv = Wq.inverted(); rest_hip = W @ arm.data.bones['Hips'].head_local
for fr, (world, hip) in frames.items():
    for b in order:
        pb = arm.pose.bones[b.name]; pb.rotation_mode = 'QUATERNION'
        a_q = Winv @ world[b.name]
        if b.parent:
            basis = (Winv @ world[b.parent.name] @ (tR[b.parent.name].inverted() @ tR[b.name])).inverted() @ a_q
        else:
            basis = tR[b.name].inverted() @ a_q
        pb.rotation_quaternion = basis; pb.keyframe_insert('rotation_quaternion', frame=fr)
    pr = arm.pose.bones['Hips']; pr.location = tR['Hips'].inverted() @ (W.inverted().to_3x3() @ (hip - rest_hip))
    pr.keyframe_insert('location', frame=fr)
bpy.data.actions.remove(src)
trk = arm.animation_data.nla_tracks.new(); trk.name = NAME; st = trk.strips.new(NAME, f0, act)
if hasattr(st, 'action_slot') and len(act.slots): st.action_slot = act.slots[0]
arm.animation_data.action = None
for o in bpy.data.objects: o.select_set(o.type in ('ARMATURE', 'MESH'))
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True, export_animations=True, export_animation_mode='NLA_TRACKS',
                          export_force_sampling=True, export_yup=True)
print('MIRROR', SRC, '->', OUT, NAME, 'frames', f0, f1)
