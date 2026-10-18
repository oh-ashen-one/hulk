"""Find 3D points where a vein crosses a UV seam (for extreme close-up QA).
Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup \
         --python tools/brute/tex_findseam.py [-- --mask PATH]
Writes ~/hulk-scratch/brute_tex/seam_vein_points.json (strongest crossings first):
  [{"co": [x,y,z], "n": [nx,ny,nz], "v_a": .., "v_b": ..}, ...]
"""
import sys, os, json
import bpy
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tex_common as tc

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
MASK = argv[argv.index('--mask') + 1] if '--mask' in argv else tc.OUT + 'T_Brute_Veins.png'

tc.clear_scene()
obj = tc.load_mesh()
me = obj.data
W = tc._weights(obj, len(me.vertices))
img = bpy.data.images.load(MASK)
w, h = img.size
px = np.empty(w * h * 4, np.float32); img.pixels.foreach_get(px); px = px.reshape(h, w, 4)[..., 0]

def sample(uv):
    x = int(np.clip(uv[0] * w, 0, w - 1)); y = int(np.clip(uv[1] * h, 0, h - 1))
    return float(px[y, x])

co = np.array([v.co[:] for v in me.vertices])
inv = tc._weld(co)
uvl = me.uv_layers.active.data
# map welded edge -> list of (face, uv_a, uv_b)
edges = {}
for p in me.polygons:
    li = list(p.loop_indices); vs = list(p.vertices)
    for k in range(len(vs)):
        a, b = vs[k], vs[(k + 1) % len(vs)]
        wa, wb = inv[a], inv[b]
        key = (min(wa, wb), max(wa, wb))
        ua, ub = uvl[li[k]].uv, uvl[li[(k + 1) % len(vs)]].uv
        if wa > wb:
            ua, ub = ub, ua
        edges.setdefault(key, []).append((a, b, (ua[0], ua[1]), (ub[0], ub[1])))
fore = W['LeftForeArm'] + W['RightForeArm'] + W['LeftArm'] + W['RightArm']
pts = []
for key, lst in edges.items():
    if len(lst) != 2:
        continue
    (a0, b0, ua0, ub0), (a1, b1, ua1, ub1) = lst
    if np.allclose(ua0, ua1, atol=1e-6) and np.allclose(ub0, ub1, atol=1e-6):
        continue   # not a UV seam
    if fore[a0] < 0.5:
        continue
    m0 = ((ua0[0] + ub0[0]) / 2, (ua0[1] + ub0[1]) / 2)
    m1 = ((ua1[0] + ub1[0]) / 2, (ua1[1] + ub1[1]) / 2)
    va, vb = sample(m0), sample(m1)
    if min(va, vb) > 0.5:
        c = (co[a0] + co[b0]) / 2
        n = (me.vertices[a0].normal + me.vertices[b0].normal).normalized()
        pts.append(dict(co=[float(x) for x in c], n=[float(x) for x in n], v_a=va, v_b=vb))
pts.sort(key=lambda d: -min(d['v_a'], d['v_b']))
# keep spatially distinct points
keep = []
for p in pts:
    if all(np.linalg.norm(np.array(p['co']) - np.array(k['co'])) > 0.05 for k in keep):
        keep.append(p)
json.dump(keep[:20], open(tc.OUT + 'seam_vein_points.json', 'w'), indent=1)
print('[tex] seam-vein crossings:', len(pts), 'distinct kept', len(keep[:20]))
