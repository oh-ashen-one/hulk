# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
# Bone-heat (Blender automatic weights) reference weights for the Brute mesh: a temporary armature with the SAME bone heads but
# anatomical tails (each bone points at its child; glTF-imported bones point sideways, which breaks heat weighting) is bound to
# a welded copy of the mesh. Writes the welded weight matrix (same welded order as mesh_fix.py) to <out.npy>.
# usage: Blender -b --factory-startup -P tools/brute/mesh_heat.py -- <rig.glb> <out.npy>
import bpy, sys, os
import numpy as np
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mesh_common as C
argv = sys.argv[sys.argv.index('--') + 1:]
RIG, OUT = argv[0], argv[1]
C.reset()
arm, me, objs = C.load_rig(RIG)
for o in objs:
    if o not in (arm, me): bpy.data.objects.remove(o)
C.rest_pose(arm)
names = [g.name for g in me.vertex_groups]
rest = C.rest_co(me); wid, nW = C.weld_map(rest); _, rep = np.unique(wid, return_index=True)
# temp armature
heads = {b.name: (arm.matrix_world @ b.head_local) for b in arm.data.bones}
par = {b.name: (b.parent.name if b.parent else None) for b in arm.data.bones}
kids = {n: [c for c, p in par.items() if p == n] for n in heads}
PREF = {'Hips': 'Spine', 'Spine2': 'Neck', 'LeftShoulder': 'LeftArm', 'RightShoulder': 'RightArm', 'LeftHand': 'LeftHandMiddle', 'RightHand': 'RightHandMiddle',
        'LeftUpLeg': 'LeftLeg', 'RightUpLeg': 'RightLeg', 'LeftFoot': 'LeftToeBase', 'RightFoot': 'RightToeBase'}
ad = bpy.data.armatures.new('heat'); ao = bpy.data.objects.new('heat', ad); bpy.context.scene.collection.objects.link(ao)
bpy.context.view_layer.objects.active = ao; bpy.ops.object.mode_set(mode='EDIT')
for n in heads:
    eb = ad.edit_bones.new(n); h = heads[n]; eb.head = h
    k = PREF.get(n) or (kids[n][0] if len(kids[n]) == 1 else None)
    if k: t = heads[k]
    else:
        p = par[n]; d = (h - heads[p]) if p else Vector((0, 0, 0.1))
        if n == 'Head': d = Vector((0, 0, 0.25))
        t = h + d.normalized() * max(0.03, min(0.25, d.length * 0.8))
    if (t - h).length < 1e-4: t = h + Vector((0, 0, 0.03))
    eb.tail = t
for n in heads:
    if par[n]: ad.edit_bones[n].parent = ad.edit_bones[par[n]]
bpy.ops.object.mode_set(mode='OBJECT')
# welded copy of the mesh
m2 = me.copy(); m2.data = me.data.copy(); bpy.context.scene.collection.objects.link(m2)
m2.parent = None; m2.matrix_world = me.matrix_world.copy()
for md in list(m2.modifiers): m2.modifiers.remove(md)
for g in list(m2.vertex_groups): m2.vertex_groups.remove(g)
import bmesh
bm = bmesh.new(); bm.from_mesh(m2.data); bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5); bm.to_mesh(m2.data); bm.free()
print('welded copy verts', len(m2.data.vertices), 'expected', nW)
for o in bpy.context.scene.objects: o.select_set(False)
m2.select_set(True); ao.select_set(True); bpy.context.view_layer.objects.active = ao
bpy.ops.object.parent_set(type='ARMATURE_AUTO')
# map welded copy verts -> our welded ids by position
co2 = np.array([m2.matrix_world @ v.co for v in m2.data.vertices])
q = {tuple(np.round(c / 1e-5).astype(np.int64)): i for i, c in enumerate(co2)}
X0 = rest[rep]; order = [q.get(tuple(np.round(c / 1e-5).astype(np.int64)), -1) for c in X0]
miss = sum(1 for o in order if o < 0); print('unmatched', miss)
Wh = np.zeros((nW, len(names)))
gidx = {g.index: g.name for g in m2.vertex_groups}
for i, o in enumerate(order):
    if o < 0: continue
    for g in m2.data.vertices[o].groups:
        n = gidx[g.group]
        if n in names: Wh[i, names.index(n)] = g.weight
s = Wh.sum(1); print('heat unweighted verts', int((s < 1e-6).sum()))
np.save(OUT, Wh)
print('WROTE', OUT)
