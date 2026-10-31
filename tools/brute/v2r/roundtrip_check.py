# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
# Compare two motion files on the SHIPPED rig the way assemble_motion.py sees them (30 fps scene, shipped rig glb imported, each
# file's action copied onto it): max mesh vertex delta on sampled frames + max bone-head delta on every frame.
# Used to prove the shipped -> aligned -> shipped round trip of v2r_rig.py / make_test_fit.py / export_clip.py.
#   Blender -b --factory-startup -P tools/brute/v2r/roundtrip_check.py -- <reference.glb> <ref action name> <candidate.glb> [frames=12] [gate_mm=1.0]
import os
import re
import sys

import bpy
import numpy as np
from mathutils import Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v2r_rig as R  # noqa: E402

argv = sys.argv[sys.argv.index('--') + 1:]
REF, REF_ACT, CAND = argv[0], argv[1], argv[2]
NS = int(argv[3]) if len(argv) > 3 else 12
GATE = float(argv[4]) if len(argv) > 4 else 1.0

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.fps = 30
rig_objs = R.import_glb(R.SHIPPED_RIG)
for o in [o for o in rig_objs if o.type == 'MESH' and re.match(r'(icosphere|sphere)', o.name.lower())]:
    rig_objs.remove(o); bpy.data.objects.remove(o)
rig = next(o for o in rig_objs if o.type == 'ARMATURE')
mesh = next(o for o in rig_objs if o.type == 'MESH')
for a in list(bpy.data.actions):
    bpy.data.actions.remove(a)
if rig.animation_data:
    rig.animation_data_clear()
for pb in rig.pose.bones:
    pb.rotation_mode = 'QUATERNION'; pb.matrix_basis = Matrix.Identity(4)


def take(path, name=None):
    objs = R.import_glb(path)
    src = next(o for o in objs if o.type == 'ARMATURE')
    if name:
        act = bpy.data.actions.get(name) or next(a for a in bpy.data.actions if a.name.split('.')[0] == name and a.users)
    else:
        act = src.animation_data.action
    ks = src.matrix_world.to_scale().x / rig.matrix_world.to_scale().x
    act = act.copy(); act.name = 'cmp_' + (name or os.path.basename(path))
    for o in objs:
        bpy.data.objects.remove(o)
    return act, ks


A, ksA = take(REF, REF_ACT)
B, ksB = take(CAND)
fa = tuple(int(round(x)) for x in R.key_range(A))
fb = tuple(int(round(x)) for x in R.key_range(B))
print('ROUNDTRIP ref %s:%s frames %s (location scale %.4f); candidate %s frames %s (location scale %.4f)' % (
    os.path.basename(REF), REF_ACT, fa, ksA, os.path.basename(CAND), fb, ksB))
n = min(fa[1] - fa[0], fb[1] - fb[0])
# both actions are compared as stored (armature-space values, no location rescale): an assembled brute.glb carries the game-height
# object scale on its armature (1.0987), which is not part of the action; assemble would rescale its location keys only if it were
# fed back in as a motion file
if abs(ksA - ksB) > 1e-4:
    print('ROUNDTRIP note: armature object scales differ (%.4f vs %.4f); actions compared unscaled in armature space' % (ksA, ksB))


def heads(act, frames):
    R.assign_action(rig, act); out = []
    for f in frames:
        sc.frame_set(f); out.append(np.array([list(pb.head) for pb in rig.pose.bones]))
    return np.array(out)


def verts(act, frames):
    R.assign_action(rig, act); out = []
    for f in frames:
        sc.frame_set(f); out.append(R.mesh_world(mesh))
    return out


allf = list(range(0, n + 1))
hA, hB = heads(A, [fa[0] + f for f in allf]), heads(B, [fb[0] + f for f in allf])
dh = np.linalg.norm(hA - hB, axis=2) * 1000
samp = sorted(set(int(round(x)) for x in np.linspace(0, n, NS)))
vA, vB = verts(A, [fa[0] + f for f in samp]), verts(B, [fb[0] + f for f in samp])
dv = [float(np.linalg.norm(a - b, axis=1).max()) * 1000 for a, b in zip(vA, vB)]
res = 'PASS' if max(dv) <= GATE and fa[1] - fa[0] == fb[1] - fb[0] else 'FAIL'
print('ROUNDTRIP bone heads, every frame (%d frames x %d bones): max %.4f mm (frame %d)' % (len(allf), dh.shape[1], dh.max(), int(dh.max(1).argmax())))
print('ROUNDTRIP mesh %d verts on frames %s: per-frame max mm %s' % (len(vA[0]), samp, [round(x, 4) for x in dv]))
print('ROUNDTRIP_GATE max_vertex_delta_mm %.4f frames %d lengths %d/%d %s (rig-armature metres; shipped rig object scale 1)' % (
    max(dv), len(samp), fa[1] - fa[0] + 1, fb[1] - fb[0] + 1, res))
