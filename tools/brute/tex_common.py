"""Shared helpers for the Brute vein/cloth normal-map bake (run inside Blender 5).

Loads the bind-pose skinned mesh, bakes its world transform into the vertex data
(so Object coords == world coords: Z up, arms along +/-Y in the T-pose), and
computes smooth per-vertex region attributes from the Mixamo skin weights:

  vein_amt   0..1   how strongly veins may appear (forearm 1, hand back, biceps,
                    neck sides, upper chest/shoulder front; 0 on face/back/legs)
  vein_sec   0..1   where the thinner secondary branch layer is allowed (limbs)
  limb_dir   vec3   per-vertex vessel run direction from the bone chain
  shorts_v   0..1   purple-shorts mask sampled from the D texture at vertices
  hem_d      m      geodesic distance inside the shorts from the leg-opening edge
  hem        0/1    hem_d < 8 cm

Attributes are smoothed over a position-welded graph, so duplicated seam
vertices (glTF splits at every UV seam) always get identical values -> no seams.
"""
import bpy
import numpy as np

GLB = '/Users/midir/hulk-scratch/brute_mesh/brute_rigged_subd.glb'
TEX = '/Users/midir/hulk-scratch/brute_v2/rig/textures/'
OUT = '/Users/midir/hulk-scratch/brute_tex/'


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def load_mesh():
    bpy.ops.import_scene.gltf(filepath=GLB)
    mesh = [o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith('SM_Character_Brute')][0]
    for m in list(mesh.modifiers):
        mesh.modifiers.remove(m)
    mw = mesh.matrix_world.copy()
    mesh.parent = None
    mesh.matrix_world = mw
    bpy.context.view_layer.objects.active = mesh
    for o in bpy.context.selected_objects:
        o.select_set(False)
    mesh.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for o in list(bpy.data.objects):
        if o is not mesh:
            bpy.data.objects.remove(o, do_unlink=True)
    return mesh


def _weights(obj, nv):
    names = [g.name for g in obj.vertex_groups]
    W = {n: np.zeros(nv, np.float32) for n in names}
    idx2name = {g.index: g.name for g in obj.vertex_groups}
    for v in obj.data.vertices:
        for ge in v.groups:
            W[idx2name[ge.group]][v.index] = ge.weight
    return W


def _smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def _weld(co):
    key = np.round(co / 1e-5).astype(np.int64)
    _, inv = np.unique(key, axis=0, return_inverse=True)
    return inv.ravel()


def _smooth(vals, inv, edges_u, nu, iters):
    """Laplacian smoothing on the welded graph. vals: per-vertex (nv,) array."""
    u = np.bincount(inv, weights=vals, minlength=nu) / np.maximum(np.bincount(inv, minlength=nu), 1)
    a, b = edges_u[:, 0], edges_u[:, 1]
    deg = np.bincount(a, minlength=nu) + np.bincount(b, minlength=nu)
    for _ in range(iters):
        s = np.bincount(a, weights=u[b], minlength=nu) + np.bincount(b, weights=u[a], minlength=nu)
        u = 0.5 * u + 0.5 * s / np.maximum(deg, 1)
    return u[inv]


def compute_attributes(obj):
    me = obj.data
    nv = len(me.vertices)
    co = np.empty(nv * 3, np.float32); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
    nr = np.empty(nv * 3, np.float32); me.vertices.foreach_get('normal', nr); nr = nr.reshape(-1, 3)
    W = _weights(obj, nv)
    inv = _weld(co)
    nu = inv.max() + 1
    ed = np.empty(len(me.edges) * 2, np.int64); me.edges.foreach_get('vertices', ed)
    eu = inv[ed.reshape(-1, 2)]
    eu = eu[eu[:, 0] != eu[:, 1]]
    # welded normals (average over seam duplicates)
    nrw = np.stack([np.bincount(inv, weights=nr[:, i], minlength=nu) for i in range(3)], 1)
    nrw /= np.linalg.norm(nrw, axis=1, keepdims=True) + 1e-9
    n = nrw[inv]

    def cen(name):
        w = W[name]
        return (co * w[:, None]).sum(0) / max(w.sum(), 1e-6)
    fwd = (cen('LeftToeBase') + cen('RightToeBase')) / 2 - (cen('LeftFoot') + cen('RightFoot')) / 2
    fwd[2] = 0; fwd /= np.linalg.norm(fwd)
    up = np.array([0.0, 0.0, 1.0])
    print('[tex] forward', fwd)
    # Arms hang in an A-pose (not a T-pose): build a per-vertex "vessel run"
    # direction from the bone chain (always pointing distally / upward).
    def unit(v):
        return v / (np.linalg.norm(v) + 1e-9)
    dirs = {}
    for s in ('Left', 'Right'):
        dirs[s + 'Arm'] = unit(cen(s + 'ForeArm') - cen(s + 'Arm'))
        dirs[s + 'ForeArm'] = unit(cen(s + 'Hand') - cen(s + 'ForeArm'))
        dirs[s + 'Hand'] = unit(cen(s + 'HandMiddle1') - cen(s + 'Hand'))
        dirs[s + 'Shoulder'] = unit(cen(s + 'Arm') - cen('Spine2') + 0.35 * up)
    dirs['Neck'] = unit(cen('Head') - cen('Spine2'))
    dirs['Head'] = dirs['Neck']
    dirs['Spine2'] = up
    ld = np.zeros((nv, 3))
    for b, d in dirs.items():
        ld += W[b][:, None] * d[None, :]
    # chest: fan the vessels toward the nearer shoulder
    side = np.sign(co[:, 1])[:, None]
    chest_dir = np.where(side > 0, dirs['LeftShoulder'], dirs['RightShoulder'])
    ld += W['Spine2'][:, None] * (chest_dir - up)   # replace the Spine2 'up' share
    ld += 1e-4 * up
    # local pivot (skin-weighted bone centroid): the shader compresses (P - ctr)
    # along ld; using a nearby pivot keeps d-variation from warping the pattern.
    ctr = np.zeros((nv, 3)); wsum = np.zeros(nv)
    for b in list(dirs) + ['Spine1', 'Spine', 'Hips']:
        ctr += W[b][:, None] * cen(b)[None, :]; wsum += W[b]
    ctr = np.where(wsum[:, None] > 1e-3, ctr / np.maximum(wsum, 1e-6)[:, None], co)
    for i in range(3):
        ld[:, i] = _smooth(ld[:, i], inv, eu, nu, 40)
        ctr[:, i] = _smooth(ctr[:, i], inv, eu, nu, 40)
    ld /= np.linalg.norm(ld, axis=1, keepdims=True) + 1e-9

    nf = n @ fwd
    head = W['Head']
    forearm = W['LeftForeArm'] + W['RightForeArm']
    # back of the hand = surface facing away from the body (hands hang palms-in)
    hand = np.zeros(nv)
    for s in ('Left', 'Right'):
        out = cen(s + 'Hand') - cen('Spine2'); out[2] = 0; out = unit(out)
        hand += W[s + 'Hand'] * _smoothstep(0.05, 0.5, n @ out)
    upper = np.zeros(nv)
    for s in ('Left', 'Right'):
        # biceps (front) and inner upper arm (toward the body) favoured, triceps lighter
        inward = cen('Spine2') - cen(s + 'Arm'); inward[2] = 0; inward = unit(inward)
        upper += W[s + 'Arm'] * np.clip(0.35 + _smoothstep(-0.3, 0.6, nf + 0.7 * (n @ inward)), 0, 1)
    nk = W['Neck'] / max(W['Neck'].max(), 1e-6)
    neck = _smoothstep(0.1, 0.5, nk) * _smoothstep(0.2, 0.65, np.abs(n[:, 1]) + 0.2 * nf) * _smoothstep(-0.45, 0.0, nf)
    z = co[:, 2]
    zsp2 = cen('Spine2')[2]
    # upper chest band (upper pec toward the shoulder/deltoid front), not the clavicle/traps
    chest = (W['Spine2'] + W['LeftShoulder'] + W['RightShoulder'] + W['Spine1']) \
        * _smoothstep(0.15, 0.5, nf) * _smoothstep(zsp2 - 0.22, zsp2 - 0.10, z) \
        * (1 - _smoothstep(zsp2 + 0.04, zsp2 + 0.12, z))
    chest *= _smoothstep(0.13, 0.25, np.abs(co[:, 1]))
    # v2: upper arm / shoulder toned down (scratchy up close); forearms stay strong
    amt = np.clip(1.0 * forearm + 0.85 * hand + 0.45 * upper + 0.8 * neck + 0.45 * chest, 0, 1)
    amt *= 1.0 - _smoothstep(0.5, 0.85, head)   # face / skull
    # torso back (shoulder blades, traps) never gets veins
    torso = W['Spine2'] + W['Spine1'] + W['Spine'] + W['LeftShoulder'] + W['RightShoulder'] + W['Neck']
    amt *= 1.0 - np.clip(torso, 0, 1) * (1 - _smoothstep(-0.35, 0.05, nf))
    amt = np.clip(_smooth(amt, inv, eu, nu, 25), 0, 1)
    # secondary (thin branch) layer only on the limbs; neck/chest keep a few big vessels
    # forearm/hand share: thin branch layer only here, and denser trunks here
    sec = np.clip(1.0 * forearm + 0.9 * (W['LeftHand'] + W['RightHand']), 0, 1) * (1.0 - _smoothstep(0.5, 0.85, head))
    axis = np.clip(_smooth(sec, inv, eu, nu, 25), 0, 1)

    # shorts mask at vertices from base colour
    D = bpy.data.images.load(TEX + 'SM_Character_Brute_D.png', check_existing=True)
    w_, h_ = D.size
    px = np.empty(w_ * h_ * 4, np.float32); D.pixels.foreach_get(px); px = px.reshape(h_, w_, 4)
    uv = np.zeros((nv, 2)); cnt = np.zeros(nv)
    luv = np.empty(len(me.loops) * 2, np.float32); me.uv_layers.active.data.foreach_get('uv', luv)
    lv = np.empty(len(me.loops), np.int64); me.loops.foreach_get('vertex_index', lv)
    luv = luv.reshape(-1, 2)
    np.add.at(uv, lv, luv); np.add.at(cnt, lv, 1)
    uv /= np.maximum(cnt, 1)[:, None]
    xi = np.clip((uv[:, 0] % 1) * w_, 0, w_ - 1).astype(int)
    yi = np.clip((uv[:, 1] % 1) * h_, 0, h_ - 1).astype(int)
    c = px[yi, xi, :3]
    purple = ((c[:, 2] > c[:, 1] + 0.02) & (c[:, 0] > c[:, 1] + 0.01)).astype(np.float32)
    # shorts live around the hips; kill stray purple texels elsewhere
    hipw = W['Hips'] + W['LeftUpLeg'] + W['RightUpLeg'] + W['Spine']
    purple *= (hipw > 0.3)
    shorts = _smooth(purple, inv, eu, nu, 6)
    # torn hem: geodesic distance (m) inside the shorts from the LEG-OPENING edge
    # (waistband edge excluded), relaxed over the welded edge graph
    pu = np.bincount(inv, weights=purple, minlength=nu) / np.maximum(np.bincount(inv, minlength=nu), 1)
    cu = np.stack([np.bincount(inv, weights=co[:, i], minlength=nu) for i in range(3)], 1) \
        / np.maximum(np.bincount(inv, minlength=nu), 1)[:, None]
    inside = pu > 0.5
    a_, b_ = eu[:, 0], eu[:, 1]
    border = np.zeros(nu, bool)
    cross = inside[a_] != inside[b_]
    border[a_[cross & inside[a_]]] = True; border[b_[cross & inside[b_]]] = True
    # the shorts are a separate cloth shell: its cut leg openings are OPEN mesh
    # boundaries (welded edges used by a single face), not purple/skin borders
    lt = np.empty(len(me.polygons), np.int64); me.polygons.foreach_get('loop_total', lt)
    ls = np.empty(len(me.polygons), np.int64); me.polygons.foreach_get('loop_start', ls)
    lvi = np.empty(len(me.loops), np.int64); me.loops.foreach_get('vertex_index', lvi)
    nxt = np.arange(len(me.loops)) + 1
    last = ls + lt - 1
    nxt[last] = ls
    wa, wb = inv[lvi], inv[lvi[nxt]]
    key = np.minimum(wa, wb) * nu + np.maximum(wa, wb)
    uk, cnt = np.unique(key, return_counts=True)
    bk = uk[cnt == 1]
    bnd = np.zeros(nu, bool); bnd[bk // nu] = True; bnd[bk % nu] = True
    border |= bnd & inside
    print('[tex] open-boundary shorts verts', int((bnd & inside).sum()))
    zin = cu[inside, 2]
    z_hip = cen('Hips')[2]
    print('[tex] shorts z range %.3f..%.3f hips z %.3f' % (zin.min(), zin.max(), z_hip))
    border &= cu[:, 2] < z_hip            # leg openings / tears only, not the waistband
    el = np.linalg.norm(cu[a_] - cu[b_], axis=1)
    dist = np.where(border, 0.0, 1e3)
    for _ in range(400):
        nd = dist.copy()
        np.minimum.at(nd, a_, dist[b_] + el)
        np.minimum.at(nd, b_, dist[a_] + el)
        nd[~inside] = 1e3
        nd[border] = 0.0
        if np.allclose(nd, dist):
            break
        dist = nd
    hem_d = np.clip(dist, 0, 0.2)[inv]
    print('[tex] hem verts (<8cm)', int((hem_d < 0.08).sum()), 'seeds', int(border.sum()))
    hem = (hem_d < 0.08).astype(np.float32)
    if 'limb_dir' in me.attributes:
        me.attributes.remove(me.attributes['limb_dir'])
    la = me.attributes.new('limb_dir', 'FLOAT_VECTOR', 'POINT')
    la.data.foreach_set('vector', ld.astype(np.float32).ravel())
    if 'limb_ctr' in me.attributes:
        me.attributes.remove(me.attributes['limb_ctr'])
    lc = me.attributes.new('limb_ctr', 'FLOAT_VECTOR', 'POINT')
    lc.data.foreach_set('vector', ctr.astype(np.float32).ravel())
    for name, val in (('vein_amt', amt), ('vein_sec', axis), ('shorts_v', shorts), ('hem', hem), ('hem_d', hem_d)):
        if name in me.attributes:
            me.attributes.remove(me.attributes[name])
        a = me.attributes.new(name, 'FLOAT', 'POINT')
        a.data.foreach_set('value', val.astype(np.float32))
    return dict(fwd=fwd)
