# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
# Drop-in check: the corrective glb must have the same base mesh (positions, UVs, skin weights), skeleton and bind pose as the
# source rig; lists its shape keys. Positions are compared per welded position (glTF exporters may split vertices differently).
# usage: Blender -b --factory-startup -P tools/brute/mesh_corrective_check.py -- <source.glb> <corr.glb>
import bpy, sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mesh_common as C

argv = sys.argv[sys.argv.index('--') + 1:]
def load(f):
    C.reset(); arm, me, objs = C.load_rig(f); C.rest_pose(arm); bpy.context.view_layer.update()
    co = C.rest_co(me); W, names = C.weights(me)
    uv = np.empty(len(me.data.loops) * 2); me.data.uv_layers.active.data.foreach_get('uv', uv); uv = uv.reshape(-1, 2)
    lv = np.empty(len(me.data.loops), dtype=np.int64); me.data.loops.foreach_get('vertex_index', lv)
    bones = {b.name: (b.parent.name if b.parent else None, np.array(b.matrix_local)) for b in arm.data.bones}
    keys = [kb.name for kb in me.data.shape_keys.key_blocks] if me.data.shape_keys else []
    return dict(co=co, W=W, names=names, uv=uv, lv=lv, bones=bones, keys=keys, nv=len(me.data.vertices), nf=len(me.data.polygons),
                arm_mw=np.array(arm.matrix_world), me_mw=np.array(me.matrix_world), mats=[m.name for m in me.data.materials])
a, b = load(argv[0]), load(argv[1])
print('verts %d vs %d, faces %d vs %d, materials %s vs %s' % (a['nv'], b['nv'], a['nf'], b['nf'], a['mats'], b['mats']))
print('shape keys:', b['keys'])
q = lambda c: np.round(c / 1e-5).astype(np.int64)
from mathutils.kdtree import KDTree
kd = KDTree(len(a['co']))
for i, c in enumerate(a['co']): kd.insert(c, i)
kd.balance()
nn = [kd.find(c) for c in b['co']]; idx = np.array([n[1] for n in nn]); dist = np.array([n[2] for n in nn])
print('positions: max distance corr vertex -> nearest source vertex %.2e m (float32 round trip ~1e-7)' % dist.max())
idx[dist > 1e-5] = -1
Wb = b['W'][:, [b['names'].index(n) for n in a['names']]]
print('skin weights max |diff| (same position): %.2e' % np.abs(Wb[idx >= 0] - a['W'][idx[idx >= 0]]).max())
# UVs: set of (position, uv) corner pairs
# UVs: per corner of the corr mesh, the source corner at the same position with the closest uv
from collections import defaultdict
wa, _ = C.weld_map(a['co'])
src = defaultdict(list)
for v, u in zip(a['lv'], a['uv']): src[wa[v]].append(u)
du = np.array([np.abs(np.array(src[wa[idx[v]]]) - u).max(1).min() if idx[v] >= 0 else 9 for v, u in zip(b["lv"], b["uv"])])
print('UV: corners %d vs %d, max |uv diff| to the matching source corner %.2e' % (len(a['uv']), len(b['uv']), du.max()))
bd = max(np.abs(a['bones'][n][1] - b['bones'][n][1]).max() for n in a['bones'])
print('bones %d vs %d, same names %s, same parents %s, bind matrix max diff %.2e, armature/mesh world diff %.2e / %.2e' % (
    len(a['bones']), len(b['bones']), set(a['bones']) == set(b['bones']), all(a['bones'][n][0] == b['bones'][n][0] for n in a['bones']), bd,
    np.abs(a['arm_mw'] - b['arm_mw']).max(), np.abs(a['me_mw'] - b['me_mw']).max()))
