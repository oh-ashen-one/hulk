# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
# Brute skin fix: re-weights the shoulder/armpit/deltoid/trap region (harmonic arm-vs-torso field with the fused arm-lat contact
# cut), cleans arm<->torso cross weights, smooths elbows, makes the head/hair rigid, prunes to 4 influences, normalises, keeps
# UV-seam duplicates identical. SAME armature object / bone names / bind pose / scale: every existing clip plays on it.
# Deformation quality is measured with a numpy LBS evaluator over every 2nd frame of all brute_v5 clips.
# usage: Blender -b --factory-startup -P tools/brute/mesh_fix.py -- <in_rig.glb> <out.glb> [--eval-only] [--params k=v,...]
import bpy, sys, os, json, math, time
import numpy as np
from mathutils import Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mesh_common as C

argv = sys.argv[sys.argv.index('--') + 1:]
RIG, OUT = argv[0], argv[1]
EVAL_ONLY = '--eval-only' in argv
P = dict(
    s1=0.30,        # along the upper arm (0 shoulder joint .. 1 elbow): arm-surface classification starts here
    s_arm=0.60,     # arm surface pinned 100% to the arm chain from here down
    r_tor=0.30,     # torso verts farther than this from the shoulder joint are pinned to the torso
    lat_cut=9.0,    # arm-vs-torso contact edges are cut (no diffusion) for s >= lat_cut (9 = off)
    cap_r=0.42,     # free (re-solved) region radius around the shoulder joint, in rig units (height 2.37)
    cap_lat=0.02,   # outward-facing deltoid verts more lateral than (joint + cap_lat) are pinned to the arm
    cap_up=0.10,    # ... and only if not higher than joint + cap_up (the trap ridge stays torso)
    med=0.20,       # verts more medial than (joint - med) are pinned to the torso
    rad_k=1.15,     # arm radius tolerance for the arm-surface classification
    band_it=6,      # smoothing iterations in the transition band (blend into untouched weights)
    elbow_it=8,     # elbow weight smoothing iterations (Arm/ForeArm only)
    elbow_r=0.16,   # elbow smoothing radius around the elbow joint
    head_rigid=1,   # hair/skull verts -> 100% Head
    hair_lum=0.06, hair_dz=0.08,  # base-colour luminance below which a head vertex is hair
    min_w=0.01,
    steps=38,       # bitmask: 1 harmonic shoulder (experimental), 2 elbow smoothing, 4 rigid head, 8 band smoothing,
                    # 16 data-driven shoulder refinement (experimental), 32 bone-heat body base (default: 32+4+2)
    neck_blend=0.10, keep_legs=1, heat_hips=0, up_lo=0.02, up_hi=0.2, up_dz0=0.12, up_dz1=0.0, loose_k=0, loose_max=200,
    clav_m0=0.10, clav_m1=0.32,
    torso_clean=1, tc_r0=0.20, tc_r1=0.34, tc_k0=1.15, tc_k1=1.6, clav_z0=0.20, clav_z1=0.40,  # clavicle (Shoulder) weight fades out towards the spine midline between these |y| offsets
    ref_it=300, ref_lam=0.5, ref_mu=0.1, ref_step=0.01, ref_beta=1.0, ref_tau=0.5,
)
if '--params' in argv:
    for kv in argv[argv.index('--params') + 1].split(','):
        k, v = kv.split('='); P[k] = type(P[k])(float(v)) if not isinstance(P[k], int) else int(float(v))
print('PARAMS', P)
os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
P_HEAT = os.path.join(C.OUTD, 'heat_weights_welded.npy')

C.reset()
acts = C.load_anim_actions()
arm, me, objs = C.load_rig(RIG)
C.rest_pose(arm); bpy.context.view_layer.update()
sc = bpy.context.scene
names = [g.name for g in me.vertex_groups]
G = len(names); gi = {n: j for j, n in enumerate(names)}
W, _ = C.weights(me)
rest = C.rest_co(me)
wid, nW = C.weld_map(rest)
_, rep = np.unique(wid, return_index=True)
X0 = rest[rep]
W0 = W[rep].copy()
Tw = wid[C.tris(me)]
Tw = Tw[(Tw[:, 0] != Tw[:, 1]) & (Tw[:, 1] != Tw[:, 2]) & (Tw[:, 0] != Tw[:, 2])]
Ew = np.sort(np.concatenate([Tw[:, [0, 1]], Tw[:, [1, 2]], Tw[:, [2, 0]]]), 1); Ew = np.unique(Ew, axis=0)
fn = np.cross(X0[Tw[:, 1]] - X0[Tw[:, 0]], X0[Tw[:, 2]] - X0[Tw[:, 0]])
VN = np.zeros_like(X0)
for k in range(3): np.add.at(VN, Tw[:, k], fn)
VN /= np.maximum(1e-12, np.linalg.norm(VN, axis=1, keepdims=True))
print('welded verts', nW, 'tris', len(Tw), 'edges', len(Ew))

def bhead(n): return np.array(arm.matrix_world @ arm.data.bones[n].head_local)

# ---------------------------------------------------------------- frame bank + numpy LBS
bones = [arm.data.bones[n] for n in names]
Amw = arm.matrix_world.copy(); Ainv = Amw.inverted()
def bank_frames(step=2):
    Ds, tags = [], []
    for clip, a in sorted(acts.items()):
        C.assign(arm, a); f0, f1 = int(round(a.frame_range[0])), int(round(a.frame_range[1]))
        for f in range(f0, f1 + 1, step):
            sc.frame_set(f)
            D = np.stack([np.array(Amw @ arm.pose.bones[b.name].matrix @ b.matrix_local.inverted() @ Ainv)[:3, :] for b in bones])
            Ds.append(D); tags.append((clip, f))
    arm.animation_data.action = None
    return np.stack(Ds), tags
t0 = time.time(); BANK, TAGS = bank_frames(); print('bank', BANK.shape, '%.1fs' % (time.time() - t0))

def lbs(Wv, D, X=X0):
    M = np.einsum('vb,bij->vij', Wv, D)  # (V,3,4)
    return np.einsum('vij,vj->vi', M[:, :, :3], X) + M[:, :, 3], M[:, :, :3]

# rest triangle data for the distortion metric
e1 = X0[Tw[:, 1]] - X0[Tw[:, 0]]; e2 = X0[Tw[:, 2]] - X0[Tw[:, 0]]
g11, g12, g22 = (e1 * e1).sum(1), (e1 * e2).sum(1), (e2 * e2).sum(1)
detG0 = g11 * g22 - g12 * g12
A0 = 0.5 * np.sqrt(np.maximum(detG0, 1e-20))
N0 = np.cross(e1, e2); N0 /= np.maximum(1e-12, np.linalg.norm(N0, axis=1, keepdims=True))
def tri_region(Wv):
    TWv = Wv[Tw].sum(1)
    sh = [gi[s + x] for s in ('Left', 'Right') for x in ('Shoulder', 'Arm')]
    tor = [gi['Spine2'], gi['Spine1'], gi['Spine'], gi['Neck']]
    dom = TWv.argmax(1); grp = lambda f: np.isin(dom, [gi[n] for n in names if f(n)])
    return {'shoulder': (TWv[:, sh].sum(1) > 0.15) & (TWv[:, tor].sum(1) > 0.15),
            'arm': grp(lambda n: n.endswith('Arm') or n.endswith('Shoulder')), 'hand': grp(lambda n: 'Hand' in n),
            'headneck': grp(lambda n: n in ('Head', 'Neck')), 'torso': grp(lambda n: n in ('Spine', 'Spine1', 'Spine2')),
            'hipsleg': grp(lambda n: n == 'Hips' or 'Leg' in n or 'Foot' in n or 'Toe' in n)}
def evaluate(Wv, label):
    tot = dict(dist=0.0, flips=0, flips_sh=0, sheared=0, stretch_gt2=0, worst_dist=0.0)
    regs = tri_region(W0)  # fixed region definition (original weights) so before/after compare the same triangles
    for f in range(len(BANK)):
        X, M = lbs(Wv, BANK[f])
        p1 = X[Tw[:, 1]] - X[Tw[:, 0]]; p2 = X[Tw[:, 2]] - X[Tw[:, 0]]
        h11, h12, h22 = (p1 * p1).sum(1), (p1 * p2).sum(1), (p2 * p2).sum(1)
        # eigenvalues of G0^-1 H  (squared singular values of the in-plane deformation gradient)
        tr = (g22 * h11 - 2 * g12 * h12 + g11 * h22) / np.maximum(detG0, 1e-20)
        dt = (h11 * h22 - h12 * h12) / np.maximum(detG0, 1e-20)
        disc = np.sqrt(np.maximum(tr * tr / 4 - dt, 0))
        l1 = np.maximum(tr / 2 + disc, 1e-8); l2 = np.maximum(tr / 2 - disc, 1e-8)
        dist = 0.25 * (np.log(l1) ** 2 + np.log(l2) ** 2)
        dist = np.minimum(dist, 4.0)
        Mavg = M[Tw].mean(1)
        ne = np.einsum('tij,tj->ti', Mavg, N0); ne /= np.maximum(1e-12, np.linalg.norm(ne, axis=1, keepdims=True))
        nn = np.cross(p1, p2); nn /= np.maximum(1e-12, np.linalg.norm(nn, axis=1, keepdims=True))
        dot = (nn * ne).sum(1)
        tot['dist'] += float((dist * A0).sum() / A0.sum())
        tot['worst_dist'] = max(tot['worst_dist'], float(np.percentile(dist, 99.5)))
        tot['flips'] += int((dot < 0).sum()); tot['flips_sh'] += int((dot[regs['shoulder']] < 0).sum())
        for k_, m_ in regs.items(): tot['fl_' + k_] = tot.get('fl_' + k_, 0) + int((dot[m_] < 0).sum()); tot['sh_' + k_] = tot.get('sh_' + k_, 0) + int((dot[m_] < 0.5).sum())
        tot['sheared'] += int((dot < 0.5).sum()); tot['stretch_gt2'] += int((l1 > 4).sum())
    n = len(BANK)
    out = dict(label=label, mean_dist=tot['dist'] / n, p995_dist_max=tot['worst_dist'], flips_per_frame=tot['flips'] / n,
               flips_shoulder_per_frame=tot['flips_sh'] / n, sheared_per_frame=tot['sheared'] / n, stretch2x_per_frame=tot['stretch_gt2'] / n)
    out['by_region_flips_per_frame'] = {k[3:]: round(v / n, 1) for k, v in tot.items() if k.startswith('fl_')}
    out['by_region_sheared_per_frame'] = {k[3:]: round(v / n, 1) for k, v in tot.items() if k.startswith('sh_')}
    print('EVAL REGIONS', label, 'flips', out['by_region_flips_per_frame'], 'sheared', out['by_region_sheared_per_frame'])
    print('EVAL %-8s dist %.4f  p99.5max %.3f  flips/f %.1f (shoulder %.1f)  sheared/f %.1f  stretch>2x/f %.1f' % (
        label, out['mean_dist'], out['p995_dist_max'], out['flips_per_frame'], out['flips_shoulder_per_frame'], out['sheared_per_frame'], out['stretch2x_per_frame']))
    return out

# check the numpy LBS matches Blender's armature modifier on one frame
C.assign(arm, acts['Lift']); sc.frame_set(74)
D = np.stack([np.array(Amw @ arm.pose.bones[b.name].matrix @ b.matrix_local.inverted() @ Ainv)[:3, :] for b in bones])
Xb = C.eval_co(me)[rep]; Xn, _ = lbs(W0, D)
print('LBS check max err', float(np.abs(Xb - Xn).max()))
arm.animation_data.action = None; C.rest_pose(arm)

# ---------------------------------------------------------------- graph helpers
def neighbours_mean(F, Ewk, wts=None):
    """mean of neighbour values over edge list Ewk (undirected)"""
    acc = np.zeros_like(F); cnt = np.zeros(len(F))
    a, b = Ewk[:, 0], Ewk[:, 1]
    np.add.at(acc, a, F[b]); np.add.at(acc, b, F[a]); np.add.at(cnt, a, 1); np.add.at(cnt, b, 1)
    return acc / np.maximum(cnt, 1)[:, None] if F.ndim == 2 else acc / np.maximum(cnt, 1)

def harmonic(fixed_mask, fixed_val, Ewk, free_mask, it=4000):
    """Laplace solve on the edge graph (Jacobi with over-relaxation); values outside free_mask stay as given"""
    # conjugate gradient on the graph Laplacian restricted to the unknowns (Dirichlet values elsewhere)
    a, b = Ewk[:, 0], Ewk[:, 1]
    deg = (np.bincount(a, minlength=nW) + np.bincount(b, minlength=nW)).astype(float)
    upd = free_mask & ~fixed_mask
    h = np.where(fixed_mask | ~free_mask, fixed_val, 0.0).astype(float)
    def Lx(x):  # Laplacian (D - A) x
        return deg * x - (np.bincount(a, weights=x[b], minlength=nW) + np.bincount(b, weights=x[a], minlength=nW))
    rhs = -Lx(np.where(upd, 0.0, h)); rhs[~upd] = 0
    x = np.zeros(nW); r = rhs.copy(); p = r.copy(); rs = r @ r
    for _ in range(it):
        Ap = Lx(p); Ap[~upd] = 0
        al = rs / max(p @ Ap, 1e-30); x += al * p; r -= al * Ap
        rn = r @ r
        if rn < 1e-14: break
        p = r + (rn / rs) * p; rs = rn
    h[upd] = x[upd]
    return np.clip(h, 0, 1)

def finalize(Wv, min_w):
    Wv = np.where(Wv < min_w, 0, Wv)
    # cap 4 influences
    if (Wv > 0).sum(1).max() > 4:
        idx = np.argsort(-Wv, 1)[:, 4:]
        np.put_along_axis(Wv, idx, 0, 1)
    s = Wv.sum(1, keepdims=True)
    return Wv / np.maximum(s, 1e-12)

ARMCH = {s: [gi[n] for n in names if n.startswith(s) and ('Arm' in n or 'Hand' in n)] for s in ('Left', 'Right')}
before = evaluate(W0, 'before')
if '--evalw' in argv:
    Wx = np.load(argv[argv.index('--evalw') + 1]); bad = Wx.sum(1) < 1e-6; Wx[bad] = W0[bad]
    evaluate(finalize(Wx, P['min_w']), 'evalw'); sys.exit(0)
if EVAL_ONLY: sys.exit(0)

# ---------------------------------------------------------------- 0. connected components (welded)
adj = [[] for _ in range(nW)]
for a_, b_ in Ew: adj[a_].append(b_); adj[b_].append(a_)
comp = -np.ones(nW, int); nc = 0
for v0 in range(nW):
    if comp[v0] >= 0: continue
    st = [v0]; comp[v0] = nc
    while st:
        x = st.pop()
        for y in adj[x]:
            if comp[y] < 0: comp[y] = nc; st.append(y)
    nc += 1
csize = np.bincount(comp); mainc = csize.argmax(); MAIN = comp == mainc
print('components', nc, 'sizes', sorted(csize.tolist(), reverse=True)[:12])
for c_ in np.argsort(-csize)[1:]:
    m_ = comp == c_; dm = W0[m_].sum(0); top = np.argsort(-dm)[:3]
    print('  part %d verts %d z %.2f..%.2f  bones %s' % (c_, m_.sum(), X0[m_, 2].min(), X0[m_, 2].max(), [(names[j], round(float(dm[j] / m_.sum()), 2)) for j in top]))

Wn = W0.copy()
report = {'params': P, 'components': sorted(csize.tolist(), reverse=True)}
# ---------------------------------------------------------------- 0b. bone-heat base (mesh_heat.py) for the body, original head/neck
if P['steps'] & 32:
    Wh = np.load(P_HEAT)
    okh = MAIN & (Wh.sum(1) > 1e-6)
    Wh = Wh / np.maximum(Wh.sum(1, keepdims=True), 1e-12)
    hd, nk = gi['Head'], gi['Neck']
    Hj, Nj, S2 = bhead('Head'), bhead('Neck'), bhead('Spine2')
    # keep original weights on the head + upper neck; blend to heat from the neck joint down to (neck joint - neck_blend)
    tz = np.clip((X0[:, 2] - (Nj[2] - P['neck_blend'])) / max(P['neck_blend'], 1e-6), 0, 1)
    headish = (W0[:, hd] + W0[:, nk]) > 0.5
    keep = np.where(headish, 1.0, tz * (W0[:, hd] + W0[:, nk] > 0.05))
    # heat only for the upper body (arms, hands, shoulders, chest/upper back): the lower torso / waist / shorts / legs keep the
    # source weights (the shorts layer and the separate right-leg shell are skinned to them; heat there opens the waistband)
    if P['keep_legs']:
        upc = [j for j, n in enumerate(names) if 'Arm' in n or 'Hand' in n or 'Shoulder' in n]
        wup = W0[:, upc].sum(1)  # the source's arm/clavicle share decides where heat may take over ...
        # ... plus the upper back / chest (Spine2 territory) above the lower back, which must keep the source weights (waistband)
        s2z = bhead('Spine2')[2]
        fzu = np.clip((X0[:, 2] - (s2z - P['up_dz0'])) / max(P['up_dz0'] - P['up_dz1'], 1e-6), 0, 1)
        wup = np.maximum(wup, fzu * (W0[:, gi['Spine2']] + Wh[:, upc].sum(1)))
        keep = np.maximum(keep, 1 - np.clip((wup - P['up_lo']) / max(P['up_hi'] - P['up_lo'], 1e-6), 0, 1))
    keep = np.where(okh, keep, 1.0)
    for _ in range(4): keep = 0.5 * keep + 0.5 * neighbours_mean(keep, Ew)  # soften the seam between the two sources
    keep = np.where(okh, keep, 1.0)
    Wn = keep[:, None] * W0 + (1 - keep)[:, None] * Wh
    report['heat'] = dict(heat_verts=int(okh.sum()), kept_original=int((keep > 0.99).sum()), blended=int(((keep > 0.01) & (keep < 0.99)).sum()))
    print('HEAT', report['heat'])
    if P['torso_clean']:
        # bone heat lets the arm/clavicle bones reach far into the back/lats (mid-back verts with Arm 0.2 / clavicle 0.3 pull the
        # lower back up when the arms swing). Arm-chain weight on torso skin fades with distance from the arm; clavicle weight
        # fades below the shoulder line. Freed weight goes back to the source's torso distribution of that vertex.
        freed = np.zeros(nW)
        tor_src = W0.copy()
        for S in ('Left', 'Right'):
            tor_src[:, [gi[n] for n in names if n.startswith(S) and ('Arm' in n or 'Hand' in n or 'Shoulder' in n)]] = 0
        ts = tor_src.sum(1, keepdims=True); tor_src = np.where(ts > 0.05, tor_src / np.maximum(ts, 1e-9), 0)
        tor_src[(ts[:, 0] <= 0.05), gi['Spine2']] = 1
        for S in ('Left', 'Right'):
            J, E_, Hh = bhead(S + 'Arm'), bhead(S + 'ForeArm'), bhead(S + 'Hand')
            def proj(a, b):
                ab = b - a; u = (X0 - a) @ ab / (ab @ ab); uc = np.clip(u, 0, 1); c = a + uc[:, None] * ab; return u, np.linalg.norm(X0 - c, axis=1)
            u1, d1 = proj(J, E_); u2, d2 = proj(E_, Hh)
            sarm = np.where(d2 < d1, 1 + np.clip(u2, 0, 1), u1); darm = np.minimum(d1, d2)
            chain = [gi[n] for n in names if n.startswith(S) and ('Arm' in n or 'Hand' in n)]
            wa_src = W0[:, chain].sum(1)
            bins = np.linspace(0, 2, 21); Rb = np.zeros(20)
            for k in range(20):
                m = (wa_src > 0.95) & (sarm >= bins[k]) & (sarm < bins[k + 1])
                Rb[k] = np.percentile(darm[m], 95) if m.sum() > 5 else np.nan
            Rb = np.where(np.isnan(Rb), np.nanmax(Rb), Rb); Rv = Rb[np.clip((np.clip(sarm, 0, 1.99) * 10).astype(int), 0, 19)]
            dJ = np.linalg.norm(X0 - J, axis=1)
            f_med = np.clip((P['tc_r1'] - dJ) / (P['tc_r1'] - P['tc_r0']), 0, 1)          # torso side of the joint
            f_lat = np.clip((P['tc_k1'] * Rv - darm) / ((P['tc_k1'] - P['tc_k0']) * Rv), 0, 1)  # beside the arm (lats)
            f = np.where(sarm <= 0.05, np.maximum(f_med, f_lat * (dJ < P['tc_r0'])), f_lat)
            f = np.where(MAIN & (wa_src < 0.5), f, 1.0)  # only skin the source calls torso
            for j in chain:
                take = Wn[:, j] * (1 - f); Wn[:, j] -= take; freed += take
            cj = gi[S + 'Shoulder']; Sz = bhead(S + 'Shoulder')[2]
            fz = np.clip((X0[:, 2] - (Sz - P['clav_z1'])) / (P['clav_z1'] - P['clav_z0']), 0, 1)
            take = Wn[:, cj] * (1 - fz) * MAIN; Wn[:, cj] -= take; freed += take
        Wn += freed[:, None] * tor_src
        report['torso_clean_freed_weight'] = float(freed.sum()); print('TORSO CLEAN freed', freed.sum(), 'verts touched', int((freed > 0.01).sum()))
    if P['clav_m1'] > 0:
        ymid = 0.5 * (bhead('LeftShoulder')[1] + bhead('RightShoulder')[1])
        f = np.clip((np.abs(X0[:, 1] - ymid) - P['clav_m0']) / max(P['clav_m1'] - P['clav_m0'], 1e-6), 0, 1)
        f = f * f * (3 - 2 * f)
        moved = 0.0
        for S in ('Left', 'Right'):
            j = gi[S + 'Shoulder']; take = Wn[:, j] * (1 - f) * MAIN
            Wn[:, j] -= take; Wn[:, gi['Spine2']] += take; moved += take.sum()
        report['clavicle_weight_moved_to_Spine2'] = float(moved); print('CLAV moved', moved)

# ---------------------------------------------------------------- 1. shoulder / armpit / deltoid / trap
report['params'] = P
regL = regR = np.zeros(nW, bool)
for S in (('Left', 'Right') if P['steps'] & 1 else ()):
    J, E, Hh = bhead(S + 'Arm'), bhead(S + 'ForeArm'), bhead(S + 'Hand')
    lat = np.array([0.0, 1.0 if S == 'Left' else -1.0, 0.0])  # outward (character faces +X, left arm at +Y)
    # closest point on the J-E-H polyline
    def proj(a, b):
        ab = b - a; u = np.clip(((X0 - a) @ ab) / (ab @ ab), 0, 1); c = a + u[:, None] * ab; return u, c, np.linalg.norm(X0 - c, axis=1)
    u1, c1, d1 = proj(J, E); u2, c2, d2 = proj(E, Hh)
    use2 = d2 < d1
    s = np.where(use2, 1 + u2, u1); c = np.where(use2[:, None], c2, c1); d = np.minimum(d1, d2)
    o = ((X0 - c) * VN).sum(1) / np.maximum(d, 1e-9)
    Wsrc = Wn.copy(); ach = ARMCH[S]; wa0 = Wsrc[:, ach].sum(1)
    # arm radius profile from confidently-arm verts
    bins = np.linspace(0, 2, 21); R = np.zeros(20)
    for k in range(20):
        m = (wa0 > 0.95) & (s >= bins[k]) & (s < bins[k + 1])
        R[k] = np.percentile(d[m], 95) if m.sum() > 5 else np.nan
    R = np.where(np.isnan(R), np.nanmax(R), R)
    Rv = R[np.clip((s * 10).astype(int), 0, 19)]
    A = (s >= P['s1']) & (o > 0.0) & (d < P['rad_k'] * Rv) & (s < 1.95)
    nearJ = np.linalg.norm(X0 - J, axis=1)
    vic = (d < 2.0 * Rv) & (s < 1.95)
    Tt = vic & ~A & (wa0 < 0.5)  # torso-side verts beside the arm (lats/pecs)
    lc = (X0 - J) @ lat  # lateral coordinate relative to the joint
    up = X0[:, 2] - J[2]
    region = (nearJ < P['cap_r']) | (vic & (s >= P['s1']) & (s < 1.0))
    fixed = np.zeros(nW, bool); val = np.zeros(nW)
    # arm pins: arm surface down the upper arm/forearm; outward-facing deltoid cap
    pin_arm = ((A | (wa0 > 0.95)) & (s >= P['s_arm'])) | ((nearJ < P['cap_r']) & (lc > P['cap_lat']) & (up < P['cap_up']) & (o > -0.2) & (wa0 > 0.2))
    pin_tor = (region & (lc < -P['med'])) | (region & ~A & (wa0 < 0.5) & (nearJ > P['r_tor']))
    pin_tor &= ~pin_arm
    fixed |= pin_arm; val[pin_arm] = 1
    fixed |= pin_tor; val[pin_tor] = 0
    # outside the region: keep the original arm share as boundary condition
    outside = ~region
    fixed |= outside; val[outside] = wa0[outside]
    # cut arm<->torso contact edges along the fused inner upper arm
    ea, eb = Ew[:, 0], Ew[:, 1]
    cut = ((A[ea] & Tt[eb]) | (A[eb] & Tt[ea])) & (np.maximum(s[ea], s[eb]) >= P['lat_cut'])
    Ek = Ew[~cut]
    h = harmonic(fixed, val, Ek, region)
    # rebuild weights in region: arm share h split by the original arm-chain ratios, torso share split by original torso ratios
    tor_cols = [j for j in range(G) if j not in ach]
    Wa = Wsrc[:, ach].copy(); Wt = Wsrc[:, tor_cols].copy()
    sa_, st_ = Wa.sum(1), Wt.sum(1)
    # fallbacks: no arm weights -> Arm/ForeArm by s ; no torso weights -> diffuse torso distribution from neighbours
    fa = np.zeros((nW, len(ach))); jA, jF = ach.index(gi[S + 'Arm']), ach.index(gi[S + 'ForeArm'])
    fa[:, jA] = np.clip(1.5 - s, 0, 1); fa[:, jF] = 1 - fa[:, jA]
    Wa = np.where(sa_[:, None] > 0.05, Wa / np.maximum(sa_, 1e-9)[:, None], fa)
    td = np.where(st_[:, None] > 0.3, Wt / np.maximum(st_, 1e-9)[:, None], 0)
    have = st_ > 0.3
    for _ in range(60):  # flood-fill the torso distribution into verts that had (almost) none
        nb = neighbours_mean(td, Ew)
        fill = ~have & (nb.sum(1) > 1e-6)
        td[fill] = nb[fill] / nb[fill].sum(1, keepdims=True); have = have | fill
    Wt = np.where(st_[:, None] > 0.3, Wt / np.maximum(st_, 1e-9)[:, None], td)
    newW = np.zeros((nW, G)); newW[:, ach] = Wa * h[:, None]; newW[:, tor_cols] = Wt * (1 - h)[:, None]
    Wn[region] = newW[region]
    report[S] = dict(region=int(region.sum()), arm_pins=int(pin_arm.sum()), torso_pins=int(pin_tor.sum()), cut_edges=int(cut.sum()),
                     arm_surface=int(A.sum()), torso_beside=int(Tt.sum()), R=[round(float(x), 3) for x in R])
    print(S, report[S])
    if S == 'Left': regL = region
    else: regR = region
reg_any = regL | regR

# ---------------------------------------------------------------- 1b. data-driven refinement of the shoulder weights
# minimise (over every 4th frame of every clip) the log edge-strain of the deformed mesh + weight smoothness + closeness to
# the harmonic initialisation; per vertex the weights live on the simplex over 7 candidate bones; projected gradient (Adam).
def simplex_proj(V):
    """project rows of V onto the probability simplex"""
    n = V.shape[1]; U = -np.sort(-V, 1); css = np.cumsum(U, 1) - 1
    ind = np.arange(1, n + 1); cond = U - css / ind > 0
    rho = n - 1 - np.argmax(cond[:, ::-1], 1)
    th = css[np.arange(len(V)), rho] / (rho + 1)
    return np.maximum(V - th[:, None], 0)

def refine(Wn, reg_sides, it, lam, mu, step, fstep=4, label='', beta=0.0, tau=0.5):
    Fb = BANK[::fstep]
    for S, rg in reg_sides:
        cand = [gi[S + 'Shoulder'], gi[S + 'Arm'], gi[S + 'ForeArm'], gi['Spine2'], gi['Spine1'], gi['Spine'], gi['Neck']]
        other = [j for j in range(G) if j not in cand]
        # optimisation set: region verts (+1 ring) whose weight is (almost) all on the candidate bones
        ring = rg.copy(); ring[Ew[rg[Ew[:, 0]] | rg[Ew[:, 1]]].ravel()] = True
        opt = ring & (Wn[:, other].sum(1) < 0.02)
        oi = np.nonzero(opt)[0]; pos = -np.ones(nW, int); pos[oi] = np.arange(len(oi))
        Er = Ew[opt[Ew[:, 0]] | opt[Ew[:, 1]]]
        L0e = np.linalg.norm(X0[Er[:, 0]] - X0[Er[:, 1]], axis=1)
        vin = np.unique(Er.ravel())  # all verts touching those edges
        # fixed positions of non-opt verts in every frame
        Xh = np.concatenate([X0, np.ones((nW, 1))], 1)
        Xfix = np.einsum('vb,fbij,vj->fvi', Wn[vin], Fb, Xh[vin])  # (F, len(vin), 3)
        vpos = -np.ones(nW, int); vpos[vin] = np.arange(len(vin))
        Y = np.einsum('fkij,vj->fvki', Fb[:, cand], Xh[oi])  # (F, nopt, K, 3)
        Wk = Wn[oi][:, cand]; Wk = Wk / np.maximum(Wk.sum(1, keepdims=True), 1e-9)
        Winit = Wk.copy()
        ea, eb = vpos[Er[:, 0]], vpos[Er[:, 1]]
        oa, ob = pos[Er[:, 0]], pos[Er[:, 1]]
        Es = Ew[opt[Ew[:, 0]] & opt[Ew[:, 1]]]; sa, sb = pos[Es[:, 0]], pos[Es[:, 1]]
        m1 = np.zeros_like(Wk); m2 = np.zeros_like(Wk)
        # triangles touching the optimisation set (fold/collapse term)
        Tr = Tw[opt[Tw].any(1)]; tv = vpos[Tr]; to = pos[Tr]
        A0r = 0.5 * np.linalg.norm(np.cross(X0[Tr[:, 1]] - X0[Tr[:, 0]], X0[Tr[:, 2]] - X0[Tr[:, 0]]), axis=1)
        N0r = np.cross(X0[Tr[:, 1]] - X0[Tr[:, 0]], X0[Tr[:, 2]] - X0[Tr[:, 0]]); N0r /= np.linalg.norm(N0r, axis=1, keepdims=True) + 1e-12
        # expected (rigid) normal per frame from the blended rotation of the triangle at the init weights (held fixed)
        Wtri = Wn[Tr].mean(1)
        Mt = np.einsum('tb,fbij->ftij', Wtri, Fb[:, :, :, :3])
        NE = np.einsum('ftij,tj->fti', Mt, N0r); NE /= np.linalg.norm(NE, axis=2, keepdims=True) + 1e-12
        def energy_grad(Wk):
            X = Xfix.copy()
            X[:, vpos[oi]] = np.einsum('vk,fvki->fvi', Wk, Y)
            dv = X[:, ea] - X[:, eb]; ln = np.linalg.norm(dv, axis=2); r = ln / L0e
            lr = np.log(np.maximum(r, 1e-6))
            E = (lr ** 2).mean(0).sum()
            gx = (2 * lr / np.maximum(ln, 1e-9) ** 2)[..., None] * dv / len(Fb)  # dE/d(xa) ; dE/d(xb) = -gx
            gv = np.zeros((len(Fb), len(oi), 3))
            ma, mb = oa >= 0, ob >= 0
            for k_ in range(len(Fb)):
                np.add.at(gv[k_], oa[ma], gx[k_, ma]); np.add.at(gv[k_], ob[mb], -gx[k_, mb])
            if beta > 0:
                p1 = X[:, tv[:, 1]] - X[:, tv[:, 0]]; p2 = X[:, tv[:, 2]] - X[:, tv[:, 0]]
                a = 0.5 * (np.cross(p1, p2) * NE).sum(2) / A0r  # signed area ratio along the expected normal
                viol = np.maximum(tau - a, 0)
                E += beta * (viol ** 2).mean(0).sum()
                ga = (-2 * beta * viol / len(Fb) * 0.5 / A0r)[..., None]  # dE/d(cross.NE)
                g1 = ga * np.cross(p2, NE); g2 = ga * np.cross(NE, p1); g0 = -(g1 + g2)
                for c_, gg in ((0, g0), (1, g1), (2, g2)):
                    mm = to[:, c_] >= 0
                    for k_ in range(len(Fb)): np.add.at(gv[k_], to[mm, c_], gg[k_, mm])
            gW = np.einsum('fvi,fvki->vk', gv, Y)
            dw = Wk[sa] - Wk[sb]
            E += lam * (dw ** 2).sum() + mu * ((Wk - Winit) ** 2).sum()
            gW_s = np.zeros_like(Wk); np.add.at(gW_s, sa, 2 * dw); np.add.at(gW_s, sb, -2 * dw)
            gW += lam * gW_s + 2 * mu * (Wk - Winit)
            return E, gW
        supp = np.ones_like(Wk, bool); E0, g0 = energy_grad(Wk)
        if os.environ.get('GRADCHECK'):
            for (vi, ki) in [(5, 1), (50, 3), (100, 0)]:
                Wp = Wk.copy(); Wp[vi, ki] += 1e-5; Ep, _ = energy_grad(Wp)
                print('GRADCHECK', g0[vi, ki], (Ep - E0) / 1e-5)
        for t in range(1, it + 1):
            E, gW = energy_grad(Wk)
            m1 = 0.9 * m1 + 0.1 * gW; m2 = 0.999 * m2 + 0.001 * gW * gW
            upd = (m1 / (1 - 0.9 ** t)) / (np.sqrt(m2 / (1 - 0.999 ** t)) + 1e-8)
            Wk = simplex_proj(Wk - step * upd)
            if t == it * 3 // 4:  # sparsify to 4 influences, keep optimising on that support
                idx = np.argsort(-Wk, 1)[:, 4:]; np.put_along_axis(Wk, idx, 0, 1); Wk = Wk / Wk.sum(1, keepdims=True)
                supp = Wk > 0
            if t > it * 3 // 4:
                Wk = np.where(supp, Wk, 0); Wk = Wk / np.maximum(Wk.sum(1, keepdims=True), 1e-9)
        print('REFINE %s %s verts %d edges %d  E %.2f -> %.2f' % (label, S, len(oi), len(Er), E0, E))
        Wo = np.zeros((len(oi), G)); Wo[:, cand] = Wk
        Wn[oi] = Wo
    return Wn

if P['steps'] & 16:
    Wn = refine(Wn, [('Left', regL), ('Right', regR)], P['ref_it'], P['ref_lam'], P['ref_mu'], P['ref_step'], beta=P['ref_beta'], tau=P['ref_tau'])

# ---------------------------------------------------------------- 2. elbows: smooth Arm/ForeArm split inside a radius
for S in (('Left', 'Right') if P['steps'] & 2 else ()):
    Ej = bhead(S + 'ForeArm'); m = np.linalg.norm(X0 - Ej, axis=1) < P['elbow_r']
    cols = [gi[S + 'Arm'], gi[S + 'ForeArm']]
    Ek_ = Ew[m[Ew[:, 0]] & m[Ew[:, 1]]]
    for _ in range(P['elbow_it']):
        tot = Wn[:, cols].sum(1)
        frac = Wn[:, cols[0]] / np.maximum(tot, 1e-9)
        nb = neighbours_mean(frac, Ek_)
        frac2 = np.where(m & (tot > 0.5), 0.5 * frac + 0.5 * nb, frac)
        Wn[:, cols[0]] = frac2 * tot; Wn[:, cols[1]] = (1 - frac2) * tot

# ---------------------------------------------------------------- 3. head / hair rigid
def vertex_albedo():
    """mean base-colour texel per welded vertex (corner UVs averaged), used to find the hair (dark) on the head"""
    mat = me.data.materials[0]; img = None
    bsdf = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    def up(sock):
        for l in sock.links:
            n = l.from_node
            if n.type == 'TEX_IMAGE': return n.image
            for i in n.inputs:
                r = up(i)
                if r: return r
        return None
    img = up(bsdf.inputs['Base Color'])
    w, h = img.size; px = np.empty(w * h * 4, dtype=np.float32); img.pixels.foreach_get(px); px = px.reshape(h, w, 4)
    d = me.data; uv = np.empty(len(d.loops) * 2); d.uv_layers.active.data.foreach_get('uv', uv); uv = uv.reshape(-1, 2)
    lv = np.empty(len(d.loops), dtype=np.int64); d.loops.foreach_get('vertex_index', lv)
    xi = np.clip((uv[:, 0] % 1) * w, 0, w - 1).astype(int); yi = np.clip((uv[:, 1] % 1) * h, 0, h - 1).astype(int)
    c = px[yi, xi, :3]; acc = np.zeros((nW, 3)); cnt = np.zeros(nW)
    np.add.at(acc, wid[lv], c); np.add.at(cnt, wid[lv], 1)
    return acc / np.maximum(cnt, 1)[:, None], img.name

if P['head_rigid'] and P['steps'] & 4:
    hd = gi['Head']; Hj = bhead('Head'); Nk = bhead('Neck')
    alb, imname = vertex_albedo(); lum = alb @ np.array([0.2126, 0.7152, 0.0722])
    headish = (W0[:, hd] > 0.3) & (X0[:, 2] > Nk[2])
    # hair = dark texels on the head (green skin ~0.25+, black hair < hair_lum); grow by one ring to catch strand edges
    hair = headish & (lum < P['hair_lum'])
    ring = hair.copy(); ring[Ew[hair[Ew[:, 0]] | hair[Ew[:, 1]]].ravel()] = True
    hair = ring & headish & (lum < P['hair_lum'] * 2.0)
    skull = (X0[:, 2] > Hj[2] + 0.02) & (W0[:, hd] > 0.5)
    rigid = (hair | skull) & MAIN
    report['head_rigid_verts'] = int(rigid.sum()); report['hair_verts'] = int(hair.sum())
    report['head_rigid_had_other'] = int((rigid & (Wn[:, hd] < 0.999)).sum()); report['hair_albedo_image'] = imname
    print('HEAD rigid', report['head_rigid_verts'], 'hair', report['hair_verts'], 'had other', report['head_rigid_had_other'])
    # rigid amount: 1 on the skull and on hair above the head joint, ramping to 0 down the nape over hair_dz (the nape hair keeps
    # part of its neck blend, otherwise the neck skin under a rigid hair cap creases when the head tilts back)
    amt = np.where(skull, 1.0, np.clip((X0[:, 2] - (Hj[2] - P['hair_dz'])) / P['hair_dz'], 0, 1)) * rigid
    Wn = Wn * (1 - amt)[:, None]; Wn[:, hd] += amt
    # soften the hairline: skin verts next to the cap get pulled part of the way to the cap's amount
    cur = amt > 0.5
    for k_, f_ in enumerate((0.5, 0.3, 0.15)):
        nb = np.zeros(nW, bool); nb[Ew[cur[Ew[:, 0]] | cur[Ew[:, 1]]].ravel()] = True; nb &= ~cur & MAIN & headish
        a2 = f_ * np.clip((X0[nb, 2] - (Hj[2] - P['hair_dz'])) / P['hair_dz'], 0, 1)
        Wn[nb] *= (1 - a2)[:, None]; Wn[nb, hd] += a2; cur |= nb

# ---------------------------------------------------------------- 4. transition band smoothing (region border) + finalize
band = np.zeros(nW, bool)
for S, rg in (('Left', regL), ('Right', regR)):
    e_cross = rg[Ew[:, 0]] != rg[Ew[:, 1]]
    b0 = np.zeros(nW, bool); b0[Ew[e_cross].ravel()] = True
    for _ in range(3): b0 |= np.isin(np.arange(nW), Ew[b0[Ew[:, 0]] | b0[Ew[:, 1]]].ravel())
    band |= b0
for _ in range(P['band_it'] if P['steps'] & 8 else 0):
    nb = neighbours_mean(Wn, Ew); Wn[band] = 0.5 * Wn[band] + 0.5 * nb[band]
# ---------------------------------------------------------------- 5. loose parts (eyes, teeth, drawstring, ...) follow the body
li = np.nonzero(~MAIN)[0]
if P['loose_k'] > 0:
    small = ~MAIN & (csize[comp] < P['loose_max'])
    Wn[~MAIN & ~small] = W0[~MAIN & ~small]
    li = np.nonzero(small)[0]; mi = np.nonzero(MAIN)[0]
    for ch in np.array_split(li, max(1, len(li) // 256)):
        d_ = np.linalg.norm(X0[ch][:, None] - X0[mi][None], axis=2)
        nn_ = np.argsort(d_, 1)[:, :P['loose_k']]; dd = np.take_along_axis(d_, nn_, 1)
        w_ = 1 / np.maximum(dd, 1e-5); w_ /= w_.sum(1, keepdims=True)
        Wn[ch] = np.einsum('vk,vkg->vg', w_, Wn[mi][nn_])
else:
    Wn[~MAIN] = W0[~MAIN]  # loose shells (separate right leg, shorts patches, drawstring, eyes) keep their original weights
report['loose_verts_transferred'] = int(len(li)) if P['loose_k'] > 0 else 0
Wn = finalize(Wn, P['min_w'])
after = evaluate(Wn, 'after')
report['before'] = before; report['after'] = after
report['changed_welded_verts(>0.05)'] = int((np.abs(Wn - W0).max(1) > 0.05).sum())
report['influences_hist'] = {int(k): int(((Wn > 0).sum(1) == k).sum()) for k in range(1, 5)}

# per-clip comparison of shoulder flips
pc = {}
for clip in sorted(acts):
    idx = [i for i, t in enumerate(TAGS) if t[0] == clip]
    rb, ra = 0, 0
    regs = tri_region(W0)['shoulder']
    for i in idx:
        for Wv, key in ((W0, 'b'), (Wn, 'a')):
            X, M = lbs(Wv, BANK[i])
            p1 = X[Tw[:, 1]] - X[Tw[:, 0]]; p2 = X[Tw[:, 2]] - X[Tw[:, 0]]
            ne = np.einsum('tij,tj->ti', M[Tw].mean(1), N0); nn = np.cross(p1, p2)
            fl = int(((nn * ne).sum(1) < 0).sum())
            if key == 'b': rb += fl
            else: ra += fl
    pc[clip] = (round(rb / len(idx), 1), round(ra / len(idx), 1))
report['flips_per_frame_by_clip(before,after)'] = pc
print('PER CLIP flips/frame before->after', pc)

# ---------------------------------------------------------------- write back + export
json.dump(report, open(os.path.splitext(OUT)[0] + '_report.json', 'w'), indent=1, default=float)
np.save(os.path.splitext(OUT)[0] + '_weights_welded.npy', Wn)
if '--noexport' in argv: sys.exit(0)
d = me.data
# smooth per-position normals from the source corner normals (the source is split at every UV seam, which makes Blender
# rebuild normals per UV island under deformation -> island-shaped shading facets; engines skin the exported normals)
ln = np.empty(len(d.loops) * 3); d.corner_normals.foreach_get('vector', ln); ln = ln.reshape(-1, 3)
lv = np.empty(len(d.loops), dtype=np.int64); d.loops.foreach_get('vertex_index', lv)
VNn = np.zeros((nW, 3)); np.add.at(VNn, wid[lv], ln); VNn /= np.maximum(1e-12, np.linalg.norm(VNn, axis=1, keepdims=True))
# weld the UV-seam duplicates (UVs stay per corner; glTF export re-splits them, with identical normals and weights)
bpy.ops.object.select_all(action='DESELECT'); bpy.context.view_layer.objects.active = me; me.select_set(True)
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.remove_doubles(threshold=1e-5)
bpy.ops.object.mode_set(mode='OBJECT')
co_n = np.empty(len(d.vertices) * 3); d.vertices.foreach_get('co', co_n); co_n = co_n.reshape(-1, 3)
Mw = np.array(me.matrix_world); co_n = co_n @ Mw[:3, :3].T + Mw[:3, 3]
key = {tuple(k): i for i, k in enumerate(np.round(X0 / 1e-5).astype(np.int64))}
newid = np.array([key.get(tuple(k), -1) for k in np.round(co_n / 1e-5).astype(np.int64)])
um = np.nonzero(newid < 0)[0]
for i in um: newid[i] = int(np.argmin(np.linalg.norm(X0 - co_n[i], axis=1)))
print('weld: %d verts matched by nearest position' % len(um), 'max dist', float(max([np.linalg.norm(X0[newid[i]] - co_n[i]) for i in um] or [0])))
print('welded mesh verts', len(d.vertices))
if 'sharp_face' in d.attributes: d.attributes.remove(d.attributes['sharp_face'])
if 'sharp_edge' in d.attributes: d.attributes.remove(d.attributes['sharp_edge'])
d.normals_split_custom_set_from_vertices([tuple(v) for v in VNn[newid]])
C.set_weights(me, Wn[newid], names)
report['output'] = dict(verts_blender_welded=len(d.vertices), tris=len(Tw))
for o in bpy.data.objects: o.select_set(o in (arm, me))
if arm.animation_data: arm.animation_data_clear()
for a in list(bpy.data.actions): bpy.data.actions.remove(a)
C.rest_pose(arm)
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True, export_animations=False, export_yup=True,
                          export_skins=True, export_normals=True, export_tangents=False)
json.dump(report, open(os.path.splitext(OUT)[0] + '_report.json', 'w'), indent=1, default=float)
print('WROTE', OUT)
