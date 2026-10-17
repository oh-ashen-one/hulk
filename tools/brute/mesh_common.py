# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
# Shared helpers for the Brute mesh/skinning quality track (mesh_audit.py, mesh_poses.py, mesh_fix.py).
# Runs inside Blender (bpy). numpy is bundled with Blender.
import bpy, re, json, os
import numpy as np
from mathutils import Quaternion, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
SCR = os.path.expanduser('~/hulk-scratch')
OUTD = os.path.join(SCR, 'brute_mesh')
IDLE_RIG = os.path.join(SCR, 'brute_v2/motion/Emerald_Behemoth_idle_30fps.glb')
ANIM = os.path.join(SCR, 'brute_v5/brute.glb')
CLIPS_JSON = os.path.join(SCR, 'brute_v5/clips.json')


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = 30


def imp(f):
    before = set(bpy.data.objects)
    if f.lower().endswith('.fbx'):
        bpy.ops.import_scene.fbx(filepath=f, ignore_leaf_bones=False, automatic_bone_orientation=False)
    else:
        bpy.ops.import_scene.gltf(filepath=f)
    return [o for o in bpy.data.objects if o not in before]


def load_rig(f):
    """import a rigged glb; drop helper primitives (same filter as assemble_motion.py); return (armature, skinned mesh)"""
    objs = imp(f)
    for o in [o for o in objs if o.type == 'MESH' and re.match(r'(icosphere|sphere|plane|cube)', o.name.lower())]:
        objs.remove(o); bpy.data.objects.remove(o)
    arm = next(o for o in objs if o.type == 'ARMATURE')
    me = next(o for o in objs if o.type == 'MESH' and any(m.type == 'ARMATURE' for m in o.modifiers))
    return arm, me, objs


def rest_pose(arm):
    if arm.animation_data:
        arm.animation_data.action = None
        for t in list(arm.animation_data.nla_tracks): arm.animation_data.nla_tracks.remove(t)
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'; pb.rotation_quaternion = Quaternion(); pb.location = Vector(); pb.scale = Vector((1, 1, 1))


def load_anim_actions(f=ANIM):
    """import the assembled animated glb, keep only its actions (objects deleted). returns {clip: action}"""
    objs = imp(f)
    acts = {a.name: a for a in bpy.data.actions}
    for a in acts.values(): a.use_fake_user = True
    for o in objs: bpy.data.objects.remove(o)
    return acts


def assign(arm, act):
    arm.animation_data_create(); arm.animation_data.action = act
    if hasattr(act, 'slots') and len(act.slots) and hasattr(arm.animation_data, 'action_slot'):
        try: arm.animation_data.action_slot = act.slots[0]
        except Exception as ex: print('slot assign failed', ex)


def eval_co(me):
    """evaluated (deformed) vertex positions in world space, numpy (V,3)"""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = me.evaluated_get(dg)
    m = ev.to_mesh()
    co = np.empty(len(m.vertices) * 3, dtype=np.float64); m.vertices.foreach_get('co', co)
    ev.to_mesh_clear()
    co = co.reshape(-1, 3)
    M = np.array(me.matrix_world)
    return co @ M[:3, :3].T + M[:3, 3]


def rest_co(me):
    co = np.empty(len(me.data.vertices) * 3); me.data.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3); M = np.array(me.matrix_world)
    return co @ M[:3, :3].T + M[:3, 3]


def weights(me):
    """dense weight matrix (V, G) and group names"""
    names = [g.name for g in me.vertex_groups]
    W = np.zeros((len(me.data.vertices), len(names)))
    for v in me.data.vertices:
        for g in v.groups: W[v.index, g.group] = g.weight
    return W, names


def set_weights(me, W, names):
    for g in list(me.vertex_groups): me.vertex_groups.remove(g)
    vgs = [me.vertex_groups.new(name=n) for n in names]
    for j, vg in enumerate(vgs):
        idx = np.nonzero(W[:, j] > 0)[0]
        for i in idx: vg.add([int(i)], float(W[i, j]), 'REPLACE')


def weld_map(co, tol=1e-5):
    """map each vertex to a welded id (vertices at the same position = UV-seam splits). returns (wid (V,), nW)"""
    q = np.round(co / tol).astype(np.int64)
    _, wid = np.unique(q, axis=0, return_inverse=True)
    return wid.ravel(), int(wid.max()) + 1


def edges(me):
    e = np.empty(len(me.data.edges) * 2, dtype=np.int64); me.data.edges.foreach_get('vertices', e)
    return e.reshape(-1, 2)


def tris(me):
    me.data.calc_loop_triangles()
    t = np.empty(len(me.data.loop_triangles) * 3, dtype=np.int64); me.data.loop_triangles.foreach_get('vertices', t)
    return t.reshape(-1, 3)


def tri_area(co, T):
    return 0.5 * np.linalg.norm(np.cross(co[T[:, 1]] - co[T[:, 0]], co[T[:, 2]] - co[T[:, 0]]), axis=1)


def clip_times():
    try: return json.load(open(CLIPS_JSON))
    except Exception: return {}


def weld_mesh(me, tol=1e-5):
    """merge UV-seam vertex splits in place (weights must already match across duplicates); smooth per-position normals"""
    d = me.data
    co = rest_co(me); wid, nW = weld_map(co, tol)
    ln = np.empty(len(d.loops) * 3); d.corner_normals.foreach_get('vector', ln); ln = ln.reshape(-1, 3)
    lv = np.empty(len(d.loops), dtype=np.int64); d.loops.foreach_get('vertex_index', lv)
    VN = np.zeros((nW, 3)); np.add.at(VN, wid[lv], ln); VN /= np.maximum(1e-12, np.linalg.norm(VN, axis=1, keepdims=True))
    _, rep = np.unique(wid, return_index=True)
    key = {tuple(k): i for i, k in enumerate(np.round(co[rep] / tol).astype(np.int64))}
    prev = bpy.context.view_layer.objects.active
    for o in bpy.context.view_layer.objects: o.select_set(False)
    bpy.context.view_layer.objects.active = me; me.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=tol)
    bpy.ops.object.mode_set(mode='OBJECT')
    c2 = rest_co(me); ids = []
    for c in c2:
        i = key.get(tuple(np.round(c / tol).astype(np.int64)), -1)
        if i < 0: i = int(np.argmin(np.linalg.norm(co[rep] - c, axis=1)))
        ids.append(i)
    for a in ('sharp_face', 'sharp_edge'):
        if a in d.attributes: d.attributes.remove(d.attributes[a])
    d.normals_split_custom_set_from_vertices([tuple(VN[i]) for i in ids])
    if prev: bpy.context.view_layer.objects.active = prev
    return len(d.vertices)
