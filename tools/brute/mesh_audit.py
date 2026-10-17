# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
# Static audit of a rigged Brute glb: mesh stats, manifoldness, loose parts, normals, UVs, weights, seam-split weight mismatch.
# usage: Blender -b --factory-startup -P tools/brute/mesh_audit.py -- <rig.glb> <out.json>
import bpy, bmesh, sys, os, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mesh_common as C

argv = sys.argv[sys.argv.index('--') + 1:]
RIG, OUT = argv[0], argv[1]
C.reset()
arm, me, _ = C.load_rig(RIG)
d = me.data
R = {}
R['verts'] = len(d.vertices); R['polys'] = len(d.polygons); R['tris'] = sum(len(p.vertices) - 2 for p in d.polygons)
R['edges'] = len(d.edges)
co = C.rest_co(me)
wid, nW = C.weld_map(co)
R['welded_verts'] = nW; R['seam_split_verts'] = R['verts'] - nW
R['bbox'] = [co.min(0).round(4).tolist(), co.max(0).round(4).tolist()]

bm = bmesh.new(); bm.from_mesh(d)
R['bm_nonmanifold_edges_raw'] = sum(1 for e in bm.edges if not e.is_manifold)
R['bm_boundary_edges_raw'] = sum(1 for e in bm.edges if e.is_boundary)
# welded copy: real topology (UV seams merged)
bmw = bm.copy()
bmesh.ops.remove_doubles(bmw, verts=bmw.verts, dist=1e-5)
R['welded_bm_verts'] = len(bmw.verts)
R['welded_nonmanifold_edges'] = sum(1 for e in bmw.edges if not e.is_manifold and not e.is_boundary)
R['welded_boundary_edges'] = sum(1 for e in bmw.edges if e.is_boundary)
R['welded_wire_edges'] = sum(1 for e in bmw.edges if e.is_wire)
R['welded_nonmanifold_verts'] = sum(1 for v in bmw.verts if not v.is_manifold)
# loose parts (welded)
bmw.verts.ensure_lookup_table()
seen = set(); parts = []
for v in bmw.verts:
    if v.index in seen: continue
    stack = [v]; seen.add(v.index); n = 0; idx = []
    while stack:
        x = stack.pop(); n += 1; idx.append(x.index)
        for e in x.link_edges:
            y = e.other_vert(x)
            if y.index not in seen: seen.add(y.index); stack.append(y)
    zs = [bmw.verts[i].co.z for i in idx]
    parts.append(dict(n=n, zmin=round(min(zs), 3), zmax=round(max(zs), 3)))
parts.sort(key=lambda p: -p['n'])
R['loose_parts'] = len(parts); R['parts_top'] = parts[:15]
R['parts_small(<50v)'] = sum(1 for p in parts if p['n'] < 50)
# degenerate faces / tiny or sliver triangles
areas = np.array([f.calc_area() for f in bmw.faces])
R['face_area_median'] = float(np.median(areas))
R['degenerate_faces(<1e-9)'] = int((areas < 1e-9).sum())
def sliver(f):
    ls = sorted(e.calc_length() for e in f.edges)
    return ls[-1] / max(1e-9, ls[0])
asp = np.array([sliver(f) for f in bmw.faces])
R['tri_aspect_p50_p99_max'] = [float(np.percentile(asp, 50)), float(np.percentile(asp, 99)), float(asp.max())]
R['sliver_faces(aspect>20)'] = int((asp > 20).sum())
# normal consistency on welded topology: edges whose two faces disagree in winding
inc = 0
for e in bmw.edges:
    if len(e.link_faces) == 2:
        f1, f2 = e.link_faces
        # consistent winding: the shared edge runs in opposite directions in the two faces
        def dirn(f):
            vs = list(f.verts); i = vs.index(e.verts[0]); return vs[(i + 1) % len(vs)] == e.verts[1]
        if dirn(f1) == dirn(f2): inc += 1
R['inconsistent_winding_edges'] = inc
# fraction of face normals pointing away from the body axis (rough outward check)
c = np.array([f.calc_center_median()[:] for f in bmw.faces]); n = np.array([f.normal[:] for f in bmw.faces])
R['faces_total_welded'] = len(bmw.faces)
bm.free(); bmw.free()

# shading: sharp flags, custom normals, seam normal mismatch
sf = np.zeros(len(d.polygons), dtype=bool)
if 'sharp_face' in d.attributes: d.attributes['sharp_face'].data.foreach_get('value', sf)
R['sharp_faces'] = int(sf.sum())
se = np.zeros(len(d.edges), dtype=bool)
if 'sharp_edge' in d.attributes: d.attributes['sharp_edge'].data.foreach_get('value', se)
R['sharp_edges'] = int(se.sum())
R['has_custom_normals'] = 'custom_normal' in d.attributes
ln = np.empty(len(d.loops) * 3); d.corner_normals.foreach_get('vector', ln); ln = ln.reshape(-1, 3)
lv = np.empty(len(d.loops), dtype=np.int64); d.loops.foreach_get('vertex_index', lv)
# per welded vertex, max angle between corner normals
order = np.argsort(wid[lv]); g = wid[lv][order]; nn = ln[order]
mean = np.zeros((nW, 3)); np.add.at(mean, wid[lv], ln)
mean /= np.maximum(1e-9, np.linalg.norm(mean, axis=1, keepdims=True))
dev = np.degrees(np.arccos(np.clip((ln * mean[wid[lv]]).sum(1), -1, 1)))
vdev = np.zeros(nW); np.maximum.at(vdev, wid[lv], dev)
R['corner_normal_split_deg_p99_max'] = [float(np.percentile(vdev, 99)), float(vdev.max())]
R['welded_verts_with_normal_split>10deg'] = int((vdev > 10).sum())

# UVs
uv = np.empty(len(d.loops) * 2); d.uv_layers.active.data.foreach_get('uv', uv); uv = uv.reshape(-1, 2)
R['uv_range'] = [uv.min(0).round(4).tolist(), uv.max(0).round(4).tolist()]
R['uv_outside_0_1'] = int(((uv < -1e-4) | (uv > 1 + 1e-4)).any(1).sum())
# UV flipped triangles (signed area sign vs majority)
d.calc_loop_triangles()
lt = np.empty(len(d.loop_triangles) * 3, dtype=np.int64); d.loop_triangles.foreach_get('loops', lt); lt = lt.reshape(-1, 3)
a = uv[lt[:, 1]] - uv[lt[:, 0]]; b = uv[lt[:, 2]] - uv[lt[:, 0]]
sa = a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0]
maj = np.sign(np.median(sa))
R['uv_flipped_tris'] = int((np.sign(sa) == -maj).sum()); R['uv_zero_area_tris'] = int((np.abs(sa) < 1e-10).sum())
# texel density: uv area / world area, relative spread
T = C.tris(me); wa = C.tri_area(co, T); ua = np.abs(sa) / 2
dens = np.sqrt(ua / np.maximum(wa, 1e-12)) * 2048
ok = wa > 1e-10
R['texel_density_px_per_unit_p5_p50_p95'] = np.percentile(dens[ok], [5, 50, 95]).round(1).tolist()
R['height_units'] = float(co[:, 2].max() - co[:, 2].min())
R['texel_px_per_m_at_2.6m_p50'] = float(np.percentile(dens[ok], 50) * R['height_units'] / 2.6)

# weights
W, names = C.weights(me)
nz = (W > 1e-6).sum(1)
s = W.sum(1)
R['groups'] = names
R['influences_hist'] = {int(k): int((nz == k).sum()) for k in range(0, int(nz.max()) + 1)}
R['verts_>4_influences'] = int((nz > 4).sum())
R['unnormalized(|sum-1|>1e-3)'] = int((np.abs(s - 1) > 1e-3).sum()); R['weight_sum_min_max'] = [float(s.min()), float(s.max())]
R['unweighted_verts'] = int((nz == 0).sum())
R['tiny_weights(<0.01)'] = int(((W > 0) & (W < 0.01)).sum())
# seam split mismatch: welded duplicates with different weights (cracks under deformation)
mx = np.zeros((nW, W.shape[1])); mn = np.full((nW, W.shape[1]), 9.0)
np.maximum.at(mx, wid, W); np.minimum.at(mn, wid, W)
diff = (mx - mn).max(1)
R['seam_weight_mismatch_welded_verts(>1e-3)'] = int((diff > 1e-3).sum()); R['seam_weight_mismatch_max'] = float(diff.max())
# rest-pose position vs bone: verts whose dominant bone is far from them (wrong-bone weights)
bonepos = {}
for b in arm.data.bones:
    h = arm.matrix_world @ b.head_local; t = arm.matrix_world @ b.tail_local
    bonepos[b.name] = (np.array(h), np.array(t))
def seg_dist(p, h, t):
    v = t - h; L = max(1e-9, v @ v); u = np.clip(((p - h) @ v) / L, 0, 1)
    return np.linalg.norm(p - (h + u[:, None] * v), axis=1)
H = R['height_units']
dom = W.argmax(1)
far = []
dist_to_dom = np.zeros(len(co))
for j, nmz in enumerate(names):
    idx = np.nonzero(dom == j)[0]
    if not len(idx) or nmz not in bonepos: continue
    dist_to_dom[idx] = seg_dist(co[idx], *bonepos[nmz])
# nearest bone overall
alld = np.stack([seg_dist(co, *bonepos[n]) if n in bonepos else np.full(len(co), 9e9) for n in names], 1)
nearest = alld.argmin(1)
ratio = dist_to_dom / np.maximum(1e-6, alld.min(1))
R['dominant_bone_far(>0.12H & >2.5x nearest)'] = int(((dist_to_dom > 0.12 * H) & (ratio > 2.5)).sum())
# any weight > 0.1 from a bone more than 0.3 H away
farw = (W > 0.1) & (alld > 0.3 * H)
R['weights>0.1_from_bones_>0.3H_away'] = int(farw.any(1).sum())
pairs = {}
for i, j in zip(*np.nonzero(farw)):
    k = '%s<-%s' % (names[nearest[i]], names[j]); pairs[k] = pairs.get(k, 0) + 1
R['far_weight_pairs'] = dict(sorted(pairs.items(), key=lambda x: -x[1])[:20])
# per bone: vertex count with weight>0.5 and bbox z
R['bone_coverage'] = {n: int((W[:, j] > 0.5).sum()) for j, n in enumerate(names)}
# region specific: deltoid / trap / chest weight mix around each shoulder
for side in ('Left', 'Right'):
    sh, ar, sp2, nk = [names.index(x) for x in (side + 'Shoulder', side + 'Arm', 'Spine2', 'Neck')]
    h = bonepos[side + 'Arm'][0]
    near = np.linalg.norm(co - h, axis=1) < 0.12 * H
    R[side + '_shoulder_region_verts'] = int(near.sum())
    R[side + '_shoulder_region_mean_w'] = {n: round(float(W[near][:, names.index(n)].mean()), 3) for n in (side + 'Shoulder', side + 'Arm', 'Spine2', 'Spine1', 'Neck', side + 'ForeArm', 'Head')}
# hair: verts above the neck far from the head axis?
R['image_sizes'] = {im.name: list(im.size) for im in bpy.data.images}
np.save(os.path.splitext(OUT)[0] + '_vdev.npy', vdev)
json.dump(R, open(OUT, 'w'), indent=1, default=float)
print(json.dumps({k: v for k, v in R.items() if k not in ('groups',)}, indent=1, default=float))
