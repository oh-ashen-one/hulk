# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
# Measures the per-act clip timing the game needs (ABruteCharacter::ActClip From / To / Rate / Hit and the AnimateClips segment
# times) from the clips themselves and writes unreal/WebHomage/Config/BruteClipTiming.json, which the game reads at load
# (BruteCharacter.cpp LoadClipTiming; an absent file or key keeps the C++ constants). Blueprint principle 1: the numbers move
# with the animation, nobody types them.
#
#   Blender -b --factory-startup -P tools/brute/v2r/measure_timing.py -- <brute.glb|brute_anim.fbx> [options]
#   python3 tools/brute/v2r/measure_timing.py --telemetry <tel.json> [options]        (re-run the analysis on a --dump, no Blender)
#   options:
#     --out PATH       JSON to write (default unreal/WebHomage/Config/BruteClipTiming.json). '-' = do not write.
#     --meta PATH      clips_meta.json of the assembled set (default: beside the glb). Its 'src' tells new clips from old.
#     --all            write every clip it can measure (default: only clips whose src is a video2rig export, '*v2r*', so the
#                      old clips of a keep-the-best mix keep today's constants exactly; with no meta file: every clip)
#     --clips A,B      write exactly these clips (assemble_motion CLIPS names)
#     --dump PATH      also save the sampled bone telemetry (input for --telemetry)
#     --check-today S  print the comparison with today's C++ constants and exit 3 if any value differs by more than S seconds
#
# Semantics (the SAME meaning as today's constants; times are seconds from the clip's first frame, 30 fps):
#   hit   punches / slap / uppercut / throw: peak speed of the striking hand (hand relative to the hips' ground position, as the
#         game pins the hips); clap: first frame the palms meet (hand gap within 2 cm of its minimum); smash (and the Land HIT):
#         first frame after the peak speed that the lower hand is within 2 cm of its lowest point (fists in the street).
#   from  hit - today's wind-up lead (Hit - From of today's constants), clamped at 0: the contact lands at the same game-time
#         as today (ActHitAt = (Hit - From) / Rate is gameplay: how fast a press connects). Throw starts at 0 (the throw take
#         starts on the carry pose it is cross-faded from).
#   to    hit + today's recovery span (To - Hit), then clamped by what the clip measures: never past the clip end, never into
#         the next motion bout (a hand faster than 40 % of the strike peak after the follow-through: the generated tails), and
#         never before the follow-through ends (striking hand under 25 % of its peak). Today's To is a chosen hold after
#         contact (slap arm lowering, smash fists held in the street, uppercut held overhead), not a settle event: the
#         measured settle times (striking hand under 10 % of peak) are reported in 'measured' for reference.
#   rate  today's, unless the clip's length differs from today's clip by more than 20 % (a video2rig take): then today's GAME-TIME
#         windows are kept exactly and only the playback rate changes (director rule 2026-10-29, game_window()): Rate =
#         min(today's x length ratio, 1.6), lowered until From = Hit - lead_game x Rate >= 0 and To = Hit + recovery_game x Rate
#         <= the clip end, never below 1.0 (then clamped and flagged). lead_game / recovery_game = today's (Hit-From)/Rate and
#         (To-Hit)/Rate. No bout / follow-through clamp on those (annotated only). Throw too (its old take started at 0 on the
#         carry pose; the v2r take starts in the stance). `--selftest-rule` checks the rule on synthetic numbers.
#   Grab  hit = to = arms fully overhead (both hands above the head by 85 % of the clip's maximum); from = to - today's span.
#   Carry from = Grab's overhead time, to = the last frame (the settled overhead hold the game freezes on; rate 0).
#   Jump  JChargeLo = the hips' highest point before the crouch; JChargeHi = deepest crouch (hips over the lowest foot) before
#         the launch; JLaunch = first frame after it with the hips rising faster than 0.5 m/s; JApex = hips highest after the
#         launch (the old analyze_clips.py markers).
#   Wall  WAttachImpact = first frame both fists are within 8 cm of their highest point above the head (analyze_clips.py);
#         AttachStart = impact - 0.5 s (analyze_clips 'reach'); WClimbImpact2 = the next fist-height peak after the first
#         impact (the second fist going in); WClimbLo / WClimbHi = those two impacts with today's offsets (0.55 = 0.70 - 0.15,
#         1.85 = 1.50 + 0.35). 2026-10-29: each wall clip also writes its own times (WAttachImpact2 / WAttachEnd on WallAttach,
#         WClimbImpact1 on WallClimb): the game used WClimbHi as the attach clip's end and both impacts on both timelines, correct
#         only while WallClimb reused the WallAttach file. A WallClimb shorter than half of today's 5 s clip is a single climb
#         cycle (the video2rig loop): WClimbLo/Hi = the whole clip, WClimbImpact1/2 = the left / right hand's height peak.
#   Land  LandStart = first frame the lowest foot is back on the floor (within 3 cm of its settled height).
#   StopLunge  LungeStart = coil start (the hips' last high point before the final descent) - 0.567 s: the offset is calibrated
#         on brute_v5 (coil 1.567 s, today's start 1.0 s) because no event marks today's mid-stride start; flagged 'cal'.
import sys, os, json, math, re
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
DEFAULT_OUT = os.path.join(REPO, 'unreal', 'WebHomage', 'Config', 'BruteClipTiming.json')
FPS = 30.0
SKIP = 2            # first frames of the generated takes are bind-like / settling (assemble_motion freezes 0-1 on frame 2)
BONES = ('Hips', 'Head', 'LeftHand', 'RightHand', 'LeftFoot', 'RightFoot', 'LeftToeBase', 'RightToeBase')

# ---- today's constants (BruteCharacter.cpp ActClip + BruteCharacter.h segment members + the literals in AnimateClips),
# and today's clip lengths (brute_v5 clips_meta.json): the baseline for the rate rule and the --check-today table
TODAY_ACT = {   # key: (clip, From, To, Rate, Hit)
    'PunchR': ('PunchR', 0.45, 1.40, 1.6, 1.0), 'PunchL': ('PunchL', 0.45, 1.40, 1.6, 1.0),
    'Slap': ('Slap', 0.30, 1.70, 1.5, 0.90), 'Clap': ('Clap', 0.10, 1.30, 1.3, 0.70),
    'Smash': ('Smash', 0.40, 2.00, 1.4, 1.17), 'Uppercut': ('Uppercut', 0.15, 1.40, 1.4, 0.60),
    'Grab': ('Lift', 0.60, 2.40, 2.0, 2.40), 'Carry': ('Lift', 2.40, 2.95, 0.0, 0.0),
    'Throw': ('Throw', 0.00, 1.46, 1.25, 0.45)}
TODAY_SEG = {'JChargeLo': 0.17, 'JChargeHi': 2.45, 'JLaunch': 2.55, 'JApex': 3.17, 'AttachStart': 0.2, 'WAttachImpact': 0.7,
             'WClimbImpact2': 1.5, 'WClimbLo': 0.55, 'WClimbHi': 1.85, 'LandStart': 0.35, 'LungeStart': 1.0,
             'WAttachImpact2': 1.5, 'WAttachEnd': 1.85, 'WClimbImpact1': 0.7}
TODAY_LEN = {'PunchL': 1.533, 'PunchR': 1.533, 'Slap': 2.467, 'Clap': 1.567, 'Smash': 2.967, 'Lift': 3.0, 'Throw': 1.467,
             'Uppercut': 2.467, 'Jump': 5.0, 'WallAttach': 5.0, 'WallClimb': 5.0, 'Land': 2.967, 'StopLunge': 2.833}
TODAY_HIT = {'PunchL': 1.0, 'PunchR': 1.0, 'Slap': 0.9, 'Clap': 0.7, 'Smash': 1.17, 'Uppercut': 0.6, 'Throw': 0.45, 'Land': 0.5}
LUNGE_CAL = 1.567 - 1.0      # brute_v5 StopLunge: coil start measured 1.567 s, today's segment start 1.0 s
CLIMB_LO_OFF = 0.70 - 0.55   # today's climb loop starts 0.15 s before the first fist impact ...
CLIMB_HI_OFF = 1.85 - 1.50   # ... and ends 0.35 s after the second
# act -> (clip, hit detector, striking hand or None = whichever hand peaks faster)
ACTS = {'PunchR': ('PunchR', 'peak', 'Right'), 'PunchL': ('PunchL', 'peak', 'Left'), 'Slap': ('Slap', 'peak', None),
        'Clap': ('Clap', 'gap', None), 'Smash': ('Smash', 'ground', None), 'Uppercut': ('Uppercut', 'peak', None),
        'Throw': ('Throw', 'peak', None)}
SEG_CLIP = {'JChargeLo': 'Jump', 'JChargeHi': 'Jump', 'JLaunch': 'Jump', 'JApex': 'Jump', 'AttachStart': 'WallAttach',
            'WAttachImpact': 'WallAttach', 'WClimbImpact2': 'WallClimb', 'WClimbLo': 'WallClimb', 'WClimbHi': 'WallClimb',
            'LandStart': 'Land', 'LungeStart': 'StopLunge',
            'WAttachImpact2': 'WallAttach', 'WAttachEnd': 'WallAttach', 'WClimbImpact1': 'WallClimb'}


# ================================================================================================ sampling (Blender only)
def sample_blender(path):
    import bpy
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps = int(FPS)          # the glTF importer maps seconds to frames with the scene rate: set it BEFORE import
    if path.lower().endswith('.fbx'): bpy.ops.import_scene.fbx(filepath=path)
    else: bpy.ops.import_scene.gltf(filepath=path)
    arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    missing = [b for b in BONES if b not in arm.pose.bones]
    if missing: raise SystemExit('measure_timing: rig lacks %s' % missing)
    arm.animation_data_create()
    tel = {}
    for act in bpy.data.actions:
        name = act.name.split('|')[-1]
        arm.animation_data.action = act
        if getattr(act, 'slots', None) and len(act.slots) and hasattr(arm.animation_data, 'action_slot'):
            arm.animation_data.action_slot = act.slots[0]
        f0, f1 = int(round(act.frame_range[0])), int(round(act.frame_range[1]))
        rows = []
        for f in range(f0, f1 + 1):
            sc.frame_set(f)
            rows.append({b: [round(v, 5) for v in (arm.matrix_world @ arm.pose.bones[b].head)] for b in BONES})
        tel[name] = {'fps': FPS, 'f0': f0, 'rows': rows}
        print('SAMPLED %-10s frames %d..%d' % (name, f0, f1))
    return tel


# ================================================================================================ analysis (pure Python)
class Clip:
    def __init__(self, name, d):
        self.name, self.R = name, d['rows']
        self.n = len(self.R); self.fps = d.get('fps', FPS); self.dur = (self.n - 1) / self.fps

    def t(self, i): return round(i / self.fps, 4)
    def z(self, i, b): return self.R[i][b][2]
    def floor(self, i): return min(self.R[i][b][2] for b in ('LeftFoot', 'RightFoot', 'LeftToeBase', 'RightToeBase'))
    def hips_over_feet(self, i): return self.z(i, 'Hips') - self.floor(i)

    def hand(self, i, s):   # hand relative to the hips' ground position (the game pins the hips' X/Y)
        h, p = self.R[i][s + 'Hand'], self.R[i]['Hips']
        return (h[0] - p[0], h[1] - p[1], h[2])

    def speed(self, s):
        out = []
        for i in range(self.n):
            a, b = max(0, i - 1), min(self.n - 1, i + 1)
            out.append(math.dist(self.hand(a, s), self.hand(b, s)) * self.fps / max(1, b - a))
        return out

    def hips_vz(self):
        return [(self.z(min(self.n - 1, i + 1), 'Hips') - self.z(max(0, i - 1), 'Hips')) * self.fps / max(1, min(self.n - 1, i + 1) - max(0, i - 1)) for i in range(self.n)]

    def gap(self, i): return math.dist(self.R[i]['LeftHand'], self.R[i]['RightHand'])
    def overhead(self, i): return min(self.z(i, 'LeftHand'), self.z(i, 'RightHand')) - self.z(i, 'Head')


def argmax(seq, lo, hi): return max(range(lo, hi), key=lambda i: seq[i])
def argmin(seq, lo, hi): return min(range(lo, hi), key=lambda i: seq[i])


def strike(c, det, hand):
    """-> (hit frame, peak frame, striking hand(s), peak speed)"""
    sp = {s: c.speed(s) for s in ('Left', 'Right')}
    lo, hi = SKIP, c.n - 1
    pk = {s: argmax(sp[s], lo, hi) for s in sp}
    s = hand or max(sp, key=lambda k: sp[k][pk[k]])
    p = pk[s]
    if det == 'peak': return p, p, s, sp[s][p]
    if det == 'gap':
        g = [c.gap(i) for i in range(c.n)]; gm = min(g[lo:hi])
        return next(i for i in range(lo, hi) if g[i] <= gm + 0.02), p, s, sp[s][p]
    if det == 'ground':   # the hand that goes lowest after its own speed peak
        best = None
        for k in ('Left', 'Right'):
            zs = [c.z(i, k + 'Hand') for i in range(c.n)]; m = min(zs[pk[k]:])
            if best is None or m < best[0]: best = (m, k, zs)
        m, k, zs = best
        return next(i for i in range(pk[k], c.n) if zs[i] <= m + 0.02), pk[k], k, sp[k][pk[k]]
    raise ValueError(det)


def follow_and_bout(c, peak, s, vmax):
    """follow-through end (striking hand < 25 % of peak), 10 % settle (reference only) and the next motion bout start"""
    sp = {k: c.speed(k) for k in ('Left', 'Right')}
    # follow-through over = the striking hand stays under 25 % of its peak for 3 frames (a one-frame dip at a rebound is not it)
    ft = next((i for i in range(peak, c.n) if all(sp[s][j] < 0.25 * vmax for j in range(i, min(c.n, i + 3)))), c.n - 1)
    st = next((i for i in range(peak, c.n) if sp[s][i] < 0.10 * vmax), None)
    bout = None
    for i in range(ft, c.n):
        k = next((k for k in sp if sp[k][i] > 0.40 * vmax), None)
        if k:   # walk back to the last speed minimum of that hand: where the new bout starts
            j = i
            while j > ft and sp[k][j - 1] <= sp[k][j]: j -= 1
            bout = j; break
    return ft, st, bout


def scale_for(clip, c):
    old = TODAY_LEN.get(clip)
    if not old: return 1.0
    r = c.dur / old
    return r if abs(r - 1.0) > 0.20 else 1.0


RATE_CAP, RATE_FLOOR = 1.6, 1.0   # the author's own rates are 1.25-1.6; a 5 s take at 4x gave a 50 m/s fist


def game_window(hit, dur, F0, T0, R0, H0, k):
    """2026-10-29 (director): a length-scaled clip keeps today's GAME-TIME windows exactly; only the playback rate changes.
    lead_game = (Hit - From) / Rate and recovery_game = (To - Hit) / Rate of today's constants; Rate = min(today's x k, 1.6), lowered
    until From >= 0 and To <= the clip end (never below 1.0; then the window is clamped and flagged). Returns (from, to, rate, note)."""
    lead, rec = (H0 - F0) / R0, (T0 - H0) / R0          # today's game-time windows (s)
    rate, note = min(R0 * k, RATE_CAP), []
    fit = min(hit / lead if lead > 0 else 1e9, (dur - hit) / rec if rec > 0 else 1e9)
    if fit < rate:
        rate = fit; note.append('rate lowered to fit the clip')
    if rate < RATE_FLOOR:
        rate = RATE_FLOOR; note.append('rate floor 1.0: window clamped to the clip (game-time NOT kept)')
    frm, to = max(0.0, hit - lead * rate), min(dur, hit + rec * rate)
    return frm, to, rate, ', '.join(note)


def measure(tel):
    clips = {n: Clip(n, d) for n, d in tel.items()}
    acts, segs, meas, flags = {}, {}, {}, {}
    for n, c in clips.items():   # diagnostics for every clip
        m = {'dur': round(c.dur, 4)}
        for s in ('Left', 'Right'):
            sp = c.speed(s); p = argmax(sp, SKIP, c.n - 1); m['peak_' + s] = [c.t(p), round(sp[p], 2)]
        hf = [c.hips_over_feet(i) for i in range(c.n)]; m['hips_low'] = c.t(argmin(hf, SKIP, c.n))
        oh = [c.overhead(i) for i in range(c.n)]; om = max(oh)
        if om > 0.1: m['overhead'] = c.t(next(i for i in range(c.n) if oh[i] >= 0.85 * om))
        fl = [c.floor(i) for i in range(c.n)]; ref = min(fl); on = [f <= ref + 0.03 for f in fl]
        off_i = next((i for i in range(SKIP, c.n) if on[i - 1] and not on[i]), None)
        on_i = next((i for i in range((off_i or SKIP), c.n) if on[i] and not on[i - 1]), None)
        m['feet_off'] = c.t(off_i) if off_i is not None else None
        m['feet_on'] = c.t(on_i) if on_i is not None else None
        meas[n] = m

    for key, (clip, det, hand) in ACTS.items():
        c = clips.get(clip)
        if not c: continue
        _, F0, T0, R0, H0 = TODAY_ACT[key]
        h, p, s, vmax = strike(c, det, hand)
        k = scale_for(clip, c)
        hit = c.t(h)
        ft, st, bout = follow_and_bout(c, p, s, vmax)
        why = []
        if k != 1.0:
            # length-scaled (video2rig) clip: today's game-time windows, rate capped at 1.6 (game_window); the measured bout /
            # follow-through only annotate
            frm, to, rate, nt = game_window(hit, c.dur, F0, T0, R0, H0, k)
            if nt: why.append(nt)
            if bout is not None and c.t(bout) < to: why.append('note: next bout %.3f inside the window' % c.t(bout))
        else:
            rate = R0
            frm = 0.0 if key == 'Throw' else max(0.0, hit - (H0 - F0))   # Throw: the old take starts on the carry pose
            to = hit + (T0 - H0)
            if bout is not None and to > c.t(bout): to = c.t(bout); why.append('next bout %.3f' % c.t(bout))
            if to > c.dur: to = c.dur; why.append('clip end')
            if to < c.t(ft): to = min(c.dur, c.t(ft)); why.append('follow-through %.3f' % c.t(ft))
        acts[key] = {'clip': clip, 'from': round(frm, 3), 'to': round(to, 3), 'rate': round(rate, 3), 'hit': round(hit, 3)}
        meas[clip].update(hit=hit, hit_hand=s, hit_by=det, follow_end=c.t(ft), settle10=c.t(st) if st is not None else None,
                          next_bout=c.t(bout) if bout is not None else None, len_scale=round(k, 3))
        flags[key] = ', '.join(why)

    c = clips.get('Lift')
    if c and 'overhead' in meas['Lift']:
        k = scale_for('Lift', c); oh = meas['Lift']['overhead']
        _, F0, T0, R0, _ = TODAY_ACT['Grab']
        if k != 1.0:   # Grab: hit = to = overhead; the game-time lift span (To - From) / Rate is today's, rate capped (game_window)
            g_from, _, g_rate, nt = game_window(oh, c.dur, F0, T0, R0, T0, k)
        else:
            g_from, g_rate, nt = max(0.0, oh - (T0 - F0)), R0, ''
        acts['Grab'] = {'clip': 'Lift', 'from': round(g_from, 3), 'to': oh, 'rate': round(g_rate, 3), 'hit': oh}
        acts['Carry'] = {'clip': 'Lift', 'from': oh, 'to': round(c.t(c.n - 2), 3), 'rate': 0.0}
        flags['Grab'] = nt; flags['Carry'] = ''

    c = clips.get('Jump')
    if c:
        vz = c.hips_vz(); hf = [c.hips_over_feet(i) for i in range(c.n)]
        hz = [c.z(i, 'Hips') for i in range(c.n)]
        lf = argmax(vz, SKIP, c.n - 10)                       # fastest rise
        low = argmin(hf, SKIP, lf + 1)                         # deepest crouch before it
        start = argmax(hz, SKIP, low + 1)                      # hips' highest point before the crouch
        launch = next((i for i in range(low, lf + 1) if vz[i] > 0.5), lf)
        apex = argmax(hz, lf, c.n - 10)
        segs.update(JChargeLo=c.t(start), JChargeHi=c.t(low), JLaunch=c.t(launch), JApex=c.t(apex))
        meas['Jump'].update(launch_fastest=c.t(lf))
    for wn in ('WallAttach', 'WallClimb'):
        c = clips.get(wn)
        if not c: continue
        oh = [c.overhead(i) for i in range(c.n)]; im = argmax(oh, 0, c.n)
        imp = next(i for i in range(c.n) if oh[i] > oh[im] - 0.08)
        hh = [max(c.z(i, 'LeftHand'), c.z(i, 'RightHand')) - c.z(i, 'Head') for i in range(c.n)]
        lo2 = min(c.n - 1, im + int(0.3 * c.fps))
        # second fist: the next fist-height peak once the first has come down (search to 2.5 s past the first impact)
        hi2 = min(c.n, imp + int(2.5 * c.fps))
        j = lo2
        while j + 1 < hi2 and hh[j + 1] <= hh[j]: j += 1      # down from the first impact
        i2 = argmax(hh, j, hi2)
        meas[wn].update(impact=c.t(imp), impact2=c.t(i2))
        # each clip writes its own fist-in times and segment end (they were one clip until the keep-the-best mix; C++ keeps
        # WAttachImpact2 / WAttachEnd / WClimbImpact1 at today's shared values when absent)
        if wn == 'WallAttach': segs.update(WAttachImpact=c.t(imp), AttachStart=round(max(0.0, c.t(imp) - 0.5), 4),
                                           WAttachImpact2=c.t(i2), WAttachEnd=round(min(c.dur, c.t(i2) + CLIMB_HI_OFF), 4))
        elif c.dur < 0.5 * TODAY_LEN['WallClimb']:
            # a single hand-over-hand climb CYCLE (video2rig WallClimb, a refined loop of ~1.2 s), not the 5 s two-fist slam: the
            # game loops the whole cycle and each fist goes in when it arrives at its height peak (first frame within 2 cm of that hand's max after its low point, cyclic;
            # WImpacts K=0 -> left hand, K=1 -> right hand, as WallPunchFx(K % 2) / BHand[0] = LeftHand)
            pk = {}
            for hb in ('LeftHand', 'RightHand'):
                hz = [c.z(i, hb) - c.z(i, 'Head') for i in range(c.n - 1)]; m = max(hz); lo = hz.index(min(hz))   # last = first frame
                pk[hb] = next(k % (c.n - 1) for k in range(lo, lo + c.n - 1) if hz[k % (c.n - 1)] > m - 0.02)   # arrival after its low
            meas[wn].update(mode='cycle', impact_left=c.t(pk['LeftHand']), impact_right=c.t(pk['RightHand']))
            segs.update(WClimbImpact1=c.t(pk['LeftHand']), WClimbImpact2=c.t(pk['RightHand']), WClimbLo=0.0, WClimbHi=round(c.dur, 4))
        else: segs.update(WClimbImpact1=c.t(imp), WClimbImpact2=c.t(i2), WClimbLo=round(max(0.0, c.t(imp) - CLIMB_LO_OFF), 4),
                          WClimbHi=round(min(c.dur, c.t(i2) + CLIMB_HI_OFF), 4))
    c = clips.get('Land')
    if c:
        fl = [c.floor(i) for i in range(c.n)]; settled = min(fl[c.n // 2:])
        on = next((i for i in range(c.n) if fl[i] <= settled + 0.03), 0)
        segs['LandStart'] = c.t(on)
        h, _, _, _ = strike(c, 'ground', None); meas['Land'].update(hit=c.t(h), hit_by='ground', feet_land=c.t(on))
    c = clips.get('StopLunge')
    if c:
        hz = [c.z(i, 'Hips') for i in range(c.n)]
        # coil start = top of the biggest continuous hips descent (the stride bob is a few cm, the coil ~0.17 m on brute_v5)
        best, i = (0.0, SKIP), SKIP
        while i < c.n - 1:
            j = i
            while j + 1 < c.n and hz[j + 1] < hz[j]: j += 1
            if hz[i] - hz[j] > best[0]: best = (hz[i] - hz[j], i)
            i = j + 1
        j = best[1]
        segs['LungeStart'] = round(max(0.0, c.t(j) - LUNGE_CAL), 4)
        meas['StopLunge'].update(coil=c.t(j))
    hit_tab = {n: meas[n]['hit'] for n in TODAY_HIT if n in meas and 'hit' in meas[n]}
    return acts, segs, meas, flags, hit_tab


# ================================================================================================ output
def act_clip(key): return TODAY_ACT[key][0]


def select(tel, args, meta):
    names = set(tel)
    if args.get('clips'): return set(args['clips'].split(',')) & names
    if args.get('all') or meta is None: return names
    new = {n for n, m in meta.items() if re.search(r'v2r', m.get('src', ''), re.I)}
    return new & names


def compare(acts, segs, flags, tol):
    worst, rows = 0.0, []
    print('\n%-10s %-5s %7s %7s %7s  %s' % ('act', 'field', 'today', 'measured', 'diff', 'note'))
    for key in TODAY_ACT:
        if key not in acts: continue
        _, F0, T0, R0, H0 = TODAY_ACT[key]
        a = acts[key]
        for fld, old in (('from', F0), ('to', T0), ('rate', R0), ('hit', H0)):
            if fld not in a or (key == 'Carry' and fld == 'hit'): continue
            d = a[fld] - old; worst = max(worst, abs(d)) if fld != 'rate' else worst
            note = flags.get(key, '') if fld == 'to' else ('lead kept from today' if fld == 'from' and key not in ('Throw', 'Carry') else '')
            if key == 'Grab' and fld == 'hit': note = 'Grab hit = to (ActHitAt uses To)'
            rows.append((key, fld, old, a[fld], d, note))
            print('%-10s %-5s %7.3f %7.3f %+7.3f  %s' % (key, fld, old, a[fld], d, note))
    for key, old in TODAY_SEG.items():
        if key not in segs: continue
        d = segs[key] - old; worst = max(worst, abs(d))
        note = 'cal (offset calibrated on brute_v5: exact by construction)' if key == 'LungeStart' else ''
        rows.append((key, 'seg', old, segs[key], d, note))
        print('%-10s %-5s %7.3f %7.3f %+7.3f  %s' % (key, 'seg', old, segs[key], d, note))
    print('worst |diff| %.3f s (tolerance %.3f)' % (worst, tol))
    print('\ngame-time windows (s): From->Hit and Hit->To at the act\'s rate, today vs measured')
    print('%-9s %7s %7s %7s   %7s %7s %7s   %6s' % ('act', 'lead0', 'lead', 'diff', 'rec0', 'rec', 'diff', 'rate'))
    gworst = 0.0
    for key in TODAY_ACT:
        if key not in acts or key == 'Carry': continue
        _, F0, T0, R0, H0 = TODAY_ACT[key]
        a = acts[key]; H0g = T0 if key == 'Grab' else H0
        l0, r0 = (H0g - F0) / R0, (T0 - H0g) / R0
        l1, r1 = (a['hit'] - a['from']) / a['rate'], (a['to'] - a['hit']) / a['rate']
        gworst = max(gworst, abs(l1 - l0), abs(r1 - r0))
        print('%-9s %7.3f %7.3f %+7.3f   %7.3f %7.3f %+7.3f   %6.3f' % (key, l0, l1, l1 - l0, r0, r1, r1 - r0, a['rate']))
    print('worst game-time |diff| %.3f s' % gworst)
    return worst, rows


def selftest_rule():
    """game_window on synthetic numbers (no Blender, no telemetry): game-time windows kept, rate in [1.0, 1.6]."""
    ok = True
    def chk(name, got, cond):
        nonlocal ok
        ok &= bool(cond); print('RULE %-44s %s %s' % (name, ['%.4f' % x if isinstance(x, float) else x for x in got], 'ok' if cond else 'FAIL'))
    F0, T0, R0, H0 = 0.45, 1.40, 1.6, 1.0                        # PunchR today: lead 0.34375 s, recovery 0.25 s game-time
    lead, rec = (H0 - F0) / R0, (T0 - H0) / R0
    f, t, r, n = game_window(1.533, 5.067, F0, T0, R0, H0, 5.067 / 1.533)                    # long take: cap 1.6
    chk('PunchR 5 s take -> rate 1.6, windows kept', (f, t, r), abs(r - 1.6) < 1e-9 and abs((1.533 - f) / r - lead) < 1e-9 and abs((t - 1.533) / r - rec) < 1e-9)
    f, t, r, n = game_window(1.533, 1.80, F0, T0, R0, H0, 1.80 / 1.533 + 0.3)                # recovery hits the clip end: rate lowered
    chk('short tail -> rate lowered to fit, To = clip end', (f, t, r), abs(r - (1.80 - 1.533) / rec) < 1e-9 and abs(t - 1.80) < 1e-9 and r < 1.6 and abs((1.533 - f) / r - lead) < 1e-9)
    f, t, r, n = game_window(1.533, 1.60, F0, T0, R0, H0, 2.0)                               # would need < 1.0: floor, flagged
    chk('tail too short -> floor 1.0, clamped + flagged', (f, t, r, n), r == 1.0 and t == 1.60 and 'NOT kept' in n)
    f, t, r, n = game_window(0.20, 5.0, F0, T0, R0, H0, 3.0)                                 # contact very early: lead decides
    chk('early contact (needs rate 0.58) -> floor 1.0, flagged', (f, t, r, n), r == 1.0 and f == 0.0 and 'NOT kept' in n)
    f, t, r, n = game_window(0.50, 5.0, F0, T0, R0, H0, 3.0)                                 # lead limits: rate = hit / lead
    chk('lead limits -> rate 1.4545, From = 0, windows kept', (f, t, r), abs(r - 0.50 / lead) < 1e-9 and abs(f) < 1e-9 and abs((t - 0.50) / r - rec) < 1e-9)
    f, t, r, n = game_window(4.133, 5.067, 0.0, 1.46, 1.25, 0.45, 5.067 / 1.467)             # v2r Throw: recovery limits it
    chk('Throw v2r -> rate 1.155, windows kept', (f, t, r), abs((4.133 - f) / r - 0.36) < 1e-9 and abs((t - 4.133) / r - 0.808) < 1e-9 and r <= 1.6)
    print('RULE SELFTEST', 'PASS' if ok else 'FAIL'); sys.exit(0 if ok else 3)


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    args, pos, i = {}, [], 0
    while i < len(argv):
        a = argv[i]
        if a in ('--out', '--meta', '--clips', '--dump', '--telemetry', '--check-today'): args[a[2:].replace('-', '_')] = argv[i + 1]; i += 2
        elif a == '--all': args['all'] = True; i += 1
        else: pos.append(a); i += 1
    if '--selftest-rule' in argv:
        selftest_rule(); return
    if 'telemetry' in args:
        tel = json.load(open(args['telemetry'])); src = args['telemetry']
    else:
        if not pos: raise SystemExit(__doc__ or 'usage: see header')
        src = os.path.abspath(pos[0]); tel = sample_blender(src)
    if args.get('dump'): json.dump(tel, open(args['dump'], 'w')); print('DUMPED', args['dump'])
    mp = args.get('meta') or (os.path.join(os.path.dirname(src), 'clips_meta.json') if 'telemetry' not in args else None)
    meta = json.load(open(mp)) if mp and os.path.isfile(mp) else None
    acts, segs, meas, flags, hit_tab = measure(tel)
    keep = select(tel, args, meta)
    out = {'note': 'Brute clip timing measured from the clips by tools/brute/v2r/measure_timing.py; read by ABruteCharacter '
                   '(LoadClipTiming). Absent keys keep the C++ constants. Times in clip seconds.',
           'source': src, 'date': date.today().isoformat(), 'clips': sorted(keep),
           'acts': {k: v for k, v in acts.items() if v['clip'] in keep},
           'segments': {k: v for k, v in segs.items() if SEG_CLIP[k] in keep},
           'hit_table': {k: v for k, v in hit_tab.items() if k in keep},
           'measured': {k: v for k, v in meas.items()}}
    print('ACTS', json.dumps(out['acts']))
    print('SEGMENTS', json.dumps(out['segments']))
    print('HIT (assemble_motion HIT table)', json.dumps(hit_tab))
    o = args.get('out', DEFAULT_OUT)
    if o != '-' and not out['acts'] and not out['segments']:
        print('NOTHING TO WRITE: no selected clip (default = video2rig clips only; --all / --clips to choose)%s'
              % ('; NOTE %s exists and still overrides the game' % o if os.path.isfile(o) else ''))
    elif o != '-':
        os.makedirs(os.path.dirname(os.path.abspath(o)), exist_ok=True)
        json.dump(out, open(o, 'w'), indent=1); print('WROTE', o, 'acts', sorted(out['acts']), 'segments', sorted(out['segments']))
    if 'check_today' in args:
        worst, _ = compare(acts, segs, flags, float(args['check_today']))
        if worst > float(args['check_today']): print('CHECK FAILED'); sys.exit(3)
        print('CHECK OK')


if __name__ == '__main__':
    main()
