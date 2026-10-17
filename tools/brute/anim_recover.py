# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
# Heavy recovery for a one-shot clip (owner 2026-10-17, Throw: "the recovery after the follow-through is a generic pose blend; make it
# read as a real heavy recovery: settle the weight, straighten up powerfully, no floaty interpolation"). Replaces everything after
# frame KS of <clip.glb> with a procedural recovery from the KS pose to a target stance (a frame of another clip, e.g. the Idle,
# so the game's blend back to Idle is short), in Blender:
#   - momentum first: for a few frames the body keeps folding (hips sink, chest dips further) instead of instantly reversing
#   - then an under-damped spring per body part with follow-through / overlap: hips lead, spine 2 frames later, head 1 frame after
#     the hips (eyes come up first), the heavy arms ~5 frames late with a bigger overshoot (they swing past and settle)
#   - parent-relative per-bone blends with extrapolation (overshoot), hips height spring + dip, feet pinned where they were at KS
#     (2-bone leg IK), the last frames converge exactly onto the target pose
# usage: Blender -b --factory-startup -P tools/brute/anim_recover.py -- <clip.glb> <KS> <N_out> <target.glb> <target_frame> <out.glb> [Name]
#   KS: last frame (offset from the clip start) taken from the clip; N_out: total output frames (clip length after the rebuild)
# 2026-10-17 Throw: anim_recover.py -- motion_bak_anim/Brute_throw.glb 15 45 motion_bak_anim/Emerald_Behemoth_idle_30fps.glb 2 Brute_throw.glb
#   (frames 0-15 = the overhead load + hurl, unchanged; hit 0.45 s; duration 1.47 s unchanged)
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import anim_lib as L
from mathutils import Vector, Quaternion
import bpy

a = sys.argv[sys.argv.index('--') + 1:]
CLIP, KS, NOUT, TGT, TFR, OUT = a[0], int(a[1]), int(a[2]), a[3], float(a[4]), a[5]
NAME = a[6] if len(a) > 6 else 'Throw'
UP = L.UP
# target pose first (its own scene), then the clip
L.load(TGT); tw, trh = L.sample(L.S['f0'] + TFR)
T_RQ = dict(L.S['RQ']); T_pos = L.fk(tw, trh)
T_head = L.heading(tw, trh)
T_floor = min(T_pos[s + 'ToeBase'].z for s in ('Left', 'Right'))
T_feet_mid = (T_pos['LeftFoot'] + T_pos['RightFoot']) / 2
T_hips_off = trh - T_feet_mid; T_hips_z = trh.z - T_floor
T_rel = {n: (tw[n] if L.S['PAR'][n] is None else tw[L.S['PAR'][n]].inverted() @ tw[n]) for n in tw}
arm, act, f0, f1 = L.load(CLIP)
src = L.sample_all()
PAR = L.S['PAR']; order = [b.name for b in L.S['order']]
def rel(ws): return {n: (ws[n] if PAR[n] is None else ws[PAR[n]].inverted() @ ws[n]) for n in order}
A_w, A_rh = src[KS]; A_rel = rel(A_w); A_pos = L.fk(A_w, A_rh)
# arm velocity at KS (world, per frame): the arms carry on through the follow-through for a few frames instead of stopping dead
P_w = src[KS - 1][0]
VEL = {n: A_w[n] @ P_w[n].inverted() for n in A_w}
DECAY = 0.62
A_head = L.heading(*src[0])
floor = min(A_pos[s + 'ToeBase'].z for s in ('Left', 'Right'))
# target aligned to this clip's facing (frame 0 heading), hips over the KS feet
Yq = Quaternion(UP, A_head - T_head)
B_rel = dict(T_rel); B_rel['Hips'] = Yq @ T_rel['Hips']
feet_mid = (A_pos['LeftFoot'] + A_pos['RightFoot']) / 2
B_rh = Vector((feet_mid.x, feet_mid.y, floor)) + Yq @ Vector((T_hips_off.x, T_hips_off.y, 0)) + Vector((0, 0, T_hips_z))
# the bind of the target clip's file and this clip's file is the same rig: relative rotations transfer directly
def qpow(q, w):
    ang = q.angle
    if ang > math.pi: q = -q; ang = q.angle
    return Quaternion(q.axis, ang * w) if ang > 1e-6 else Quaternion()
def rblend(qa, qb, w):   # parent-relative blend with extrapolation beyond 1 (overshoot) and below 0 (momentum)
    d = qb @ qa.inverted()
    if d.w < 0: d = -d
    return qpow(d, w) @ qa
def spring(x, tau, period):
    if x <= 0: return 0.0
    om = 2 * math.pi / period
    return 1 - math.exp(-x / tau) * (math.cos(om * x) + math.sin(om * x) / (tau * om))
GROUP = {}
for n in order:
    if n == 'Hips': GROUP[n] = 'hips'
    elif n in ('Spine', 'Spine1', 'Spine2'): GROUP[n] = 'spine'
    elif n in ('Neck', 'Head'): GROUP[n] = 'head'
    elif any(n.startswith(s) for s in ('LeftShoulder', 'RightShoulder')): GROUP[n] = 'shoulder'
    elif any(n.startswith(s + p) for s in ('Left', 'Right') for p in ('Arm', 'ForeArm', 'Hand')): GROUP[n] = 'arm'
    else: GROUP[n] = 'legs'
# per group: delay (frames), tau, period -> under-damped step response; arms late and loose, head early
SPR = {'hips': (3, 4.0, 24), 'spine': (4.5, 4.5, 26), 'head': (3.5, 4.0, 22), 'shoulder': (5, 5.0, 22), 'arm': (2, 5.0, 20), 'legs': (3, 4.0, 24)}
R = NOUT - 1 - KS          # recovery frames
DIP = 0.045 * L.leg_len()  # momentum sink of the hips
LEAN = 4.0                 # deg: extra forward fold before the rise
def weights(t):
    w = {}
    for g, (dl, tau, per) in SPR.items():
        x = t - dl
        v = spring(x, tau, per)
        # converge exactly in the last 5 frames
        e = L.smooth((t - (R - 5)) / 5)
        w[g] = v * (1 - e) + e
    return w
mom = lambda t: (L.smooth(t / 4) if t <= 4 else 1 - L.smooth((t - 4) / 7)) if t < 11 else 0.0   # momentum lobe 0 -> 1 -> 0
def bump(t, a_, b_, c_): return 0.0 if t <= a_ or t >= c_ else L.smooth((t - a_) / (b_ - a_)) if t <= b_ else 1 - L.smooth((t - b_) / (c_ - b_))
SETTLE = 0.018 * L.leg_len()   # after the rise: the weight settles once more (small sink + exhale) before the stance holds
frames = [src[k] for k in range(KS + 1)]
lat0 = (A_pos['RightUpLeg'] - A_pos['LeftUpLeg']); lat0.z = 0; lat0.normalize(); fwd0 = UP.cross(lat0)
for t in range(1, R + 1):
    w = weights(t); m = mom(t)
    new = {}
    for n in order:
        q = rblend(A_rel[n], B_rel[n], w[GROUP[n]])
        new[n] = q if PAR[n] is None else new[PAR[n]] @ q
    # heavy arms: the bone DIRECTIONS of the upper arm / forearm are blended in world space (they hang and swing down under gravity
    # while the torso rises instead of riding along with the chest); twist stays the parent-relative blend (no 180-deg roll flips)
    RHp = L.S['RH']; RQ = L.S['RQ']
    for s_ in ('Left', 'Right'):
        Bw = {}; par = new[s_ + 'Shoulder']
        for n in (s_ + 'Arm', s_ + 'ForeArm'): par = par @ B_rel[n]; Bw[n] = par
        for n, c in ((s_ + 'Arm', s_ + 'ForeArm'), (s_ + 'ForeArm', s_ + 'Hand')):
            v = RHp[c] - RHp[n]
            dA = (A_w[n] @ RQ[n].inverted()) @ v; dB = (Bw[n] @ RQ[n].inverted()) @ v; dC = (new[n] @ RQ[n].inverted()) @ v
            ax = dA.cross(dB); ang = dA.angle(dB)
            dT = (Quaternion(ax.normalized(), ang * w['arm']) @ dA) if ax.length > 1e-6 else dA
            c_ = sum(DECAY ** i for i in range(1, t + 1)) * (1 - min(1.0, w['arm']))   # carried momentum, fading as the spring takes over
            dT = qpow(VEL[n], c_) @ dT
            new = L.rebuild(new, {n: dC.rotation_difference(dT) @ new[n]})
    # momentum: the chest keeps folding forward a little (about the hips' lateral axis) before the rise
    st = bump(t, 12, 17, 26)
    ql = Quaternion(lat0, math.radians(LEAN * m + 2.5 * st))
    if (ql @ UP).dot(fwd0) < 0: ql = Quaternion(lat0, -math.radians(LEAN * m + 2.5 * st))
    cs_ = sum(0.55 ** i for i in range(1, t + 1)) * (1 - min(1.0, w['spine']))   # the torso carries its hurl rotation a little
    new = L.rebuild(new, {'Spine': qpow(VEL['Spine2'], cs_) @ ql @ new['Spine']})
    rh = A_rh.lerp(B_rh, w['hips']) - UP * (DIP * m + SETTLE * st)
    # feet stay where they were at KS
    over = {}
    for s in ('Left', 'Right'):
        over.update(L.leg_ik(L.rebuild(new, over), rh, s, A_pos[s + 'Foot'], foot_rot=A_w[s + 'Foot']))
    new = L.rebuild(new, over)
    frames.append((new, rh))
    if t % 4 == 0 or t == R:
        p = L.fk(new, rh)
        print('R t %2d  w hips %.2f spine %.2f arm %.2f  mom %.2f  hips z %.3f  head z %.3f  hands z %.2f' % (t, w['hips'], w['spine'], w['arm'], m, rh.z,
              p['Head'].z, (p['LeftHand'].z + p['RightHand'].z) / 2))
L.write(frames, OUT, NAME)
print('RECOVER', NAME, 'kept 0..%d, recovery %d frames, total %d (%.2f s)' % (KS, R, len(frames), (len(frames) - 1) / 30))
