# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
# Scripted Blender pass on a raw video2rig fit of the Brute (ALIGNED rig .blend from import_motion.py): a fit is a base, never a
# deliverable (boss-fight-blueprint, Veyr lessons). Biped port of the dragon's refine/move/refine_move.py + lib_anim.py.
#
#   Blender -b --factory-startup -P tools/brute/v2r/refine_brute.py -- <fit.blend> [options]
#     --loop                 close the loop: end on the best-matching frame within --loop-win s of the end, offset-blend the last N
#                            frames so the end pose equals frame 0 (velocities stay continuous); N auto 12-24 (--xfade N to force)
#     --return-to-stance     one-shot: blend the end back onto frame 0 (the start-picture stance) over --return-frames (24-36, def 30)
#     --keep-travel          with --return-to-stance: leave the Hips' horizontal position alone (moves that travel)
#     --trim THR             trim the still tail: trailing samples whose 9-sample mean rotation step < THR x median (default 0.4;
#                            --trim 0 turns it off); never below half the clip
#     --no-plant             skip the foot plant (IK bake while a foot is grounded) and the toe clamp
#     --floor Z              floor height in the fit scene (default 0.0: model.blend has the stance's soles on z=0)
#     --max-lift M           the toe clamp lifts a foot by IK at most M metres (default 0.05); a deeper penetration means the whole
#                            body sits low (a floor / root mismatch, not a toe problem): it is capped and reported, never folded away
#     --spike-k K --spike-min-deg D   single-frame spike test: deviation from the neighbours' midpoint > K x the bone's median
#                            (default 4.0) and >= D deg (default 3), direction reverses, AND the in/out steps are > --spike-iso x
#                            (default 3) the steps around them (isolated jitter; a fast extreme such as a punch snap is never touched)
#     --action NAME --clip NAME --out PATH.blend   (defaults: active action; clip = action name; <fit>_refined.blend beside input)
#     --stance-rig rig.json  the aligned rig.json whose start_pose is the start-picture stance (overlap check)
# Writes <out>.blend and <out>.json; prints
#   REFINE_GATE <clip> seam x.xx foot_drift_mm X toe_min_mm X peakhand_L f peakhand_R f
#   seam  = rotation step across the loop wrap / median step (loop: last DISTINCT frame -> frame 0, the end frame equals frame 0 as in
#           assemble_motion; one-shot: last frame -> frame 0, i.e. how far the end is from the start stance)
#   foot_drift_mm = worst horizontal slide vs that plant's mean, after the plant: toe joint over every planted sample, ankle over the
#           heel-down samples (with the heel up the ankle legitimately swings around the ball)
#   toe_min_mm = lowest toe-region vertex over the clip, after the clamp (floor = 0)
#   peakhand_L/R = sample index of peak hand speed after refinement (seconds and 30 fps frame in the JSON)
# Arms/hands are only ever touched on detected single-frame spikes and inside the loop/return blend window; the JSON proves it.
# The input .blend is never written. Works on the fit's own key grid (no resampling: export_clip.py does the one 30 fps resample).
import argparse
import json
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import v2r_rig as R  # noqa: E402
import anim_lib as L  # noqa: E402  (tools/brute/anim_lib.py: FK, 2-bone leg IK, plant segmentation)

SIDES = ('Left', 'Right')
LEG = ('UpLeg', 'Leg', 'Foot', 'ToeBase')
ARM = ('Shoulder', 'Arm', 'ForeArm', 'Hand')
STANCE_RIG = '/Users/midir/hulk/Local/video2rig/brute-aligned/rig/rig.json'


def parse():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    ap = argparse.ArgumentParser(prog='refine_brute.py')
    ap.add_argument('blend')
    ap.add_argument('--loop', action='store_true')
    ap.add_argument('--return-to-stance', action='store_true')
    ap.add_argument('--keep-travel', action='store_true')
    ap.add_argument('--trim', type=float, default=0.4)
    ap.add_argument('--no-plant', action='store_true')
    ap.add_argument('--floor', type=float, default=0.0)
    ap.add_argument('--max-lift', type=float, default=0.05)
    ap.add_argument('--loop-win', type=float, default=2.0)
    ap.add_argument('--xfade', type=int, default=0)
    ap.add_argument('--return-frames', type=int, default=30)
    ap.add_argument('--spike-k', type=float, default=4.0)
    ap.add_argument('--spike-min-deg', type=float, default=3.0)
    ap.add_argument('--spike-iso', type=float, default=3.0)
    ap.add_argument('--action', default='')
    ap.add_argument('--clip', default='')
    ap.add_argument('--out', default='')
    ap.add_argument('--stance-rig', default=STANCE_RIG)
    a = ap.parse_args(argv)
    if a.loop and a.return_to_stance:
        ap.error('--loop and --return-to-stance exclude each other')
    return a


# ------------------------------------------------------------------ small math
def qang(a, b):
    return 2.0 * math.acos(min(1.0, abs(float(np.dot(a, b)))))


def fix_hemi(q):
    q = q / np.linalg.norm(q, axis=1, keepdims=True)
    for i in range(1, len(q)):
        if np.dot(q[i], q[i - 1]) < 0:
            q[i] = -q[i]
    return q


def nlerp(a, b, w):
    b = b if np.dot(a, b) >= 0 else -b
    o = (1 - w) * a + w * b
    return o / np.linalg.norm(o)


def sstep(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def gauss1d(v, sig=1.5, hw=4):
    g = np.exp(-.5 * (np.arange(-hw, hw + 1) / sig) ** 2); g /= g.sum()
    return np.convolve(np.pad(v, hw, mode='edge'), g, mode='valid')


def r3(x):
    return None if x is None else round(float(x), 3)


# ------------------------------------------------------------------ channels on the key grid
def read_channels(act, grid):
    ch = {}
    for fc in R.action_fcurves(act):
        p = fc.data_path
        if not p.startswith('pose.bones["'):
            continue
        b = p.split('"')[1]; prop = p.rsplit('.', 1)[1]
        kind = {'rotation_quaternion': 'q', 'location': 'l'}.get(prop)
        if kind is None:
            continue
        d = ch.setdefault(b, {})
        if kind not in d:
            d[kind] = np.zeros((len(grid), 4 if kind == 'q' else 3))
        d[kind][:, fc.array_index] = [fc.evaluate(x) for x in grid]
    for d in ch.values():
        if 'q' in d:
            d['q'] = fix_hemi(d['q'])
    return ch


def write_channels(arm, act, ch, grid):
    """replace every key of every channel in ch with one linear key per grid point; creates missing F-curves"""
    have = {(fc.data_path, fc.array_index): fc for fc in R.action_fcurves(act)}
    for b, d in ch.items():
        pb = arm.pose.bones[b]; pb.rotation_mode = 'QUATERNION'
        for kind, prop in (('q', 'rotation_quaternion'), ('l', 'location')):
            if kind in d and ('pose.bones["%s"].%s' % (b, prop), 0) not in have:
                pb.keyframe_insert(prop, frame=grid[0])
    have = {(fc.data_path, fc.array_index): fc for fc in R.action_fcurves(act)}
    G = np.asarray(grid, dtype=np.float64)
    for b, d in ch.items():
        for kind, prop, n in (('q', 'rotation_quaternion', 4), ('l', 'location', 3)):
            if kind not in d:
                continue
            for i in range(n):
                fc = have[('pose.bones["%s"].%s' % (b, prop), i)]
                fc.keyframe_points.clear(); fc.keyframe_points.add(len(G))
                co = np.empty(2 * len(G)); co[0::2] = G; co[1::2] = d[kind][:len(G), i]
                fc.keyframe_points.foreach_set('co', co)
                for kp in fc.keyframe_points:
                    kp.interpolation = 'LINEAR'
                fc.update()


def steps(ch, n, bones):
    """per-step summed rotation (rad) over bones, length n-1"""
    s = np.zeros(max(0, n - 1))
    for b in bones:
        q = ch[b]['q']
        s += np.array([qang(q[i], q[i + 1]) for i in range(n - 1)])
    return s


def pose_dist(ch, i, j, bones):
    return float(sum(qang(ch[b]['q'][i], ch[b]['q'][j]) for b in bones))


def apply_plant(frames, tg, frot):
    """anim_lib.apply_feet with a per-frame foot world rotation (None = keep the take's)"""
    out = []
    for i, (w, rh) in enumerate(frames):
        over = {}
        for s in SIDES:
            t = tg[s][i]
            if t is None:
                continue
            fr_ = frot[s][i] if frot and frot[s][i] is not None else w[s + 'Foot']
            over.update(L.leg_ik(L.rebuild(w, over), rh, s, t, foot_rot=fr_))
        out.append((L.rebuild(w, over) if over else w, rh))
    return out


def smooth_lift(need, cyclic):
    """max-filter (+-2) then Gaussian, never below the need; cyclic = over the distinct samples of a closed loop (last = first)"""
    n = len(need)
    if cyclic and n > 3:
        m = n - 1
        v = need[:m]
        mx = np.array([max(v[(i + o) % m] for o in range(-2, 3)) for i in range(m)])
        g = np.exp(-.5 * (np.arange(-4, 5) / 1.5) ** 2); g /= g.sum()
        sm = np.array([sum(g[k] * mx[(i + k - 4) % m] for k in range(9)) for i in range(m)])
        out = np.maximum(sm, v)
        return np.append(out, out[0])
    mx = np.array([need[max(0, i - 2):i + 3].max() for i in range(n)])
    return np.maximum(gauss1d(mx, 1.5, 4), need)


# ------------------------------------------------------------------ main
def main():
    a = parse()
    src = os.path.abspath(a.blend)
    out_blend = os.path.abspath(a.out) if a.out else os.path.splitext(src)[0] + '_refined.blend'
    out_json = os.path.splitext(out_blend)[0] + '.json'
    assert out_blend != src, 'refusing to overwrite the input'
    bpy.ops.wm.open_mainfile(filepath=src, load_ui=False)
    sc = bpy.context.scene
    arms = [o for o in sc.objects if o.type == 'ARMATURE']
    arm = next((o for o in arms if o.animation_data and o.animation_data.action), arms[0])
    act = bpy.data.actions[a.action] if a.action else arm.animation_data.action
    R.assign_action(arm, act)
    mesh = next(o for o in sc.objects if o.type == 'MESH' and any(m.type == 'ARMATURE' and m.object == arm for m in o.modifiers))
    clip = a.clip or act.name
    fps = sc.render.fps / sc.render.fps_base
    xs = sorted({round(kp.co.x, 5) for fc in R.action_fcurves(act) for kp in fc.keyframe_points})
    dx = np.diff(xs)
    if len(xs) > 2 and dx.std() < 1e-3 * dx.mean():
        grid0 = list(xs); spacing = float(dx.mean())
    else:  # irregular keys: integer frames
        grid0 = list(np.arange(math.ceil(xs[0]), math.floor(xs[-1]) + 1, 1.0)); spacing = 1.0
    sr = fps / spacing                       # samples per second
    N0 = len(grid0)
    REP = dict(source=src, clip=clip, action=act.name, scene_fps=fps, grid=dict(first=grid0[0], spacing_frames=spacing, samples=N0,
               sample_rate=sr, seconds=(N0 - 1) / sr), options=vars(a))
    print('REFINE %s: %d samples, %.3f s, sample rate %.3f /s (keys every %.4f frames at %g fps)' % (clip, N0, (N0 - 1) / sr, sr, spacing, fps))
    ch0 = read_channels(act, grid0)
    rotb = sorted(b for b in ch0 if 'q' in ch0[b])
    armb = [s + x for s in SIDES for x in ARM if s + x in ch0]
    legb = [s + x for s in SIDES for x in LEG]
    root = L.ROOT
    W = arm.matrix_world.copy()
    sc_w = W.to_scale().x

    names = {g.index: g.name for g in mesh.vertex_groups}
    dom = np.array([names[max(v.groups, key=lambda g: g.weight).group] if len(v.groups) else '' for v in mesh.data.vertices])
    toe_idx = {s: np.where(dom == s + 'ToeBase')[0] for s in SIDES}
    foot_idx = {s: np.where((dom == s + 'Foot') | (dom == s + 'ToeBase'))[0] for s in SIDES}

    def eval_frames(grid):
        L.bind(arm, act)
        return [L.sample(x) for x in grid]

    def hand_peaks(frames):
        out = {}
        for s in SIDES:
            P = np.array([list(L.fk(w, rh)[s + 'Hand']) for w, rh in frames])
            v = np.zeros(len(P))
            v[1:-1] = np.linalg.norm(P[2:] - P[:-2], axis=1) / 2 * sr
            i = int(v.argmax())
            out[s] = dict(sample=i, seconds=round(i / sr, 3), frame30=round(i / sr * 30, 1), speed_m_s=round(float(v[i]), 3))
        return out

    def foot_heights(grid):
        """per sample: min z of toe-region and whole-foot vertices per side (fit-scene metres)"""
        res = {s: dict(toe=np.zeros(len(grid)), foot=np.zeros(len(grid))) for s in SIDES}
        for i, x in enumerate(grid):
            R.set_frame(x)
            V = R.mesh_world(mesh)
            for s in SIDES:
                res[s]['toe'][i] = V[toe_idx[s], 2].min()
                res[s]['foot'][i] = V[foot_idx[s], 2].min()
        return res

    # ---------- before: stance overlap, hand peaks, toe heights (raw fit)
    st = json.load(open(a.stance_rig))['start_pose'] if os.path.exists(a.stance_rig) else None
    overlap = None
    if st:
        R.set_frame(grid0[0]); V0 = R.mesh_world(mesh)
        q0 = {pb.name: pb.matrix_basis.to_quaternion() for pb in arm.pose.bones}
        h0 = arm.pose.bones[root].matrix_basis.to_translation()
        arm.animation_data.action = None
        for pb in arm.pose.bones:
            pb.matrix_basis = Matrix(st[pb.name])
        bpy.context.view_layer.update()
        Vs = R.mesh_world(mesh)
        angs = {n: math.degrees(q0[n].rotation_difference(Matrix(st[n]).to_quaternion()).angle) for n in st}
        dv = np.linalg.norm(V0 - Vs, axis=1) * 1000
        wn = max(angs, key=lambda n: angs[n] if angs[n] <= 180 else 360 - angs[n])
        overlap = dict(mesh_mm_mean=r3(dv.mean()), mesh_mm_p95=r3(np.percentile(dv, 95)), mesh_mm_max=r3(dv.max()),
                       bone_deg_max=r3(min(angs[wn], 360 - angs[wn])), bone_deg_max_name=wn,
                       hips_loc_mm=r3((h0 - Matrix(st[root]).to_translation()).length * sc_w * 1000))
        R.assign_action(arm, act)
    REP['frame0_vs_start_stance'] = overlap
    print('REFINE frame 0 vs start-picture stance', json.dumps(overlap))
    fr_raw = eval_frames(grid0)
    peaks_raw = hand_peaks(fr_raw)
    fh_raw = foot_heights(grid0)
    toe_raw = min(float(fh_raw[s]['toe'].min()) for s in SIDES)
    med0 = float(np.median(steps(ch0, N0, rotb)))
    REP['raw'] = dict(median_step_rad=r3(med0), pose_dist_last_vs_first_rad=r3(pose_dist(ch0, N0 - 1, 0, rotb)),
                      seam_ratio_last_to_first=r3(pose_dist(ch0, N0 - 1, 0, rotb) / med0), peak_hand=peaks_raw,
                      toe_min_mm=r3((toe_raw - a.floor) * 1000))

    # ---------- 1. trim the still tail
    spd = steps(ch0, N0, rotb)
    run = np.convolve(np.pad(spd, 4, mode='edge'), np.ones(9) / 9, mode='valid')
    N = N0
    trim_rep = dict(threshold=a.trim)
    if a.trim > 0:
        live = [i for i in range(len(run)) if run[i] >= a.trim * med0]
        still_start = (live[-1] + 1) if live else N0 - 1
        Nt = min(N0, still_start + 1)
        floor_n = max(int(0.5 * N0), int(round(1.0 * sr)))
        trim_rep.update(still_tail_start=int(still_start), limited=Nt < floor_n)
        N = max(Nt, min(N0, floor_n))
    trim_rep.update(kept=[0, N - 1], trimmed_samples=N0 - N, trimmed_seconds=r3((N0 - N) / sr))
    REP['trim'] = trim_rep
    ch = {b: {k: v[:N].copy() for k, v in d.items()} for b, d in ch0.items()}
    print('REFINE trim', json.dumps(trim_rep))

    # ---------- 2. single-frame spikes (per bone: out-and-back deviation from the neighbours' midpoint)
    spikes = {}
    G = np.exp(-.5 * (np.arange(-2, 3) / 1.0) ** 2); G /= G.sum()
    for b in rotb:
        q = ch[b]['q']
        touched = set()
        for _ in range(3):
            dev = np.zeros(N); rev = np.zeros(N, bool)
            for i in range(1, N - 1):
                mid = nlerp(q[i - 1], q[i + 1], 0.5)
                dev[i] = qang(q[i], mid)
                d1 = (Quaternion(q[i - 1]).inverted() @ Quaternion(q[i])).to_exponential_map()
                d2 = (Quaternion(q[i]).inverted() @ Quaternion(q[i + 1])).to_exponential_map()
                rev[i] = d1.length > 1e-9 and d2.length > 1e-9 and d1.normalized().dot(d2.normalized()) < 0
            med = float(np.median(dev[1:-1])) if N > 2 else 0.0
            thr = max(a.spike_k * med, math.radians(a.spike_min_deg))
            stp = [qang(q[i], q[i + 1]) for i in range(N - 1)]

            def isolated(i):   # the in/out steps dwarf the steps around them: a jitter frame, not a fast extreme (punch snap)
                around = max(stp[i - 2] if i >= 2 else 0.0, stp[i + 1] if i + 1 < N - 1 else 0.0)
                return min(stp[i - 1], stp[i]) > a.spike_iso * around
            sp = [i for i in range(1, N - 1) if dev[i] > thr and rev[i] and isolated(i)]
            if not sp:
                break
            for i in sp:
                q[i] = nlerp(q[i - 1], q[i + 1], 0.5); touched.add(i)
            qs = q.copy()
            for i in sp:
                for j in range(max(1, i - 1), min(N - 1, i + 2)):
                    acc = sum(g * qs[min(N - 1, max(0, j + o))] * (1 if np.dot(qs[min(N - 1, max(0, j + o))], qs[j]) >= 0 else -1)
                              for o, g in zip(range(-2, 3), G))
                    q[j] = acc / np.linalg.norm(acc); touched.add(j)
        ch[b]['q'] = fix_hemi(q)
        if touched:
            spikes[b] = sorted(int(i) for i in touched)
    REP['spikes'] = dict(bones=len(spikes), frames_touched=spikes, arm_bones_touched=[b for b in spikes if b in armb])
    print('REFINE spikes', json.dumps({b: len(v) for b, v in spikes.items()}))
    spike_frames_arm = {b: set(spikes.get(b, [])) for b in armb}

    # ---------- 3a. loop: best end frame + offset blend
    blend_win = set()
    if a.loop:
        win = int(round(a.loop_win * sr))
        lo = max(int(N * 0.5), N - 1 - win)

        def cost(Lx):
            c = 0.0
            for b in rotb:
                q = ch[b]['q']
                c += qang(q[Lx], q[0]) ** 2
                v_end = Quaternion(q[Lx - 1]).inverted() @ Quaternion(q[Lx]); v_beg = Quaternion(q[0]).inverted() @ Quaternion(q[1])
                c += 0.5 * v_end.rotation_difference(v_beg).angle ** 2
            if root in ch and 'l' in ch[root]:
                l_ = ch[root]['l']; c += float(np.sum((l_[Lx] - l_[0]) ** 2)) * 25
            return c
        costs = {Lx: cost(Lx) for Lx in range(lo, N)}
        Lend = min(costs, key=costs.get)
        offs = {b: (Quaternion(ch[b]['q'][Lend]).inverted() @ Quaternion(ch[b]['q'][0])) for b in rotb}
        for b in offs:
            if offs[b].w < 0:
                offs[b] = -offs[b]
        tot = sum(o.angle for o in offs.values())
        if a.xfade:
            nX = a.xfade; why = 'forced'
        else:  # smallest N in 12..24 whose blend adds at most half a median step per frame (smoothstep peak slope 1.5/N)
            nX = next((n for n in range(12, 25) if tot * 1.5 / n <= 0.5 * med0), 24); why = 'auto: added step <= 0.5 x median' if tot * 1.5 / nX <= 0.5 * med0 else 'auto: capped at 24'
        nX = min(nX, Lend)
        seam_before = pose_dist(ch, N - 1, 0, rotb) / med0
        for b in rotb:
            q = ch[b]['q']
            for j in range(Lend - nX, Lend + 1):
                s = sstep((j - (Lend - nX)) / nX)
                q[j] = np.array(q[j]) if s == 0 else np.array(Quaternion(q[j]) @ Quaternion().slerp(offs[b], s))
            ch[b]['q'] = fix_hemi(q)
        for b, d in ch.items():
            if 'l' in d:
                l0, lL = d['l'][0].copy(), d['l'][Lend].copy()
                for j in range(Lend - nX, Lend + 1):
                    d['l'][j] = d['l'][j] + sstep((j - (Lend - nX)) / nX) * (l0 - lL)
        N = Lend + 1
        for b in ch:
            for k in ch[b]:
                ch[b][k] = ch[b][k][:N]
        blend_win = set(range(Lend - nX, Lend + 1))
        REP['loop'] = dict(window_samples=win, end_sample=Lend, end_seconds=r3(Lend / sr), cost=r3(costs[Lend]), cost_at_last=r3(costs[max(costs)]),
                           xfade=nX, xfade_rule=why, offset_total_rad=r3(tot), seam_ratio_before=r3(seam_before))
        print('REFINE loop', json.dumps(REP['loop']))

    # ---------- 3b. one-shot: return to the frame-0 stance
    if a.return_to_stance:
        Wn = max(2, min(a.return_frames, N // 2))
        # combat timing: the blend never starts before the later hand-speed peak + 0.2 s (contact and follow-through survive)
        hp = max(peaks_raw[s_]['sample'] for s_ in SIDES if peaks_raw[s_]['sample'] < N)
        start_min = hp + int(round(0.2 * sr))
        limited = N - Wn < start_min
        if limited:
            Wn = max(2, N - start_min)
        before = pose_dist(ch, N - 1, 0, rotb)
        for b in rotb:
            q = ch[b]['q']
            for j in range(N - Wn, N):
                q[j] = nlerp(q[j], q[0], sstep((j - (N - Wn) + 1) / Wn))
            ch[b]['q'] = fix_hemi(q)
        Rr = arm.data.bones[root].matrix_local.to_3x3()      # root location keys are in the rest bone's axes; travel = armature x/y
        for b, d in ch.items():
            if 'l' not in d:
                continue
            for j in range(N - Wn, N):
                s = sstep((j - (N - Wn) + 1) / Wn)
                if a.keep_travel and b == root:
                    lj, l0 = Rr @ Vector(d['l'][j]), Rr @ Vector(d['l'][0])
                    t = Vector((lj.x, lj.y, (1 - s) * lj.z + s * l0.z))
                    d['l'][j] = list(Rr.inverted() @ t)
                else:
                    d['l'][j] = (1 - s) * d['l'][j] + s * d['l'][0]
        blend_win = set(range(N - Wn, N))
        REP['return'] = dict(frames=Wn, seconds=r3(Wn / sr), limited_by_hand_peak=limited, hand_peak_sample=hp, end_vs_start_rad_before=r3(before), end_vs_start_rad_after=r3(pose_dist(ch, N - 1, 0, rotb)))
        print('REFINE return', json.dumps(REP['return']))

    grid = grid0[:N]
    write_channels(arm, act, ch, grid)
    ch_pre = {b: {k: v.copy() for k, v in d.items()} for b, d in ch.items()}   # for the untouched-arms proof

    # ---------- 4. feet: plant while grounded (anim_lib segmentation + analytic 2-bone IK), cyclic-aware for loops
    frames = eval_frames(grid)
    feet_rep = {}
    groups = {}
    if not a.no_plant:
        for s in SIDES:
            _, segs = L.plant_targets(frames, s)
            gs = [[sg] for sg in segs]
            if a.loop and len(gs) >= 2 and segs[0][0] == 0 and segs[-1][1] == N - 1:
                gs = [gs[0] + gs[-1]] + gs[1:-1]
            groups[s] = gs

        def drift(frs):
            res = {}
            for s in SIDES:
                P = [L.fk(w, rh) for w, rh in frs]
                worst = dict(ankle=0.0, toe=0.0)
                for g in groups[s]:
                    idx = [i for a_, b_ in g for i in range(a_, b_ + 1)]
                    zmin = min(P[i][s + 'Foot'].z for i in idx)
                    down = [i for i in idx if P[i][s + 'Foot'].z - zmin < 0.01] or idx   # ankle counts while the heel is down
                    for key, bn, ii in (('ankle', s + 'Foot', down), ('toe', s + 'ToeBase', idx)):
                        pts = np.array([[P[i][bn].x, P[i][bn].y] for i in ii])
                        if len(pts):
                            worst[key] = max(worst[key], float(np.linalg.norm(pts - pts.mean(0), axis=1).max()) * 1000)
                res[s] = {k: r3(v) for k, v in worst.items()}
            return res
        d_before = drift(frames)
        # heel down: ankle pinned (xy) to the plant's mean and the foot held at the plant's flat rotation (mean, yaw-aligned), so ankle
        # and toe joint both stay put; heel up (ankle 0-2 cm over its lowest in the plant, smooth): the pivot moves to the ball, the toe
        # joint is pinned to its mean and the foot keeps the take's pitch/roll (yaw still pinned), the ankle following around the ball.
        # 3-sample blends in/out, like anim_lib.plant_targets
        tg, frot = {}, {}
        for s in SIDES:
            P = [L.fk(w, rh) for w, rh in frames]
            ank = [p[s + 'Foot'] for p in P]
            toe = [p[s + 'ToeBase'] for p in P]
            yaw = [math.atan2((toe[i] - ank[i]).y, (toe[i] - ank[i]).x) for i in range(N)]
            tgt, wts, fr_ = [None] * N, [0.0] * N, [None] * N
            for g in groups[s]:
                idx = [i for a_, b_ in g for i in range(a_, b_ + 1)]
                c = sum((ank[i] for i in idx), Vector()) / len(idx)
                zmin = min(ank[i].z for i in idx)
                yc = math.atan2(sum(math.sin(yaw[i]) for i in idx), sum(math.cos(yaw[i]) for i in idx))
                # flat-foot rotation of this plant: mean of the yaw-locked foot rotations over the heel-down samples
                flat = [i for i in idx if ank[i].z - zmin < 0.01] or idx
                qs = [Quaternion((0, 0, 1), L.wrap(yc - yaw[i])) @ frames[i][0][s + 'Foot'] for i in flat]
                acc = np.zeros(4)   # (mathutils' 4-D Vector.normalized() only normalizes x, y, z: use numpy)
                for q in qs:
                    acc += np.array(q) * (1 if q.dot(qs[0]) >= 0 else -1)
                qflat = Quaternion(acc / np.linalg.norm(acc))
                # the plant that holds frame 0 (and, returning to the stance, the plant that holds the last frame) is anchored on that
                # frame instead of the mean, so frame 0 stays the start-picture stance the game blends from
                a0 = 0 if 0 in idx else (N - 1 if (a.return_to_stance and N - 1 in idx) else None)
                if a0 is not None:
                    c, yc, qflat = ank[a0].copy(), yaw[a0], frames[a0][0][s + 'Foot'].copy()
                # the ball pin is where the flat foot puts the toe joint (rigid offset in the foot's frame), so the heel-down and heel-up
                # phases share one contact point
                i0 = idx[0]
                ct = c + qflat @ (frames[i0][0][s + 'Foot'].inverted() @ (toe[i0] - ank[i0]))
                for a_, b_ in g:
                    for i in range(max(0, a_ - 3), min(N, b_ + 4)):
                        w = 1.0 if a_ <= i <= b_ else L.smooth(1 - (a_ - i) / 4) if i < a_ else L.smooth(1 - (i - b_) / 4)
                        if w > wts[i]:
                            rz = Quaternion((0, 0, 1), L.wrap(yc - yaw[i]) * w)
                            u = L.smooth((ank[i].z - zmin) / 0.02)
                            qf = frames[i][0][s + 'Foot']
                            qpl = qflat.slerp(Quaternion((0, 0, 1), L.wrap(yc - yaw[i])) @ qf, u)   # heel down: flat; heel up: take's roll
                            qn = qf.slerp(qpl, w)
                            v = qpl @ (qf.inverted() @ (toe[i] - ank[i]))
                            pin = Vector((ct.x - v.x, ct.y - v.y, c.z))   # toe joint on the contact point; heel down => pin == c
                            wts[i] = w; tgt[i] = Vector((ank[i].x + (pin.x - ank[i].x) * w, ank[i].y + (pin.y - ank[i].y) * w, ank[i].z))
                            fr_[i] = qn
            tg[s], frot[s] = tgt, fr_
        frames = apply_plant(frames, tg, frot)
        reach = {}
        for s in SIDES:   # IK reach: samples where the solved ankle misses its pin by > 5 mm (target beyond the straight leg)
            miss = [i for i in range(N) if tg[s][i] is not None and
                    (Vector(L.fk(*frames[i])[s + 'Foot'][:2]) - Vector(tg[s][i][:2])).length > 0.005]
            reach[s] = dict(samples_missing_pin=len(miss), first=miss[:8])
        d_after = drift(frames)
        feet_rep = dict(plants={s: [[list(sg) for sg in g] for g in groups[s]] for s in SIDES},
                        planted_samples={s: int(sum(b_ - a_ + 1 for g in groups[s] for a_, b_ in g)) for s in SIDES},
                        drift_mm_before=d_before, drift_mm_after=d_after, ik_reach=reach)

        def to_basis(frs):
            Wqi, tR, PAR = L.S['Wqi'], L.S['tR'], L.S['PAR']
            for bn in legb:
                q = np.zeros((N, 4))
                for i, (w, rh) in enumerate(frs):
                    aq = Wqi @ w[bn]; p = PAR[bn]
                    qq = (((Wqi @ w[p]) @ (tR[p].inverted() @ tR[bn])).inverted() @ aq) if p else tR[bn].inverted() @ aq
                    q[i] = list(qq)
                ch.setdefault(bn, {})['q'] = fix_hemi(q)
        to_basis(frames)
        write_channels(arm, act, {b: ch[b] for b in legb}, grid)
        print('REFINE feet', json.dumps(feet_rep['drift_mm_before']), '->', json.dumps(d_after))

        # ---------- 5. toes above the floor: lift the ankle (IK, foot rotation kept) where any foot vertex is under the floor
        fh = foot_heights(grid)
        lifts = {}
        for s in SIDES:
            need = np.maximum(0.0, a.floor - fh[s]['foot'])
            if need.max() > a.max_lift:
                feet_rep.setdefault('floor_mismatch', {})[s] = dict(deepest_mm=r3(need.max() * 1000), samples_over_cap=int((need > a.max_lift).sum()),
                                                                     note='penetration deeper than --max-lift: capped; check --floor / the root height')
                print('REFINE WARNING %s foot %.0f mm under the floor (> --max-lift %.0f mm): lift capped' % (s, need.max() * 1000, a.max_lift * 1000))
                need = np.minimum(need, a.max_lift)
            lifts[s] = smooth_lift(need, a.loop)
        if any(l_.max() > 1e-6 for l_ in lifts.values()):
            frames = eval_frames(grid)
            tg = {}
            for s in SIDES:
                tg[s] = [None] * N
                for i, (w, rh) in enumerate(frames):
                    if lifts[s][i] > 1e-6:
                        p = L.fk(w, rh)[s + 'Foot']
                        tg[s][i] = Vector((p.x, p.y, p.z + lifts[s][i]))
            frames = apply_plant(frames, tg, None)
            to_basis(frames)
            write_channels(arm, act, {b: ch[b] for b in legb}, grid)
        if a.loop:   # the leg edits are built cyclic; make the closed end exact and report what that changed
            res_ = max(math.degrees(qang(ch[b]['q'][N - 1], ch[b]['q'][0])) for b in legb)
            for b in legb:
                ch[b]['q'][N - 1] = ch[b]['q'][0]
            write_channels(arm, act, {b: ch[b] for b in legb}, grid)
            feet_rep['loop_leg_end_residual_deg'] = r3(res_)
        feet_rep['toe_clamp'] = {s: dict(max_lift_mm=r3(lifts[s].max() * 1000), samples_lifted=int((lifts[s] > 1e-6).sum())) for s in SIDES}
    REP['feet'] = feet_rep

    # ---------- after
    fr_fin = eval_frames(grid)
    peaks = hand_peaks(fr_fin)
    fh_fin = foot_heights(grid)
    toe_min = min(float(fh_fin[s]['toe'].min()) for s in SIDES)
    foot_min = min(float(fh_fin[s]['foot'].min()) for s in SIDES)
    chf = read_channels(act, grid)
    medf = float(np.median(steps(chf, N, rotb)))
    dup = pose_dist(chf, N - 1, 0, rotb) < 1e-3
    if a.loop:
        seam = pose_dist(chf, N - 2, 0, rotb) / medf
        seam_def = 'loop: last distinct frame (N-2) -> frame 0 / median step; end frame equals frame 0: %s' % dup
    else:
        seam = pose_dist(chf, N - 1, 0, rotb) / medf
        seam_def = 'one-shot: last frame -> frame 0 / median step'
    # untouched arms: every arm-bone rotation equals the pre-plant channels (plant touches legs only); and the pre-plant channels equal
    # the raw fit outside spike frames and the loop/return blend window
    arm_vs_pre = max((math.degrees(qang(chf[b]['q'][i], ch_pre[b]['q'][i])) for b in armb for i in range(N)), default=0.0)
    arm_vs_raw = max((math.degrees(qang(ch_pre[b]['q'][i], ch0[b]['q'][i])) for b in armb for i in range(N)
                      if i not in blend_win and i not in spike_frames_arm[b]), default=0.0)
    head_dev = {b: r3(max(math.degrees(qang(chf[b]['q'][i], chf[b]['q'][0])) for i in range(N))) for b in ('Neck', 'Head') if b in chf}
    if not a.no_plant:
        feet_rep['drift_mm_final'] = drift(fr_fin)
    drift_after = max((v for s in SIDES for v in feet_rep.get('drift_mm_final', {}).get(s, {}).values()), default=float('nan'))
    if st:
        R.set_frame(grid[0]); V0f = R.mesh_world(mesh)
        dvf = np.linalg.norm(V0f - Vs, axis=1) * 1000
        REP['frame0_vs_start_stance_after'] = dict(mesh_mm_mean=r3(dvf.mean()), mesh_mm_p95=r3(np.percentile(dvf, 95)), mesh_mm_max=r3(dvf.max()))
        print('REFINE refined frame 0 vs start-picture stance', json.dumps(REP['frame0_vs_start_stance_after']))
    REP['final'] = dict(samples=N, seconds=r3((N - 1) / sr), key_first=grid[0], key_last=grid[-1], seam_ratio=r3(seam), seam_definition=seam_def,
                        median_step_rad=r3(medf), foot_drift_mm=r3(drift_after), toe_min_mm=r3((toe_min - a.floor) * 1000),
                        toe_min_mm_before=REP['raw']['toe_min_mm'], foot_sole_min_mm=r3((foot_min - a.floor) * 1000),
                        peak_hand=peaks, peak_hand_raw=peaks_raw,
                        arm_rotation_change_deg_by_plant=r3(arm_vs_pre), arm_rotation_change_deg_outside_spikes_and_blend=r3(arm_vs_raw),
                        neck_head_max_deg_from_frame0=head_dev)
    sc.frame_start, sc.frame_end = int(math.floor(grid[0])), int(math.ceil(grid[-1]))
    act.name = act.name if act.name.endswith('_refined') else act.name + '_refined'
    REP['final']['action'] = act.name
    json.dump(REP, open(out_json, 'w'), indent=1)
    bpy.ops.wm.save_as_mainfile(filepath=out_blend)
    print('REFINE final', json.dumps({k: v for k, v in REP['final'].items() if k not in ('peak_hand_raw',)}))
    print('REFINE saved', out_blend, out_json)
    print('REFINE_GATE %s seam %.2f foot_drift_mm %s toe_min_mm %.1f peakhand_L %d peakhand_R %d' % (
        clip, seam, ('%.1f' % drift_after) if drift_after == drift_after else 'n/a', (toe_min - a.floor) * 1000,
        peaks['Left']['sample'], peaks['Right']['sample']), flush=True)


if __name__ == '__main__':
    main()
