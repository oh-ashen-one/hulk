"""Export UV-seam correspondences + per-side tangent frames for seam erasure.
Run once per mesh/UV layout (Blender):
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python tools/brute/tex_seamdata.py
Writes ~/hulk-scratch/brute_tex/seam_data.npz with, per seam edge (welded edge whose two
faces use different UVs) and per side A/B: endpoint UVs (2x2), MikkTSpace tangent,
bitangent sign and normal at both endpoints (the frame a renderer decodes with).
"""
import sys, os
import bpy
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tex_common as tc

tc.clear_scene()
obj = tc.load_mesh()
me = obj.data
me.calc_tangents(uvmap=me.uv_layers.active.name)
nl = len(me.loops)
uv = np.empty(nl * 2, np.float32); me.uv_layers.active.data.foreach_get('uv', uv); uv = uv.reshape(-1, 2)
tan = np.empty(nl * 3, np.float32); me.loops.foreach_get('tangent', tan); tan = tan.reshape(-1, 3)
sgn = np.empty(nl, np.float32); me.loops.foreach_get('bitangent_sign', sgn)
nrm = np.empty(nl * 3, np.float32); me.loops.foreach_get('normal', nrm); nrm = nrm.reshape(-1, 3)
lv = np.empty(nl, np.int64); me.loops.foreach_get('vertex_index', lv)
co = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
inv = tc._weld(co)
ls = np.empty(len(me.polygons), np.int64); me.polygons.foreach_get('loop_start', ls)
lt = np.empty(len(me.polygons), np.int64); me.polygons.foreach_get('loop_total', lt)
nxt = np.arange(nl) + 1
nxt[ls + lt - 1] = ls
wa, wb = inv[lv], inv[lv[nxt]]
lo = np.minimum(wa, wb); hi = np.maximum(wa, wb)
key = lo.astype(np.int64) * (inv.max() + 1) + hi
order = np.argsort(key, kind='stable')
ks = key[order]
starts = np.r_[0, np.nonzero(np.diff(ks))[0] + 1]
cnt = np.diff(np.r_[starts, len(ks)])
pairs = starts[cnt == 2]
la = order[pairs]; lb = order[pairs + 1]           # loop (edge start corner) on side A / B


def side(l):
    """endpoint loops ordered so endpoint 0 is the lower welded id."""
    l0, l1 = l, nxt[l]
    swap = inv[lv[l0]] > inv[lv[l1]]
    e0 = np.where(swap, l1, l0); e1 = np.where(swap, l0, l1)
    return e0, e1


a0, a1 = side(la); b0, b1 = side(lb)
is_seam = (np.abs(uv[a0] - uv[b0]).max(1) > 1e-6) | (np.abs(uv[a1] - uv[b1]).max(1) > 1e-6)
a0, a1, b0, b1 = a0[is_seam], a1[is_seam], b0[is_seam], b1[is_seam]
np.savez(tc.OUT + 'seam_data.npz',
         uvA0=uv[a0], uvA1=uv[a1], uvB0=uv[b0], uvB1=uv[b1],
         TA0=tan[a0], TA1=tan[a1], TB0=tan[b0], TB1=tan[b1],
         sA0=sgn[a0], sA1=sgn[a1], sB0=sgn[b0], sB1=sgn[b1],
         NA0=nrm[a0], NA1=nrm[a1], NB0=nrm[b0], NB1=nrm[b1],
         P0=co[lv[a0]], P1=co[lv[a1]])
print('[tex] seam edges:', int(is_seam.sum()), 'of', len(la), 'manifold edges')
