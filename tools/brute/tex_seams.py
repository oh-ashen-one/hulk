"""Seam erasure for the Brute normal map + vein mask (system python3 + numpy/scipy/PIL).

Problem: across a UV seam the two islands reconstruct the surface signal with
bilinear interpolation on two differently placed/rotated texel grids, so at the
seam line their values disagree slightly. Flat maps hide this; steep vein flanks
show it as a thin shading line at extreme close range.
Fix (after Liu et al. 2017 "Seamless"): sample every seam edge densely, and
solve a sparse least-squares problem over the texels in the bilinear footprints
of those samples so that the *decoded world-space normal* (each side decoded
with its own MikkTSpace frame: n = x*T + y*(s*NxT) + z*N) agrees on both sides,
while staying as close as possible to the baked values. Only footprints of
samples that actually disagree are touched; every other texel stays bit-exact.

Run (after tex_bake.py and, once per mesh, tex_seamdata.py):
  python3 tools/brute/tex_seams.py
Reads  ~/hulk-scratch/brute_tex/{seam_data.npz, final_normal_f32.npy, final_veins_f32.npy}
Writes ~/hulk-scratch/brute_tex/{T_Brute_Normal.png, T_Brute_Veins.png} (overwrites)
"""
import os, sys
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
from PIL import Image

D = os.path.expanduser('~/hulk-scratch/brute_tex/')
SFX = sys.argv[sys.argv.index('--suffix') + 1] if '--suffix' in sys.argv else ''
W_SEAM = 400.0      # seam-agreement weight vs data fidelity (1.0)
W_SMOOTH = 4.0      # smoothness of the correction field between neighbouring texels
EPS_N = 0.004       # world-normal mismatch that triggers a fix
EPS_V = 0.01        # vein-mask mismatch that triggers a fix

S = np.load(D + 'seam_data.npz')
C = np.load(D + f'final_normal_f32{SFX}.npy').astype(np.float64)      # (H, W, 3) bottom-up rows
V = np.load(D + f'final_veins_f32{SFX}.npy').astype(np.float64)       # (H, W)
H, Wd = C.shape[:2]


def unit(v):
    return v / (np.linalg.norm(v, axis=-1, keepdims=True) + 1e-12)


# ---- dense samples along every seam edge --------------------------------
lenA = np.linalg.norm((S['uvA1'] - S['uvA0']) * [Wd, H], axis=1)
lenB = np.linalg.norm((S['uvB1'] - S['uvB0']) * [Wd, H], axis=1)
ns = np.maximum(2, np.ceil(np.maximum(lenA, lenB) * 2.0).astype(int) + 1)
eidx = np.repeat(np.arange(len(ns)), ns)
t = np.concatenate([np.linspace(0, 1, k) for k in ns])[:, None]


def lerp(a, b):
    return S[a][eidx] * (1 - t) + S[b][eidx] * t


uvA, uvB = lerp('uvA0', 'uvA1'), lerp('uvB0', 'uvB1')
TA, TB = unit(lerp('TA0', 'TA1')), unit(lerp('TB0', 'TB1'))
NA, NB = unit(lerp('NA0', 'NA1')), unit(lerp('NB0', 'NB1'))
sA, sB = np.sign(S['sA0'][eidx] + 1e-9), np.sign(S['sB0'][eidx] + 1e-9)
BA = sA[:, None] * np.cross(NA, TA)
BB = sB[:, None] * np.cross(NB, TB)
MA = np.stack([TA, BA, NA], -1)     # world = M @ tangent
MB = np.stack([TB, BB, NB], -1)
print('[seams] seam edges %d, samples %d' % (len(ns), len(t)))


def footprint(uv):
    """bilinear texel indices (n,4) and weights (n,4); texel centres at (i+.5)/W."""
    x = uv[:, 0] * Wd - 0.5
    y = uv[:, 1] * H - 0.5
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int)
    fx = x - x0; fy = y - y0
    xs = np.stack([x0, x0 + 1, x0, x0 + 1], 1).clip(0, Wd - 1)
    ys = np.stack([y0, y0, y0 + 1, y0 + 1], 1).clip(0, H - 1)
    w = np.stack([(1 - fx) * (1 - fy), fx * (1 - fy), (1 - fx) * fy, fx * fy], 1)
    return ys * Wd + xs, w


iA, wA = footprint(uvA)
iB, wB = footprint(uvB)
Cf = C.reshape(-1, 3)
Vf = V.reshape(-1)


def decode_world(idx, w, M):
    tn = (Cf[idx] * w[..., None]).sum(1) * 2 - 1
    return np.einsum('nij,nj->ni', M, tn)


mis_n = np.linalg.norm(decode_world(iA, wA, MA) - decode_world(iB, wB, MB), axis=1)
mis_v = np.abs((Vf[iA] * wA).sum(1) - (Vf[iB] * wB).sum(1))
print('[seams] world-normal mismatch before: mean %.4f  p99 %.4f  max %.4f' %
      (mis_n.mean(), np.percentile(mis_n, 99), mis_n.max()))


def laplacian(tex, pos, ch):
    """graph differences between 4-neighbour texels that are both unknowns."""
    y, x = np.divmod(tex, Wd)
    rows, cols, vals = [], [], []
    r = 0
    for dy, dx in ((0, 1), (1, 0)):
        yy, xx = y + dy, x + dx
        ok = (yy < H) & (xx < Wd)
        nb = np.where(ok, yy.clip(0, H - 1) * Wd + xx.clip(0, Wd - 1), 0)
        j = np.where(ok, pos[nb], -1)
        sel = j >= 0
        i0 = np.arange(len(tex))[sel]; j0 = j[sel]
        m = len(i0)
        for c in range(ch):
            rr = r + np.arange(m) * ch + c
            rows += [rr, rr]; cols += [i0 * ch + c, j0 * ch + c]; vals += [np.ones(m), -np.ones(m)]
        r += m * ch
    return sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(r, len(tex) * ch))


def solve_normal(active):
    tex = np.unique(np.concatenate([iA[active].ravel(), iB[active].ravel()]))
    pos = -np.ones(H * Wd, np.int64); pos[tex] = np.arange(len(tex))
    n = len(tex)
    rows, cols, vals = [], [], []
    act = np.nonzero(active)[0]
    # vectorised assembly: for sample k, component c (3 rows):
    #   sum_j wA_j * 2*MA[c,:] . u_j  - sum_j wB_j * 2*MB[c,:] . u_j = sum_c' MA[c,c'] - MB[c,c']
    K = len(act)
    for side, (I, Wt, M, sg) in enumerate(((iA, wA, MA, 1.0), (iB, wB, MB, -1.0))):
        Ii = pos[I[act]]                     # (K,4)
        for c in range(3):
            for cc in range(3):
                coef = sg * 2.0 * Wt[act] * M[act, c, cc][:, None]   # (K,4)
                rows.append(np.repeat(np.arange(K), 4) * 3 + c)
                cols.append(Ii.ravel() * 3 + cc)
                vals.append(coef.ravel())
    rhs = (MA[act].sum(2) - MB[act].sum(2)).ravel()      # (K*3,)
    A = sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(K * 3, n * 3))
    u0 = Cf[tex].ravel()
    L = laplacian(tex, pos, 3)
    # minimise W|Au-b|^2 + |u-u0|^2 + W_SMOOTH |L(u-u0)|^2  (smooth corrections, no blotches)
    LtL = W_SMOOTH * (L.T @ L)
    lhs = W_SEAM * (A.T @ A) + sp.identity(n * 3, format='csr') + LtL
    u = spla.spsolve(lhs.tocsc(), W_SEAM * (A.T @ rhs) + u0 + LtL @ u0)
    u = u.reshape(-1, 3) * 2 - 1
    u[:, 2] = np.maximum(u[:, 2], 0.05)
    u = unit(u) * 0.5 + 0.5
    return tex, u


def solve_scalar(active, F):
    tex = np.unique(np.concatenate([iA[active].ravel(), iB[active].ravel()]))
    pos = -np.ones(H * Wd, np.int64); pos[tex] = np.arange(len(tex))
    act = np.nonzero(active)[0]; K = len(act)
    rows = np.concatenate([np.repeat(np.arange(K), 4), np.repeat(np.arange(K), 4)])
    cols = np.concatenate([pos[iA[act]].ravel(), pos[iB[act]].ravel()])
    vals = np.concatenate([wA[act].ravel(), -wB[act].ravel()])
    A = sp.csr_matrix((vals, (rows, cols)), shape=(K, len(tex)))
    L = laplacian(tex, pos, 1)
    LtL = W_SMOOTH * (L.T @ L)
    lhs = W_SEAM * (A.T @ A) + sp.identity(len(tex), format='csr') + LtL
    u = spla.spsolve(lhs.tocsc(), F[tex] + LtL @ F[tex])
    return tex, np.clip(u, 0, 1)


# only where we added detail (the source map's own tiny seam mismatches - it was
# baked with another tangent basis - are left exactly as delivered)
FL = np.load(D + f'final_flat{SFX}.npy').reshape(-1)
touched = (~FL[iA]).any(1) | (~FL[iB]).any(1)
print('[seams] samples touching added detail: %d' % touched.sum())
active_n = (mis_n > EPS_N) & touched
tex_n, u_n = solve_normal(active_n)
Cf2 = Cf.copy(); Cf2[tex_n] = u_n
active_v = mis_v > EPS_V
tex_v, u_v = solve_scalar(active_v, Vf) if active_v.any() else (np.array([], int), np.array([]))
Vf2 = Vf.copy(); Vf2[tex_v] = u_v
Cf = Cf2
mis_n2 = np.linalg.norm(decode_world(iA, wA, MA) - decode_world(iB, wB, MB), axis=1)
print('[seams] fixed %d normal texels (%d samples), %d vein texels' % (len(tex_n), active_n.sum(), len(tex_v)))
print('[seams] world-normal mismatch after:  mean %.4f  p99 %.4f  max %.4f' %
      (mis_n2.mean(), np.percentile(mis_n2, 99), mis_n2.max()))

# ---- write: untouched texels keep the bake's 8-bit values exactly ---------
Nimg = np.asarray(Image.open(D + f'T_Brute_Normal{SFX}.png').convert('RGB')).copy()   # top-down
Nbu = Nimg[::-1].reshape(-1, 3)
Nbu[tex_n] = np.clip(np.rint(u_n * 255), 0, 255).astype(np.uint8)
Image.fromarray(Nbu.reshape(H, Wd, 3)[::-1]).save(D + f'T_Brute_Normal{SFX}.png')
Vimg = np.asarray(Image.open(D + f'T_Brute_Veins{SFX}.png').convert('L')).copy()
Vbu = Vimg[::-1].reshape(-1)
if len(tex_v):
    Vbu[tex_v] = np.clip(np.rint(u_v * 255), 0, 255).astype(np.uint8)
Image.fromarray(Vbu.reshape(H, Wd)[::-1]).convert('RGB').save(D + f'T_Brute_Veins{SFX}.png')
src = np.asarray(Image.open(os.path.expanduser('~/hulk-scratch/brute_v2/rig/textures/SM_Character_Brute_N.png')).convert('RGB'))
out = np.asarray(Image.open(D + f'T_Brute_Normal{SFX}.png').convert('RGB'))
same = (src == out).all(-1).mean()
print('[seams] wrote T_Brute_Normal%s.png / T_Brute_Veins%s.png ; identical to source: %.2f%%' % (SFX, SFX, 100 * same))
