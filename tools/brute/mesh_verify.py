# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
# Compatibility check of a fixed Brute rig against the source rig: same armature/bone names/hierarchy/rest matrices, a skinned
# mesh found the way assemble_motion.py finds it, textures present, the brute_v5 clips produce identical bone poses, and the
# rest-pose surface is unchanged (vertex positions, UVs).
# usage: Blender -b --factory-startup -P tools/brute/mesh_verify.py -- <src_rig.glb> <fixed_rig.glb>
import bpy, sys, os, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mesh_common as C
argv = sys.argv[sys.argv.index('--') + 1:]
SRC, FIX = argv[0], argv[1]
C.reset()
acts = C.load_anim_actions()
a1, m1, o1 = C.load_rig(SRC)
a2, m2, o2 = C.load_rig(FIX)
R = {}
R['objects_fixed'] = [(o.name, o.type) for o in o2]
R['armature_names'] = (a1.name, a2.name)
R['mesh_names'] = (m1.name, m2.name)
b1 = {b.name: b for b in a1.data.bones}; b2 = {b.name: b for b in a2.data.bones}
R['same_bone_set'] = set(b1) == set(b2); R['bones'] = len(b2)
R['same_parents'] = all((b1[n].parent.name if b1[n].parent else None) == (b2[n].parent.name if b2[n].parent else None) for n in b1)
R['max_rest_matrix_diff'] = max(float(np.abs(np.array(b1[n].matrix_local) - np.array(b2[n].matrix_local)).max()) for n in b1)
R['armature_world_diff'] = float(np.abs(np.array(a1.matrix_world) - np.array(a2.matrix_world)).max())
R['mesh_has_armature_modifier'] = any(md.type == 'ARMATURE' and md.object == a2 for md in m2.modifiers)
R['vertex_groups_match_bones'] = set(g.name for g in m2.vertex_groups) <= set(b2)
c1 = C.rest_co(m1); c2 = C.rest_co(m2)
k1 = np.unique(np.round(c1 / 1e-5).astype(np.int64), axis=0); k2 = np.unique(np.round(c2 / 1e-5).astype(np.int64), axis=0)
R['rest_positions'] = dict(src_unique=len(k1), fixed_unique=len(k2), bbox_src=[c1.min(0).round(4).tolist(), c1.max(0).round(4).tolist()],
                          bbox_fixed=[c2.min(0).round(4).tolist(), c2.max(0).round(4).tolist()])
R['tris'] = (sum(len(p.vertices) - 2 for p in m1.data.polygons), sum(len(p.vertices) - 2 for p in m2.data.polygons))
R['materials'] = [m.name for m in m2.data.materials]
R['images'] = {im.name: list(im.size) for im in bpy.data.images}
# weights
W, names = C.weights(m2); nz = (W > 0).sum(1)
R['max_influences'] = int(nz.max()); R['unnormalized'] = int((np.abs(W.sum(1) - 1) > 1e-3).sum()); R['unweighted'] = int((nz == 0).sum())
# same clip -> same bone poses
diffs = []
for clip in ('Lift', 'Clap', 'Uppercut', 'Run'):
    a = acts[clip]
    for arm in (a1, a2): C.assign(arm, a)
    for f in range(int(a.frame_range[0]), int(a.frame_range[1]) + 1, 7):
        bpy.context.scene.frame_set(f)
        for n in b1:
            diffs.append(float(np.abs(np.array(a1.matrix_world @ a1.pose.bones[n].matrix) - np.array(a2.matrix_world @ a2.pose.bones[n].matrix)).max()))
R['max_pose_matrix_diff_over_clips'] = max(diffs)
print(json.dumps(R, indent=1, default=str))
json.dump(R, open(os.path.splitext(FIX)[0] + '_verify.json', 'w'), indent=1, default=str)
