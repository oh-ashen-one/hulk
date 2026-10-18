# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
# Corrective shape keys for the Brute's raised-arm armpit / lat / deltoid (the 52-bone Mixamo skeleton has no helper/twist bones).
#   1. every 2nd frame of every brute_v5 clip (WallClimb = WallAttach, skipped) is skinned (numpy linear-blend skinning, checked
#      == Blender's armature modifier); frames where a key weight (mesh_corrective_lib.weights = THE GAME MAPPING) >= 0.05 are kept
#   2. each kept frame is repaired in POSED space inside a soft armpit/lat/deltoid region (CORR_MODE=dqs_arap, default):
#      as-rigid-as-possible solve against the bind edge vectors (unfolds, spreads the inner-arm stretch; region edge softly pinned)
#      + 0.35 x the dual-quaternion-skinning offset of the same weights (puts back lat / deltoid volume ARAP alone loses)
#      + 10 masked Taubin passes
#   3. JOINT pose-space solve (CORR_SOLVE=joint, default): one bind-space delta per key minimising, over ALL kept frames at once,
#        ARAP energy of  y_k = X_k + M_k * sum_key w_key,k d_key   (M_k = sum_i w_i BoneMatrix_i,k: exactly morph-then-skin)
#        + 0.1 |y_k - repair_k|^2 + pin + 0.01 |d|^2,  Lift frames weighted x4 (CORR_CLIPW).  Fitting each frame's exact
#      inverse-skinned repair (CORR_SOLVE=lsq) was tried first: per-frame corrections are incoherent (rel. difference ~1 between
#      overhead frames, blended skin matrices near-singular at 160-180 deg) and the averaged key made things worse.
#   4. deltas are zero outside the region and written as shape keys; exported glb = same mesh / skin / UVs / skeleton
# usage: Blender -b --factory-startup -P tools/brute/mesh_corrective.py -- <rig.glb> <out.glb>
#   CORR_FIT_CACHE=<file.npz> caches the sampled frames (~25 min to sample at CORR_STEP=2; the solve from cache takes ~1 min).
#   Debug: CORR_DEBUG=Clip:frame[,..] (repair metrics), CORR_COHERENCE=Clip:frame,.. (per-frame correction similarity).
import bpy, sys, os, json, math, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mesh_common as C
import mesh_corrective_lib as K

argv = sys.argv[sys.argv.index('--') + 1:]
RIG, OUTF = argv[0], argv[1]
ARAP_IT = int(os.environ.get('CORR_ARAP_IT', '8'))
os.environ.setdefault('CORR_MODE', 'dqs_arap')
INFLATE = float(os.environ.get('CORR_INFLATE', '0.0'))
INWARD = float(os.environ.get('CORR_INWARD', '0.25'))
DQS_ARAP = float(os.environ.get('CORR_DQS_ARAP', '0.35'))
DQS_SMOOTH = int(os.environ.get('CORR_DQS_SMOOTH', '10'))
LAM_REL = float(os.environ.get('CORR_LAM', '0.0'))
DSMOOTH = int(os.environ.get('CORR_DSMOOTH', '0'))
WMIN = float(os.environ.get('CORR_WMIN', '0.05'))
STEP = int(os.environ.get('CORR_STEP', '2'))
t0 = time.time()

C.reset()
acts = C.load_anim_actions()
arm, me, objs = C.load_rig(RIG)
C.rest_pose(arm); bpy.context.view_layer.update()
sc = bpy.context.scene
A = np.array(arm.matrix_world); Ainv = np.linalg.inv(A)
MW = np.array(me.matrix_world)

W, names = C.weights(me)
W /= np.maximum(1e-12, W.sum(1, keepdims=True))
rest = C.rest_co(me)                         # world, bind
wid, nW = C.weld_map(rest)
_, rep = np.unique(wid, return_index=True)
P0 = rest[rep]; Wv = W[rep]
E = np.unique(np.sort(wid[C.edges(me)], 1), axis=0); E = E[E[:, 0] != E[:, 1]]
H = P0[:, 2].max() - P0[:, 2].min()
deg = np.bincount(E.ravel(), minlength=nW).astype(float)
I = np.concatenate([E[:, 0], E[:, 1]]); J = np.concatenate([E[:, 1], E[:, 0]])
g = names.index
print('welded verts %d edges %d H %.3f' % (nW, len(E), H))

# ---------------- region masks (per side), smooth falloff by graph distance
def graph_dist(seed, maxd):
    """approximate geodesic distance from seed set over the edge graph (Bellman-Ford sweeps)"""
    el = np.linalg.norm(P0[E[:, 0]] - P0[E[:, 1]], axis=1)
    d = np.where(seed, 0.0, np.inf)
    for _ in range(400):
        nd = d.copy()
        np.minimum.at(nd, E[:, 0], d[E[:, 1]] + el); np.minimum.at(nd, E[:, 1], d[E[:, 0]] + el)
        nd = np.minimum(nd, maxd * 2)
        if np.allclose(nd, d): break
        d = nd
    return d

REG_R = float(os.environ.get('CORR_REG_R', '0.085'))  # falloff width, fraction of height
MASK, CORE = {}, {}
for s in ('Left', 'Right'):
    a = Wv[:, [g(s + 'Arm'), g(s + 'ForeArm')]].sum(1)
    t = Wv[:, [g('Spine'), g('Spine1'), g('Spine2'), g(s + 'Shoulder')]].sum(1)
    core = (a > 0.05) & (t > 0.05)
    # keep only the shoulder neighbourhood (not the elbow / wrist / far torso)
    pa = np.array(arm.matrix_world @ arm.data.bones[s + 'Arm'].head_local)
    core &= np.linalg.norm(P0 - pa, axis=1) < 0.22 * H
    d = graph_dist(core, REG_R * H)
    m = 1.0 - np.vectorize(lambda x: K.smoothstep(0.0, REG_R * H, x))(d)
    # never touch the head, hands or the far side
    far = Wv[:, [g('Head')] + [j for j, n in enumerate(names) if 'Hand' in n]].sum(1)
    m *= np.clip(1 - 2 * far, 0, 1)
    MASK[s] = m; CORE[s] = core
    print('mask %s core %d  >0 %d  >0.5 %d' % (s, core.sum(), (m > 0).sum(), (m > 0.5).sum()))
assert not ((MASK['Left'] > 0) & (MASK['Right'] > 0)).any(), 'side masks overlap'
mask = MASK['Left'] + MASK['Right']
FREE = mask > 1e-4
fidx = np.nonzero(FREE)[0]
ALPHA = 12.0 * (1 - mask) ** 2 + 1e-3     # soft pin to the skinned surface, zero in the core

# edges touching the free set
ef = FREE[I]
If, Jf = I[ef], J[ef]

# ---------------- numpy linear-blend skinning
bone_list = names
bidx = [arm.data.bones.find(n) for n in bone_list]
def bone_mats():
    """(G,4,4) world-space deform matrices A @ pose @ bind^-1 @ A^-1"""
    out = np.empty((len(bone_list), 4, 4))
    for k, n in enumerate(bone_list):
        pb = arm.pose.bones[n]; b = arm.data.bones[n]
        out[k] = A @ np.array(pb.matrix) @ np.linalg.inv(np.array(b.matrix_local)) @ Ainv
    return out
def skin(Bm):
    M = np.einsum('vg,gij->vij', Wv, Bm)            # (nW,4,4)
    X = np.einsum('vij,vj->vi', M[:, :3, :3], P0) + M[:, :3, 3]
    return X, M[:, :3, :3]

# check against Blender on one frame
C.assign(arm, acts['Lift']); sc.frame_set(70); bpy.context.view_layer.update()
Xb = C.eval_co(me)[rep]; Xn, _ = skin(bone_mats())
print('LBS check max err %.2e (H units)' % (np.abs(Xb - Xn).max() / H))
assert np.abs(Xb - Xn).max() < 1e-4 * H

def polar(S):
    U, _, Vt = np.linalg.svd(S)
    R = np.einsum('vji,vkj->vik', Vt, U)    # V U^T
    neg = np.linalg.det(R) < 0
    if neg.any():
        Vt2 = Vt[neg].copy(); Vt2[:, 2, :] *= -1
        R[neg] = np.einsum('vji,vkj->vik', Vt2, U[neg])
    return R

def lap(z):
    """graph Laplacian (deg on diagonal, -1 off) applied to z (nW,3), only free rows meaningful"""
    out = deg[:, None] * z
    for c in range(3): out[:, c] -= np.bincount(If, weights=z[Jf, c], minlength=nW)
    return out

def arap(X, Mlin):
    """repair the skinned surface X inside the soft region. returns Y"""
    R = polar(Mlin.transpose(0, 2, 1))    # init: rotation of the blended skinning matrix (polar() expects S = sum p y^T)
    Y = X.copy()
    dP = P0[If] - P0[Jf]
    LX = lap(X)
    for it in range(ARAP_IT):
        # global step: (L + diag alpha) y = b + alpha x, solved for z = y - x with z = 0 off the free set
        Rij = 0.5 * (R[If] + R[Jf])
        b = np.zeros((nW, 3))
        v = np.einsum('eij,ej->ei', Rij, dP)
        for c in range(3): b[:, c] = np.bincount(If, weights=v[:, c], minlength=nW)
        rhs = (b - LX); rhs[~FREE] = 0
        z = (Y - X); z[~FREE] = 0
        def Aop(q):
            o = lap(q) + ALPHA[:, None] * q; o[~FREE] = 0; return o
        r = rhs - Aop(z); p = r.copy(); rs = (r * r).sum(0)
        for _ in range(300):
            Ap = Aop(p); al = rs / np.maximum(1e-30, (p * Ap).sum(0))
            z += al * p; r -= al * Ap; rn = (r * r).sum(0)
            if np.sqrt(rn.max()) < 1e-5 * H: break
            p = r + (rn / np.maximum(1e-30, rs)) * p; rs = rn
        Y = X + z
        # local step: best rotation per vertex
        dY = Y[If] - Y[Jf]
        S = np.zeros((nW, 3, 3))
        outer = np.einsum('ei,ej->eij', dP, dY)
        for a_ in range(3):
            for b_ in range(3): S[:, a_, b_] = np.bincount(If, weights=outer[:, a_, b_], minlength=nW)
        Rf = polar(S[fidx]); R = R.copy(); R[fidx] = Rf
    global LAST_R; LAST_R = R
    return Y

# ---------------- delta mush repair (posed-space smoothing + bind-pose detail offsets in local frames)
MUSH_IT = int(os.environ.get('CORR_MUSH_IT', '40'))
MUSH_L = 0.5
nb0 = np.full(nW, -1); nb0[E[::-1, 0]] = E[::-1, 1]; nb0[E[::-1, 1]] = np.where(nb0[E[::-1, 1]] < 0, E[::-1, 0], nb0[E[::-1, 1]])
nb0[nb0 < 0] = np.arange(nW)[nb0 < 0]
def smooth(X, it=None):
    Y = X.copy()
    for _ in range(it or MUSH_IT):
        avg = np.stack([np.bincount(I, weights=Y[J, c], minlength=nW) for c in range(3)], 1) / np.maximum(1, deg)[:, None]
        Y += MUSH_L * (avg - Y)
    return Y
def vnormals(X):
    n = np.cross(X[Tw[:, 1]] - X[Tw[:, 0]], X[Tw[:, 2]] - X[Tw[:, 0]])
    VN = np.zeros((nW, 3))
    for k in range(3): np.add.at(VN, Tw[:, k], n)
    return VN / np.maximum(1e-12, np.linalg.norm(VN, axis=1, keepdims=True))
def frames(S):
    n = vnormals(S); t = S[nb0] - S; t -= (t * n).sum(1, keepdims=True) * n
    t /= np.maximum(1e-12, np.linalg.norm(t, axis=1, keepdims=True)); b = np.cross(n, t)
    return np.stack([t, b, n], 2)      # columns
Tw = wid[C.tris(me)]
_OFF = {}
def mush(X, Mlin):
    if MUSH_IT not in _OFF:   # local-frame detail offsets of the bind pose
        S0 = smooth(P0); _OFF[MUSH_IT] = np.einsum('vji,vj->vi', frames(S0), P0 - S0)
    S = smooth(X); F = frames(S)
    Y = S + np.einsum('vij,vj->vi', F, _OFF[MUSH_IT])
    if INFLATE > 0:
        pass
    m = mask[:, None]
    return X + m * (Y - X)

# ---------------- mask-weighted Taubin smoothing (no shrink) + volume restore along normals
TAU_L, TAU_M = 0.5, -0.53
VOL = float(os.environ.get('CORR_VOL', '1.0'))
def taubin(X, it, wgt):
    Y = X.copy(); w = wgt[:, None]
    for k in range(it):
        avg = np.stack([np.bincount(I, weights=Y[J, c], minlength=nW) for c in range(3)], 1) / np.maximum(1, deg)[:, None]
        Y += w * (TAU_L if k % 2 == 0 else TAU_M) * (avg - Y)
    return Y
def region_vol(Y, s, c):
    """signed volume of the cone from point c over the region triangles of side s"""
    m = TVOL[s]; a, b, d = Y[Tw[m, 0]] - c, Y[Tw[m, 1]] - c, Y[Tw[m, 2]] - c
    return (a * np.cross(b, d)).sum() / 6.0
def smooth_fix(X, Mlin, Bm=None):
    Y = taubin(X, MUSH_IT, mask)
    if VOL > 0 and Bm is not None:
        for s in ('Left', 'Right'):
            cb = np.array(arm.matrix_world @ arm.data.bones[s + 'Arm'].head_local)
            cp = (Bm[g(s + 'Shoulder')] @ np.append(cb, 1))[:3]
            v0 = region_vol(P0, s, cb); vx = region_vol(Y, s, cp)
            # uniform push along vertex normals weighted by the mask: dV ~ h * sum(mask * area)
            n = vnormals(Y); m = MASK[s]
            At = 0.5 * np.linalg.norm(np.cross(Y[Tw[:, 1]] - Y[Tw[:, 0]], Y[Tw[:, 2]] - Y[Tw[:, 0]]), axis=1)
            va = np.zeros(nW); np.add.at(va, Tw.ravel(), np.repeat(At / 3, 3))
            h = VOL * (v0 - vx) / max(1e-9, (m * va).sum())
            h = float(np.clip(h, 0, 0.02 * H))
            Y = Y + (h * m)[:, None] * n
            STATS_VOL.append((s, v0, vx, h))
    return Y
STATS_VOL = []

def repair(X, Mlin, Bm=None):
    mode = os.environ.get('CORR_MODE', 'smooth')
    if mode == 'mush': return mush(X, Mlin)
    if mode in ('dqs', 'dqs_arap'):
        # dual-quaternion skinning of the SAME weights (Blender armature 'Preserve Volume') as the volume-correct target
        amod = next(m for m in me.modifiers if m.type == 'ARMATURE')
        amod.use_deform_preserve_volume = True; bpy.context.view_layer.update()
        Yd = C.eval_co(me)[rep]
        amod.use_deform_preserve_volume = False; bpy.context.view_layer.update()
        if mode == 'dqs_arap':
            # ARAP repair of the linear skin (unfolds, spreads stretch) + a fraction of the dual-quaternion volume offset
            Y = arap(X, Mlin) + DQS_ARAP * mask[:, None] * (Yd - X)
        else:
            Y = X + mask[:, None] * (Yd - X)
        if DQS_SMOOTH: Y = taubin(Y, DQS_SMOOTH, mask)
        return Y
    if mode == 'arap':
        Y = arap(X, Mlin)
        # keep the volume: the inward (below the skinned surface) part of the repair is scaled by INWARD; tangential
        # (stretch-spreading) and outward (fold-filling) parts are kept. normals of the lightly smoothed skinned surface
        n = vnormals(taubin(X, 20, np.ones(nW)))
        d = Y - X; dn = (d * n).sum(1)
        d -= ((1 - INWARD) * np.minimum(dn, 0))[:, None] * n
        return X + d
    return smooth_fix(X, Mlin, Bm)

# ---------------- region metrics (same definition as mesh_corrective_verify.py, welded topology)
Tw = wid[C.tris(me)]
tdom = Wv[Tw].sum(1).argmax(1)
TVOL = {s_: (MASK[s_][Tw] > 0).all(1) for s_ in ('Left', 'Right')}
TREG = {s: (Wv[Tw][:, :, [g(s + 'Arm'), g(s + 'ForeArm')]].sum(2) > 0.08).all(1) & (MASK[s][Tw] > 0.5).all(1) for s in ('Left', 'Right')}
def tn(co):
    n = np.cross(co[Tw[:, 1]] - co[Tw[:, 0]], co[Tw[:, 2]] - co[Tw[:, 0]]); return n / np.maximum(1e-12, np.linalg.norm(n, axis=1, keepdims=True))
N0w = tn(P0)
# geometric creases: interior edges whose two triangles' normals oppose (dot < -0.3) -- independent of any rig expectation
def tri_adj(Tw):
    e = np.concatenate([Tw[:, [0, 1]], Tw[:, [1, 2]], Tw[:, [2, 0]]]); t = np.tile(np.arange(len(Tw)), 3)
    e = np.sort(e, 1); o = np.lexsort((e[:, 1], e[:, 0])); e, t = e[o], t[o]
    same = (e[1:] == e[:-1]).all(1)
    return np.stack([t[:-1][same], t[1:][same]], 1)
TA = tri_adj(Tw)
TAREG = {s: TREG[s][TA].all(1) for s in TREG}
def tframe(co):
    e1 = co[Tw[:, 1]] - co[Tw[:, 0]]; e2 = co[Tw[:, 2]] - co[Tw[:, 0]]
    u = e1 / np.maximum(1e-12, np.linalg.norm(e1, axis=1, keepdims=True))
    n = np.cross(e1, e2); n /= np.maximum(1e-12, np.linalg.norm(n, axis=1, keepdims=True)); v = np.cross(n, u)
    return np.stack([np.stack([(e1 * u).sum(1), (e1 * v).sum(1)], 1), np.stack([(e2 * u).sum(1), (e2 * v).sum(1)], 1)], 2)
B0i = np.linalg.inv(tframe(P0) + np.eye(2) * 1e-12)
def metrics(Y, Bm):
    Ne = np.einsum('tij,tj->ti', Bm[tdom, :3, :3], N0w); Ne /= np.linalg.norm(Ne, axis=1, keepdims=True)
    n = tn(Y); dot = (n * Ne).sum(1); cr = (n[TA[:, 0]] * n[TA[:, 1]]).sum(1)
    sv = np.linalg.svd(np.einsum('tij,tjk->tik', tframe(Y), B0i), compute_uv=False)
    return {s[0]: dict(fold=int((dot[m] < 0).sum()), crease=int((cr[TAREG[s]] < -0.3).sum()), s1gt2=int((sv[m, 0] > 2).sum()),
                       s1p99=round(float(np.percentile(sv[m, 0], 99)), 2), amin=round(float((sv[m, 0] * sv[m, 1]).min()), 3)) for s, m in TREG.items()}
print('bind creases', metrics(P0, np.tile(np.eye(4), (len(names), 1, 1))))
COH = os.environ.get('CORR_COHERENCE')
if COH:
    # how similar are the exact per-frame bind-space corrections of different frames? (rel. difference over the core region)
    ds, tags = [], []
    for item in COH.split(','):
        clip, f = item.split(':'); C.assign(arm, acts[clip]); sc.frame_set(int(f)); bpy.context.view_layer.update()
        Bm = bone_mats(); X, Ml = skin(Bm); Y = repair(X, Ml, Bm)
        ds.append(np.einsum('vij,vj->vi', np.linalg.inv(Ml), Y - X)); tags.append(item)
        print('COH frame %s elev L %.0f R %.0f' % (item, K.elevation(arm, 'Left'), K.elevation(arm, 'Right')))
    for s in ('Left', 'Right'):
        v = MASK[s] > 0.5
        print('COH side', s, ' '.join('%10s' % t for t in tags))
        for a, ta in enumerate(tags):
            print('COH %10s ' % ta + ' '.join('%10.2f' % (np.linalg.norm(ds[a][v] - ds[b][v]) / np.linalg.norm(ds[a][v])) for b in range(len(tags))),
                  ' |d| rms %.3f' % np.sqrt((ds[a][v] ** 2).sum(1).mean()))
    sys.exit(0)
DEBUG = os.environ.get('CORR_DEBUG')
if DEBUG:
    for item in DEBUG.split(','):
        clip, f = item.split(':'); C.assign(arm, acts[clip]); sc.frame_set(int(f)); bpy.context.view_layer.update()
        Bm = bone_mats(); X, Ml = skin(Bm)
        for it in ([0] + [int(x) for x in os.environ.get('CORR_DEBUG_ITS', '10,20,40,80').split(',')]):
            ARAP_IT = it; MUSH_IT = it; Y = repair(X, Ml, Bm) if it else X
            print('DEBUG %s:%s it %3d %s  max move %.3f H vol %s' % (clip, f, it, metrics(Y, Bm), np.abs(Y - X).max() / H,
                  [(a, round(b, 4), round(c, 4), round(d / H, 4)) for a, b, c, d in STATS_VOL[-2:]] if it else ''))
    if os.environ.get('CORR_DEBUG_EXPORT'):
        # exact per-frame inverse skinning of the last debug solve -> keys (weight 1 reproduces Y at that frame)
        dl = np.einsum('vij,vj->vi', np.linalg.inv(Ml), Y - X)
        D = {'CorrArmUp_L': dl * (MASK['Left'] > 0)[:, None], 'CorrArmUp_R': dl * (MASK['Right'] > 0)[:, None]}
    else:
        sys.exit(0)

# ---------------- sample frames, solve, accumulate least squares
def fit():
    global nfr
    SIDES = ('Left', 'Right')
    KEYS = {s: ['CorrArmUp_' + s[0]] + (['CorrArmSide_' + s[0]] if K.USE_SIDE else []) for s in SIDES}
    nk = {s: len(KEYS[s]) for s in SIDES}
    AtA = {s: np.zeros((nW, 3 * nk[s], 3 * nk[s])) for s in SIDES}
    Atb = {s: np.zeros((nW, 3 * nk[s])) for s in SIDES}
    nfr = 0; log = []
    cache = os.environ.get('CORR_FIT_CACHE')
    if cache and os.path.exists(cache):
        z = np.load(cache, allow_pickle=True)
        for s_ in SIDES: AtA[s_] = z['AtA_' + s_]; Atb[s_] = z['Atb_' + s_]
        log = list(z['log']); nfr = len(log); print('loaded fit cache', cache, nfr, 'frames')
    else:
        for clip, act in sorted(acts.items()):
            if clip == 'WallClimb': continue   # same take as WallAttach
            C.assign(arm, act); f0, f1 = int(round(act.frame_range[0])), int(round(act.frame_range[1]))
            for f in range(f0, f1 + 1, STEP):
                sc.frame_set(f); bpy.context.view_layer.update()
                w = K.weights(arm)
                if max(w.values()) < WMIN: continue
                Bm = bone_mats(); X, Ml = skin(Bm)
                Y = repair(X, Ml, Bm)
                res = Y - X
                nfr += 1; log.append((clip, f, {k: round(v, 3) for k, v in w.items()}, float(np.abs(res).max() / H)))
                for s in SIDES:
                    ws = np.array([w[k] for k in KEYS[s]])
                    if ws.max() < WMIN: continue
                    v = np.nonzero(MASK[s] > 0)[0]
                    Ak = np.concatenate([wk * Ml[v] for wk in ws], axis=2)   # (n,3,3nk)
                    AtA[s][v] += np.einsum('nji,njk->nik', Ak, Ak)
                    Atb[s][v] += np.einsum('nji,nj->ni', Ak, res[v])
            print('clip %-10s done, frames used so far %d  (%.0fs)' % (clip, nfr, time.time() - t0))
        if cache: np.savez(cache, log=np.array(log, dtype=object), **{'AtA_' + s_: AtA[s_] for s_ in SIDES}, **{'Atb_' + s_: Atb[s_] for s_ in SIDES})

    D = {}
    for s in SIDES:
        v = np.nonzero(MASK[s] > 0)[0]
        # Tikhonov: relative to the per-vertex data strength (shrinks inconsistent / barely constrained vertices to 0)
        tr = np.trace(AtA[s][v], axis1=1, axis2=2)[:, None, None] / (3 * nk[s])
        lam = (LAM_REL * tr + 1e-4) * np.eye(3 * nk[s])[None]
        sol = np.linalg.solve(AtA[s][v] + lam, Atb[s][v][..., None])[..., 0]
        for k, key in enumerate(KEYS[s]):
            d = np.zeros((nW, 3)); d[v] = sol[:, 3 * k:3 * k + 3]
            # spatial smoothing of the bind-space delta field (masked; the region edge stays at 0)
            for _ in range(DSMOOTH):
                avg = np.stack([np.bincount(I, weights=d[J, c], minlength=nW) for c in range(3)], 1) / np.maximum(1, deg)[:, None]
                d = d + 0.5 * (avg - d) * (MASK[s] > 0)[:, None]
            d *= MASK[s][:, None]
            D[key] = d
            print('KEY %s  max |d| %.4f m (%.3f%% H)  verts moved >1mm %d' % (key, np.linalg.norm(d, axis=1).max(), 100 * np.linalg.norm(d, axis=1).max() / H,
                  (np.linalg.norm(d, axis=1) > 1e-3).sum()))
    np.savez(os.path.splitext(OUTF)[0] + '_deltas.npz', **D, mask_L=MASK['Left'], mask_R=MASK['Right'])
    return D, log

# ---------------- joint (pose-space) solve: ONE key per side/type that minimises the sum over all sampled frames of
#   ARAP energy of the corrected skin  sum_edges |(y_i - y_j) - R_k,ij (p_i - p_j)|^2   (R_k from the per-frame repair)
# + GAMMA * |y - Y_k|^2 (pull to the per-frame repair target, which carries the volume)  + ALPHA pin + LAMBDA |d|^2
#   with y = X_k + M_k * sum_key w_key,k d_key  (exactly what the game's morph + skinning produce)
GAMMA = float(os.environ.get('CORR_GAMMA', '0.1'))
JLAM = float(os.environ.get('CORR_JLAM', '0.01'))
OUTER = int(os.environ.get('CORR_OUTER', '1'))
MU = float(os.environ.get('CORR_MU', '0'))
REWEIGHT = float(os.environ.get('CORR_REWEIGHT', '0'))
DPOW = float(os.environ.get('CORR_DPOW', '0'))   # pull of the Laplacian (local shape) of the corrected skin to the per-frame target's
def fit_joint():
    SIDES = ('Left', 'Right')
    nkey = 2 if K.USE_SIDE else 1
    F = fidx; nF = len(F); loc = -np.ones(nW, int); loc[F] = np.arange(nF)
    side_of = np.where(MASK['Left'][F] > 0, 0, 1)
    # directed free-free edges, sorted by target row (for reduceat neighbour sums)
    ff = FREE[I] & FREE[J]; a_, b_ = loc[I[ff]], loc[J[ff]]; o = np.argsort(a_, kind='stable'); a_, b_ = a_[o], b_[o]
    starts = np.searchsorted(a_, np.arange(nF)); has = np.bincount(a_, minlength=nF) > 0
    degF = deg[F]; alF = ALPHA[F]
    def nsum(u):   # u (K,nF,3) -> sum over free neighbours
        g_ = u[:, b_]; out = np.zeros_like(u)
        r_ = np.add.reduceat(g_, np.minimum(starts, len(a_) - 1), axis=1); out[:, has] = r_[:, has]; return out
    cache = os.environ.get('CORR_FIT_CACHE')
    if cache and os.path.exists(cache):
        z = np.load(cache, allow_pickle=True); Mk, Wk, Xk, Yk, Rk, log = z['Mk'], z['Wk'], z['Xk'], z['Yk'], z['Rk'], list(z['log'])
        print('loaded joint cache', cache, len(log))
    else:
        Mk, Wk, Xk, Yk, Rk, log = [], [], [], [], [], []
        for clip, act in sorted(acts.items()):
            if clip == 'WallClimb': continue
            C.assign(arm, act); f0, f1 = int(round(act.frame_range[0])), int(round(act.frame_range[1]))
            for f in range(f0, f1 + 1, STEP):
                sc.frame_set(f); bpy.context.view_layer.update()
                w = K.weights(arm)
                if max(w.values()) < WMIN: continue
                Bm = bone_mats(); X, Ml = skin(Bm); Y = repair(X, Ml, Bm)
                # rotations of the repaired surface (local ARAP step on Y, every vertex touching the region)
                dP = P0[I] - P0[J]; dY = Y[I] - Y[J]; outer = np.einsum('ei,ej->eij', dP, dY); S = np.zeros((nW, 3, 3))
                for p_ in range(3):
                    for q_ in range(3): S[:, p_, q_] = np.bincount(I, weights=outer[:, p_, q_], minlength=nW)
                R = polar(S)
                ww = np.zeros((nF, nkey))
                for si, s in enumerate(SIDES):
                    ks = ['CorrArmUp_' + s[0]] + (['CorrArmSide_' + s[0]] if K.USE_SIDE else [])
                    ww[side_of == si] = [w[k] for k in ks]
                Mk.append(Ml[F]); Wk.append(ww); Xk.append(X); Yk.append(Y[F]); Rk.append(R.astype(np.float32))
                log.append((clip, f, {k: round(v, 3) for k, v in w.items()}))
            print('clip %-10s sampled, frames %d (%.0fs)' % (clip, len(log), time.time() - t0))
        # X / R are only needed on the free set + its 1-ring
        NB = np.unique(np.concatenate([F, J[FREE[I]]]))
        Mk, Wk, Yk = np.array(Mk), np.array(Wk), np.array(Yk)
        Xk = np.array([x[NB] for x in Xk]); Rk = np.array([r[NB] for r in Rk])
        if cache: np.savez(cache, Mk=Mk, Wk=Wk, Xk=Xk, Yk=Yk, Rk=Rk, NB=NB, log=np.array(log, dtype=object))
    NB = np.unique(np.concatenate([F, J[FREE[I]]])); nbl = -np.ones(nW, int); nbl[NB] = np.arange(len(NB))
    Kf = len(Mk); print('joint solve: frames %d free verts %d keys/side %d' % (Kf, nF, nkey))
    # edges with a free source (directed), in NB-local indices
    ef_ = FREE[I]; Ei, Ej = nbl[I[ef_]], nbl[J[ef_]]; Ei_f = loc[I[ef_]]
    e0 = P0[I[ef_]] - P0[J[ef_]]
    XF = Xk[:, nbl[F]]
    def rhs_arap(Rn):
        # b_i - (L X)_i for free rows, per frame: sum_j [ (R_i+R_j)/2 e0_ij - (x_i - x_j) ]
        v = 0.5 * np.einsum('keab,eb->kea', Rn[:, Ei] + Rn[:, Ej], e0) - (Xk[:, Ei] - Xk[:, Ej])
        out = np.zeros((Kf, nF, 3))
        for c in range(3):
            out[:, :, c] = np.stack([np.bincount(Ei_f, weights=v[k, :, c], minlength=nF) for k in range(Kf)])
        return out
    def U(D):   # (nF,nkey,3) -> per-frame displacement (K,nF,3)
        return np.einsum('kfij,kfj->kfi', Mk, np.einsum('kfn,fnj->kfj', Wk, D))
    def Ut(Q):  # adjoint
        return np.einsum('kfn,kfi->fni', Wk, np.einsum('kfji,kfj->kfi', Mk, Q))
    ck = np.ones(Kf)
    CLIPW = dict((kv.split(':')[0], float(kv.split(':')[1])) for kv in os.environ.get('CORR_CLIPW', 'Lift:4').split(',') if kv)
    if CLIPW: ck = np.array([CLIPW.get(str(r[0]), 1.0) for r in log]); ck *= Kf / ck.sum(); print('clip weights', CLIPW)
    ck0 = ck.copy()
    def Aop(D):
        u = U(D)
        Lu = degF[None, :, None] * u - nsum(u)
        q = Lu + (alF[None, :, None] + GAMMA) * u
        if MU: q = q + MU * (degF[None, :, None] * Lu - nsum(Lu))
        return Ut(ck[:, None, None] * q) + JLAM * ck.sum() * D
    # region creases per frame (same definition as metrics()), NB-local
    TRm = TREG['Left'] | TREG['Right']; TAm = TRm[TA].all(1)
    trs = np.nonzero(TRm)[0]; tpos = -np.ones(len(Tw), int); tpos[trs] = np.arange(len(trs))
    tl = nbl[Tw[trs]]; ta0, ta1 = tpos[TA[TAm, 0]], tpos[TA[TAm, 1]]
    def creases(Y):   # Y (K, nNB, 3)
        e1 = Y[:, tl[:, 1]] - Y[:, tl[:, 0]]; e2 = Y[:, tl[:, 2]] - Y[:, tl[:, 0]]
        n = np.cross(e1, e2); n /= np.maximum(1e-12, np.linalg.norm(n, axis=2, keepdims=True))
        return ((n[:, ta0] * n[:, ta1]).sum(2) < -0.3).sum(1)
    TRUSE = TRm.copy()
    c0 = creases(Xk)
    print('LBS region creases per frame: mean %.1f' % c0.mean())
    Rn = Rk.astype(np.float64)
    D = np.zeros((nF, nkey, 3))
    for it in range(OUTER):
        T_ = Yk - XF; LT = degF[None, :, None] * T_ - nsum(T_)
        rhs = Ut(ck[:, None, None] * (rhs_arap(Rn) + GAMMA * T_ + (MU * (degF[None, :, None] * LT - nsum(LT)) if MU else 0)))
        r = rhs - Aop(D); p = r.copy(); rs = (r * r).sum()
        for cg in range(400):
            Ap = Aop(p); al = rs / max(1e-30, (p * Ap).sum()); D += al * p; r -= al * Ap; rn = (r * r).sum()
            if np.sqrt(rn) < 1e-6 * np.sqrt((rhs * rhs).sum()): break
            p = r + (rn / rs) * p; rs = rn
        u = U(D)
        print('joint outer %d: cg its %d  rel res %.2e  max |d| %.3f  rms |u| %.4f (%.0fs)' % (it, cg, np.sqrt(rn / max(1e-30, (rhs * rhs).sum())),
              np.linalg.norm(D, axis=2).max(), np.sqrt((u ** 2).sum(2).mean()), time.time() - t0))
        yC = Xk.copy(); yC[:, nbl[F]] += u; c1 = creases(yC)
        print('   region creases per frame: LBS %.1f -> corrected %.1f; frames worse %d / %d' % (c0.mean(), c1.mean(), (c1 > c0).sum(), Kf))
        if REWEIGHT:
            # frames whose creases got worse than the plain skin weigh more in the next solve
            ck = ck0 * (1.0 + REWEIGHT * np.maximum(0, c1 - c0) / (c0 + 5.0)); ck *= Kf / ck.sum()
        if it + 1 < OUTER:
            # local step: new rotations of the corrected surface per frame (free vertices)
            yN = Xk.copy(); yN[:, nbl[F]] += u
            dY = yN[:, Ei] - yN[:, Ej]
            S = np.zeros((Kf, nF, 3, 3)); outer = np.einsum('ea,keb->keab', e0, dY)
            for p_ in range(3):
                for q_ in range(3):
                    S[:, :, p_, q_] = np.stack([np.bincount(Ei_f, weights=outer[k, :, p_, q_], minlength=nF) for k in range(Kf)])
            Rn[:, nbl[F]] = polar(S.reshape(-1, 3, 3)).reshape(Kf, nF, 3, 3)
    Dk = {}
    for si, s in enumerate(SIDES):
        ks = ['CorrArmUp_' + s[0]] + (['CorrArmSide_' + s[0]] if K.USE_SIDE else [])
        for j, key in enumerate(ks):
            d = np.zeros((nW, 3)); sel = side_of == si; d[F[sel]] = D[sel, j]
            d *= (np.minimum(1.0, MASK[s] / 0.05) * MASK[s] ** DPOW)[:, None]   # exact zero at the region edge (+ optional tighter falloff)
            Dk[key] = d
            print('KEY %s  max |d| %.4f m  rms %.4f' % (key, np.linalg.norm(d, axis=1).max(), np.sqrt((d[F[sel]] ** 2).sum(1).mean())))
    np.savez(os.path.splitext(OUTF)[0] + '_deltas.npz', **Dk, mask_L=MASK['Left'], mask_R=MASK['Right'])
    return Dk, log

SIDES = ('Left', 'Right'); nfr = 0; log = []
if not DEBUG:
    D, log = fit_joint() if os.environ.get('CORR_SOLVE', 'joint') == 'joint' else fit()
    nfr = len(log)

# ---------------- write shape keys on the original (seam-split) mesh, export
C.rest_pose(arm)
for o in [o for o in bpy.data.objects if o.type == 'ARMATURE']:
    if o.animation_data: o.animation_data.action = None
Minv = np.linalg.inv(MW[:3, :3])
co0 = np.empty(len(me.data.vertices) * 3); me.data.vertices.foreach_get('co', co0); co0 = co0.reshape(-1, 3)
me.shape_key_add(name='Basis', from_mix=False)
for key, d in D.items():
    kb = me.shape_key_add(name=key, from_mix=False)
    dl = d[wid] @ Minv.T
    kb.data.foreach_set('co', (co0 + dl).ravel())
    kb.slider_min = 0.0; kb.slider_max = 1.0; kb.value = 0.0
for a in list(bpy.data.actions): bpy.data.actions.remove(a)
for o in bpy.data.objects: o.select_set(o.type in ('MESH', 'ARMATURE'))
bpy.ops.export_scene.gltf(filepath=OUTF, export_format='GLB', use_selection=True, export_skins=True, export_animations=False,
                          export_morph=True, export_morph_normal=False)
json.dump(dict(frames=[list(map(lambda x: x.tolist() if hasattr(x, "tolist") else x, r)) for r in log], keys=list(D), mapping=dict(elev='angle(ForeArm-Arm, Spine1-Neck) deg', up=[K.UP_A0, K.UP_A1], side=[K.SIDE_A0, K.SIDE_A1] if K.USE_SIDE else None),
               clipw=os.environ.get('CORR_CLIPW', 'Lift:4'), mode=os.environ.get('CORR_MODE'), solve=os.environ.get('CORR_SOLVE', 'joint'), gamma=GAMMA, jlam=JLAM, outer=OUTER, mu=MU, step=STEP, dqs_arap=DQS_ARAP, dqs_smooth=DQS_SMOOTH,
               arap_it=ARAP_IT, reg_r=REG_R), open(os.path.splitext(OUTF)[0] + '_build.json', 'w'), indent=0)
print('WROTE', OUTF, 'frames', nfr, '%.0fs' % (time.time() - t0))
