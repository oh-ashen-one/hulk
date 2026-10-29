# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
# Blind A/B numbers straight from the Actions on the shipped rig (no video): loop seam, foot drift, secondary-motion ratio.
#
#   Blender -b --factory-startup -P tools/brute/v2r/ab_measure.py -- --clip Idle --out <dir> --subject A=<file.glb>[:<Action>] --subject B=<...>
#     --clip      clip name (decides loop vs one-shot via clips_meta.json, and ground vs air handling)
#     --loop / --no-loop   override the loop flag        --root game|raw   as in ab_render.py (game = BruteCharacter.cpp's root treatment)
#     --include-source     also write the subject paths into measure.json (default off: the critic's file stays blind)
#   Writes <out>/measure.json and prints one line per subject:
#     AB_MEASURE <clip> <label> seam x.xx foot_drift_px X secondary x.xx          (seam n/a for one-shots)
#
# Definitions (every number is computed on exactly the frames ab_render.py films: 24 fps samples of the Action key range)
#   seam       loops only. step(i) = mean distance (m) that a 1/40 vertex subsample of the evaluated mesh (corrective shape keys
#              included) moves from sample i to i+1, with the Hips XY removed; seam = the same for last -> first. seam_ratio =
#              seam / median(step). ~1 = a clean wrap, 0 = last frame equals the first (a one-frame hold in a loop), >2 = a pop.
#              The same ratio on the 52 bone heads and the 3 worst bones are in the json.
#   foot drift for each foot (vertices whose dominant skin influence is Foot or ToeBase). The foot is grounded while its lowest
#              vertex is within 2 cm of its own planted level (5th percentile of its lowest-vertex height over the clip; the
#              level itself, planted_level_cm, is reported against the rendered z = 0 floor so a sunken or hovering foot shows).
#              Per run of >= 3 grounded samples: take the foot vertices within 1 cm of the lowest at the run's middle sample,
#              follow that patch rigidly (heel / toe roll does not move it), keep the frames where it stays within 2 cm of its
#              middle height, and take its largest horizontal extent (max pairwise distance). foot_drift_px = the worst of those
#              over both feet and the three fixed cameras (projected with ab_common.CAMERAS); foot_drift_cm is the same in world
#              units. planted_speed_m_s (json) = median net ground speed of long runs: in 'game' mode Hips XY is pinned, so
#              Walk / Run / StopLunge feet slide backwards at stride speed by design: compare it with clips_meta.json speed.
#   secondary  Head + all finger bones: mean speed (m per sample) of each bone head in its parent frame (fingers in their Hand
#              bone's frame, the Head in the Spine2 frame, so arm swing and trunk motion drop out) / mean world speed of the Hips
#              in the Action as exported (floored at 0.5 mm per sample; the root treatment of 'game' mode is not applied). The rig
#              has no hair or shorts bones; head and fingers are what moves independently of the trunk. Compare A with B for the
#              same clip: near 0 = frozen head and hands, much above the other = flicking. world_ratio in the json uses world
#              positions (arm swing included).
import argparse
import json
import os
import sys

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ab_common as C  # noqa: E402
import v2r_rig as R  # noqa: E402

SUB = 40               # mesh subsample stride for the seam
HIPS_FLOOR_M = 0.0005
FRAME_BONES = ('LeftHand', 'RightHand', 'Spine2')


def parse():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    ap = argparse.ArgumentParser(prog='ab_measure.py')
    ap.add_argument('--clip', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--subject', action='append', required=True, help='LABEL=<file.glb>[:<Action>]')
    ap.add_argument('--loop', dest='loop', action='store_true', default=None)
    ap.add_argument('--no-loop', dest='loop', action='store_false')
    ap.add_argument('--root', choices=['game', 'raw'], default='game')
    ap.add_argument('--base', default=C.BASE_GLB)
    ap.add_argument('--include-source', action='store_true')
    return ap.parse_args(argv)


def r(x, n=3):
    return None if x is None else round(float(x), n)


def collect(base, act, clip, mode):
    loop = base_loop
    times = C.sample_times(act, loop)
    grounding = C.grounding_for(clip)
    dz0 = C.first_dz(base, times, mode)
    names = [b.name for b in base.arm.data.bones]
    S = base.foot_sets()
    bones, raw_bones, raw_mats, mesh_sub, foot = [], [], [], [], {k: dict(z=[], xyz=[], V=[]) for k in 'LR'}
    m = base.arm.matrix_world
    for t in times:
        C.pose_frame(base, t, mode, grounding, dz0)
        m = base.arm.matrix_world
        bones.append(np.array([list(m @ base.arm.pose.bones[n].head) for n in names]))
        C.pose_frame(base, t, 'raw')                      # the clip's own motion, for the secondary-motion ratio
        m0 = base.arm.matrix_world
        raw_bones.append(np.array([list(m0 @ base.arm.pose.bones[n].head) for n in names]))
        raw_mats.append(np.array([np.array(m0 @ base.arm.pose.bones[n].matrix) for n in FRAME_BONES]))
        C.pose_frame(base, t, mode, grounding, dz0)
        m = base.arm.matrix_world
        V = R.mesh_world(base.mesh)
        mesh_sub.append(V[::SUB].copy())
        for k in 'LR':
            F = V[S[k]]
            zmin = F[:, 2].min()
            patch = F[F[:, 2] <= zmin + C.CONTACT_PATCH_M]
            foot[k]['z'].append(zmin)
            foot[k]['V'].append(F.astype(np.float32))
    return dict(times=times, names=names, bones=np.array(bones), raw=np.array(raw_bones), raw_mats=np.array(raw_mats), mesh=np.array(mesh_sub), foot={k: dict(z=np.array(v['z']), V=np.array(v['V'])) for k, v in foot.items()}, loop=loop, grounding=grounding)


def step_series(X, hips_xy, cyc):
    """mean point distance between consecutive samples with the hips XY removed; cyc adds last -> first as the final entry"""
    Y = X.copy()
    Y[:, :, 0] -= hips_xy[:, 0:1]
    Y[:, :, 1] -= hips_xy[:, 1:2]
    d = np.linalg.norm(np.diff(Y, axis=0), axis=2)           # (N-1, P)
    seam = np.linalg.norm(Y[0] - Y[-1], axis=1)
    return d, seam


def measure(base, act, clip, mode, cams, scene):
    D = collect(base, act, clip, mode)
    N = len(D['times'])
    names = D['names']
    hi = names.index('Hips')
    hips = D['bones'][:, hi, :]
    out = dict(frames=N, seconds=r((N - 1) / C.FPS), loop=D['loop'], root=mode, grounding=D['grounding'] if mode == 'game' else None)
    # ---- seam
    dm, sm = step_series(D['mesh'], hips[:, :2], True)
    step_m = dm.mean(1)
    med = float(np.median(step_m))
    mesh_seam = float(sm.mean())
    db, sb = step_series(D['bones'], hips[:, :2], True)
    step_b = db.mean(1)
    medb = float(np.median(step_b))
    seam = dict(median_step_mm=r(med * 1000, 3), last_first_gap_mm=r(mesh_seam * 1000, 3), mesh_ratio=r(mesh_seam / max(med, 1e-9), 3),
                bone_ratio=r(float(sb.mean()) / max(medb, 1e-9), 3), duplicate_end_frame=bool(mesh_seam < 5e-5),
                max_step_over_median=r(float(step_m.max()) / max(med, 1e-9), 2))
    pb_med = np.median(db, axis=0)
    pb_ratio = sb / np.maximum(pb_med, 1e-9)
    ok = pb_med > 0.0005
    worst = sorted(((float(pb_ratio[i]), names[i]) for i in range(len(names)) if ok[i]), reverse=True)[:3]
    seam['worst_bones'] = [dict(bone=n, ratio=r(v, 2)) for v, n in worst]
    out['seam'] = seam if D['loop'] else dict(applies=False, note='one-shot clip; numbers below are for reference', **seam)
    # still tail (trailing samples whose 9-sample running mean motion is < 40 % of the median)
    run = np.convolve(step_b, np.ones(9) / 9, mode='same') if len(step_b) >= 9 else step_b
    still = run < 0.4 * medb
    tail = 0
    for v in still[::-1]:
        if not v:
            break
        tail += 1
    out['still_tail_samples'] = int(tail)
    # ---- feet
    allz = np.concatenate([D['foot'][k]['z'] for k in 'LR'])
    foot = dict(lowest_foot_vertex_cm=r(float(allz.min()) * 100, 2), contact_m=C.CONTACT_M, tracked_patch_m=C.CONTACT_PATCH_M)
    worst_px, worst_cm = 0.0, 0.0
    speeds, per = [], {}
    for k, lab in (('L', 'left'), ('R', 'right')):
        z = D['foot'][k]['z']
        V = D['foot'][k]['V']                                  # (N, nv, 3)
        floor_f = float(np.percentile(z, 5))                   # this foot's own planted level (robust to a single deep frame)
        g = z <= floor_f + C.CONTACT_M
        runs, i = [], 0
        while i < N:
            if g[i]:
                j = i
                while j + 1 < N and g[j + 1]:
                    j += 1
                if j - i + 1 >= 3:
                    runs.append((i, j))
                i = j + 1
            else:
                i += 1
        segs = []
        for (i, j) in runs:
            mid = (i + j) // 2
            T = np.nonzero(V[mid][:, 2] <= V[mid][:, 2].min() + C.CONTACT_PATCH_M)[0]
            c = V[:, T, :].mean(axis=1)                        # the contact patch of the middle frame, followed rigidly
            a_, b_ = mid, mid
            while a_ - 1 >= i and c[a_ - 1, 2] <= c[mid, 2] + C.CONTACT_M:
                a_ -= 1
            while b_ + 1 <= j and c[b_ + 1, 2] <= c[mid, 2] + C.CONTACT_M:
                b_ += 1
            if b_ - a_ + 1 < 3:
                continue
            P = c[a_:b_ + 1]
            dd = np.linalg.norm(P[:, None, :2] - P[None, :, :2], axis=2)
            d_cm = float(dd.max()) * 100
            px = {}
            for cn in C.CAM_ORDER:
                p = np.array([C.project_px(scene, cams[cn], q) for q in P])
                px[cn] = float(np.linalg.norm(p[:, None] - p[None, :], axis=2).max())
            dur = (b_ - a_) / C.FPS
            sp = float(np.linalg.norm(P[-1, :2] - P[0, :2]) / dur) if dur >= 0.25 else None
            if sp is not None:
                speeds.append(sp)
            segs.append(dict(first=int(a_), last=int(b_), drift_cm=r(d_cm, 2), drift_px={a: r(b, 1) for a, b in px.items()}, net_speed_m_s=r(sp, 3)))
            worst_px = max(worst_px, max(px.values()))
            worst_cm = max(worst_cm, d_cm)
        per[lab] = dict(planted_level_cm=r(floor_f * 100, 2), grounded_fraction=r(float(g.mean()), 3), min_height_cm=r(float(z.min()) * 100, 2),
                        max_height_cm=r(float(z.max()) * 100, 2), runs=segs)
    foot.update(per)
    foot['foot_drift_px'] = r(worst_px, 1)
    foot['foot_drift_cm'] = r(worst_cm, 2)
    foot['planted_speed_m_s'] = r(float(np.median(speeds)), 3) if speeds else None
    out['foot'] = foot
    # ---- secondary motion
    sec = [i for i, n in enumerate(names) if n == 'Head' or any(f in n for f in ('HandIndex', 'HandMiddle', 'HandRing', 'HandPinky', 'HandThumb'))]
    Rb = D['raw']
    hips_raw = Rb[:, hi, :]
    # articulation: finger bones in their Hand bone's frame, the Head in the Spine2 frame (so arm swing and trunk motion drop out)
    Mf = {n: D['raw_mats'][:, k] for k, n in enumerate(FRAME_BONES)}
    loc = []
    for i in sec:
        n = names[i]
        par = 'Spine2' if n == 'Head' else ('LeftHand' if n.startswith('Left') else 'RightHand')
        P = np.concatenate([Rb[:, i, :], np.ones((N, 1))], axis=1)[:, :, None]
        loc.append((np.linalg.inv(Mf[par]) @ P)[:, :3, 0])
    loc = np.array(loc).transpose(1, 0, 2)                                    # (N, S, 3)
    sp = np.linalg.norm(np.diff(loc, axis=0), axis=2)                         # (N-1, S) m per sample
    spw = np.linalg.norm(np.diff(Rb[:, sec, :], axis=0), axis=2)
    hs = np.linalg.norm(np.diff(hips_raw, axis=0), axis=1)
    head_i = [k for k, i in enumerate(sec) if names[i] == 'Head']
    sec_mean = float(sp[:, head_i].mean()) + float(np.delete(sp, head_i, axis=1).mean())    # head + fingers, each group's mean
    hips_mean = float(hs.mean())
    out['secondary'] = dict(ratio=r(sec_mean / max(hips_mean, HIPS_FLOOR_M), 3), head_in_chest_mm_per_sample=r(float(sp[:, head_i].mean()) * 1000, 3),
                            fingers_in_hand_mm_per_sample=r(float(np.delete(sp, head_i, axis=1).mean()) * 1000, 3),
                            hips_mm_per_sample=r(hips_mean * 1000, 3), world_ratio=r(float(spw.mean()) / max(hips_mean, HIPS_FLOOR_M), 3),
                            travel_m=r(float(np.linalg.norm(hips_raw[:, :2] - hips_raw[0, :2], axis=1).max()), 3), bones=len(sec))
    return out


base_loop = False


def main():
    global base_loop
    a = parse()
    subs = []
    for s in a.subject:
        lab, _, spec = s.partition('=')
        subs.append((lab, spec))
    base = C.Base(a.base)
    sc = base.scene
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = C.RES[0], C.RES[1], 100
    cams = {n: C.make_camera(sc, n) for n in C.CAM_ORDER}
    bpy.context.view_layer.update()
    base_loop = C.clip_is_loop(a.clip) if a.loop is None else a.loop
    res = dict(clip=a.clip, root=a.root, loop=base_loop, fps=C.FPS, subjects={})
    lines = []
    for lab, spec in subs:
        act, info = base.import_action(spec)
        base.play(act)
        m = measure(base, act, a.clip, a.root, cams, sc)
        if a.include_source:
            m['source'] = spec
            m['source_scale_ratio'] = r(info['source_scale_ratio'], 4)
        res['subjects'][lab] = m
        seam = ('%.2f' % m['seam']['mesh_ratio']) if base_loop else 'n/a'
        lines.append('AB_MEASURE %s %s seam %s foot_drift_px %.1f secondary %.2f' % (a.clip, lab, seam, m['foot']['foot_drift_px'], m['secondary']['ratio']))
        base.arm.animation_data_clear()
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, 'measure.json'), 'w') as f:
        json.dump(res, f, indent=1)
    for ln in lines:
        print(ln, flush=True)


if __name__ == '__main__':
    main()
