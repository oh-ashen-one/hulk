# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
# Slap rebuilt from the retargeted Meshy take (owner 2026-10-17: "spinning backhand, his back faces the camera at the swing; want a
# huge brutal open-hand backhand delivered FORWARD, torso twist 45-60 deg max, chest mostly toward the target, big arm sweep across
# the front, weight shift"). The take's legs, wind-up and recovery are kept; in Blender:
#   - pelvis and chest heading vs frame 0 are soft-limited (tanh) to +PEL_A/-PEL_B and +CH_A/-CH_B deg; during the swing both are
#     driven by one kinetic-chain curve (pelvis leads, chest 1 frame later, arm last) from the wound pose to the follow-through
#   - the right arm is posed procedurally in the swing window (2-bone IK): a near-horizontal arc in FRONT of the body from the
#     wind-up at the left shoulder to a straight-arm contact in front of the chest at the hit frame (peak speed) and out to the
#     right side, back of the open hand leading; blended in/out of the take's arm
#   - head counter-turns toward the target, hips shift forward onto the front (left) foot at the hit and drop, feet stay planted
# usage: Blender -b --factory-startup -P tools/brute/anim_slap.py -- <slap_take.glb> <out.glb>
#   env SLAP_WIND / SLAP_HIT / SLAP_END: swing frames (default 21 / 27 / 33)
# 2026-10-17 Slap: input = the previous Brute_slap.glb (Meshy take 01a143f9-3e49-7368-a4fa-fdffd7a4e3ca, ~/hulk-scratch/brute_v2/motion_bak_anim/),
#   defaults; contact frame 27 = 0.90 s (assemble_motion.py HIT)
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import anim_lib as L
from mathutils import Vector, Quaternion, Matrix

a = sys.argv[sys.argv.index('--') + 1:]
SRC, OUT = a[0], a[1]
arm, act, f0, f1 = L.load(SRC)
KW, KH, KE = (int(os.environ.get(k, d)) for k, d in (('SLAP_WIND', 21), ('SLAP_HIT', 27), ('SLAP_END', 33)))
CH_A, CH_B, PEL_A, PEL_B = 45.0, 55.0, 25.0, 35.0
RQ, RH = L.S['RQ'], L.S['RH']
UP = L.UP
src = L.sample_all(); n = len(src)
h0 = L.heading(*src[0]); FWD = Vector((math.cos(h0), math.sin(h0), 0)); RGT = FWD.cross(UP)
def soft(y, A, B): return A * math.tanh(y / A) if y > 0 else B * math.tanh(y / B)
def unwrap(seq):
    out = []; acc = None
    for v in seq:
        if acc is None: acc = L.wrap(v - h0)
        else: acc += L.wrap(v - prev)
        prev = v; out.append(acc)
    return out
pel = [math.degrees(x) for x in unwrap([L.heading(w, rh) for w, rh in src])]
che = [math.degrees(x) for x in unwrap([L.heading(w, rh, 'LeftArm', 'RightArm') for w, rh in src])]
def s_curve(t):   # swing progress 0..1 over [KW, KE], fastest at KH
    if t <= KW: return 0.0
    if t >= KE: return 1.0
    if t <= KH: u = (t - KW) / (KH - KW); return 0.5 * u * u          # accelerate into the hit
    u = (t - KH) / (KE - KH); return 0.5 + 0.5 * (1 - (1 - u) ** 2)   # decelerate after it
Yw, Ye = soft(che[KW], CH_A, CH_B), soft(che[KE], CH_A, CH_B)
Pw, Pe = soft(pel[KW], PEL_A, PEL_B), soft(pel[KE], PEL_A, PEL_B)
def chest_t(k): return Yw + (Ye - Yw) * s_curve(k + 1) if KW - 1 <= k <= KE else soft(che[k], CH_A, CH_B)
def pel_t(k): return Pw + (Pe - Pw) * s_curve(k + 2.5) if KW - 2.5 <= k <= KE else soft(pel[k], PEL_A, PEL_B)
def Rz(deg): return Quaternion(UP, math.radians(deg))
def bump(k, a_, b_, c_):   # 0 at a_, 1 at b_, 0 at c_ (smooth)
    return L.smooth((k - a_) / (b_ - a_)) if k <= b_ else 1 - L.smooth((k - b_) / (c_ - b_))
# right hand frame from the bind pose: finger axis f (wrist -> middle knuckle), palm normal p (finger curl side)
def hand_frame(s):
    w_ = RH[s + 'Hand']; k_ = RH[s + 'HandMiddle1']; f = (k_ - w_).normalized()
    tip = L.S['W'] @ arm.data.bones[s + 'HandMiddle2'].tail_local; c = tip - k_; c -= c.dot(f) * f
    across = RH[s + 'HandIndex1'] - RH[s + 'HandPinky1']; across -= across.dot(f) * f
    p = f.cross(across).normalized()
    if p.dot(c) < 0: p = -p
    return f, p
HF, HP = hand_frame('Right')
def frame_rot(f_new, p_new):
    def M(x, y):
        x = x.normalized(); y = (y - y.dot(x) * x).normalized(); return Matrix((x, y, x.cross(y))).transposed()
    return (M(f_new, p_new) @ M(HF, HP).inverted()).to_quaternion()
l1 = (RH['RightForeArm'] - RH['RightArm']).length; l2 = (RH['RightHand'] - RH['RightForeArm']).length; LA = l1 + l2
# targets (assemble's foot lock re-plants as well): plants of the take
tg = {s: L.plant_targets(src, s, keep=[(0, len(src) - 1)])[0] for s in ('Left', 'Right')}   # both feet stay planted (the take slides them)
frames = []; info = {}
# the take's upper body is contorted through its spin (big back bend / roll): in [KW, KR] the pelvis, spine, neck, head and left arm
# are a two-pose blend (parent-relative) from the wound pose at KW to the take's settled pose at KR (pitch / roll), the heading is
# then driven by the kinetic-chain yaw curve above, plus a forward lean into the hit
KR = int(os.environ.get('SLAP_REC', 56))
UPPER = ['Hips', 'Spine', 'Spine1', 'Spine2', 'Neck', 'Head', 'LeftShoulder', 'LeftArm', 'LeftForeArm', 'LeftHand', 'RightShoulder']
PAR = L.S['PAR']
def rel(ws): return {b.name: (ws[b.name] if PAR[b.name] is None else ws[PAR[b.name]].inverted() @ ws[b.name]) for b in L.S['order']}
RA, RB = rel(src[KW][0]), rel(src[KR][0])
def g_curve(k):
    if k <= KE: return 0.6 * s_curve(k)
    return 0.6 + 0.4 * L.smooth((k - KE) / (KR - KE))
LAT0 = None
for k in range(n):
    ws, rh = src[k]
    if KW < k < KR:
        g = g_curve(k); r_ = rel(ws); new = {}
        for b in L.S['order']:
            nm = b.name; p = PAR[nm]
            q = RA[nm].slerp(RB[nm], g) if nm in UPPER else r_[nm]
            new[nm] = q if p is None else new[p] @ q
        lean = 14 * bump(k, KW, KH + 1, KR)   # deg, forward into the hit
        posn = L.fk(new, rh); lat = posn['RightUpLeg'] - posn['LeftUpLeg']; lat.z = 0; lat.normalize()
        ql = Quaternion(lat, math.radians(lean))
        if (ql @ UP).dot(FWD) < 0: ql = Quaternion(lat, -math.radians(lean))
        new = L.rebuild(new, {'Spine': ql @ new['Spine']})
        for s_ in ('Left', 'Right'):   # legs keep the take's world rotations (feet re-planted below)
            for b_ in ('UpLeg', 'Leg', 'Foot', 'ToeBase'): new[s_ + b_] = ws[s_ + b_]
        new = L.rebuild(new, {s_ + b_: ws[s_ + b_] for s_ in ('Left', 'Right') for b_ in ('UpLeg', 'Leg', 'Foot', 'ToeBase')})
        rh = src[KW][1].lerp(src[KR][1], g)
        ws = new
        # the blended pose's own headings (the yaw curve corrects from these)
        pel_k = math.degrees(L.wrap(L.heading(ws, rh) - h0)); che_k = math.degrees(L.wrap(L.heading(ws, rh, 'LeftArm', 'RightArm') - h0))
    else: pel_k, che_k = pel[k], che[k]
    dP = pel_t(k) - pel_k; dC = chest_t(k) - che_k
    cur = L.rebuild(ws, {'Hips': Rz(dP) @ ws['Hips']})
    for b in ('Spine', 'Spine1', 'Spine2'):
        cur = L.rebuild(cur, {b: Rz((dC - dP) / 3) @ cur[b]})
    cur = L.rebuild(cur, {'Neck': Rz(-0.35 * chest_t(k)) @ cur['Neck']})   # eyes stay on the target
    # weight shift onto the front foot + drop at the hit
    sh = bump(k, KW - 4, KH + 2, KH + 22)
    rh2 = rh + (FWD * 0.07 - RGT * 0.035 - UP * 0.035) * sh
    # right arm swing
    wA = L.smooth((k - (KW - 4)) / 4) if k < KW else 1.0 if k <= KE + 3 else 1 - ((k - KE - 3) / 12) ** 2 if k < KE + 15 else 0.0   # heavy arm drops (accelerating)
    if wA > 0:
        pos = L.fk(cur, rh2); S_ = pos['RightArm']; pw = pos
        if k <= KW:   # wind-up reference: the (corrected) take's hand, up to the wind-up frame
            info['wind_d'] = (pw['RightHand'] - S_).normalized(); info['wind_r'] = (pw['RightHand'] - S_).length / LA
        d_w, r_w = info['wind_d'], info['wind_r']
        d_h = (FWD * 1.0 - RGT * 0.40 + UP * 0.10).normalized()
        d_e = (RGT * 0.95 + FWD * 0.22 + UP * 0.22).normalized()
        s = s_curve(k)
        if k > KE: s = 1.0 + 0.10 * L.smooth((k - KE) / 6)              # carries on a little after the follow-through
        if s <= 0.5: d = d_w.slerp(d_h, s * 2); r = r_w + (0.97 - r_w) * L.smooth(s * 2)
        else:
            u = (s - 0.5) * 2
            d = d_h.slerp(d_e, min(u, 1.0)) if u <= 1 else (Quaternion(d_h.cross(d_e).normalized(), d_h.angle(d_e) * u) @ d_h)
            r = 0.97 - 0.05 * min(1.0, u)
        T = S_ + d * r * LA
        # travel direction (for the back of the hand leading): tangent of the arc (rotation axis x direction)
        ax_ = (d_w.cross(d_h) if s <= 0.5 else d_h.cross(d_e)).normalized()
        tang = ax_.cross(d).normalized()
        pw_ = L.smooth((s - 0.1) / 0.35); pole = (pos['RightForeArm'] - S_).normalized().lerp((-UP * 0.8 + FWD * 0.2 - RGT * 0.2).normalized(), pw_)   # elbow turns down gradually
        K2, T2 = L.ik2(S_, pos['RightForeArm'], T, l1, l2, pole)
        up_q = (pos['RightForeArm'] - S_).rotation_difference(K2 - S_) @ cur['RightArm']
        w2 = L.rebuild(cur, {'RightArm': up_q}); p2 = L.fk(w2, rh2)
        fo_q = (p2['RightHand'] - p2['RightForeArm']).rotation_difference(T2 - K2) @ w2['RightForeArm']
        f_dir = (T2 - K2).normalized()
        hand_q = frame_rot(f_dir, -tang) @ RQ['RightHand']       # palm faces away from the travel: back of the hand leads
        # forearm twist follows the hand (half of the hand's twist about the forearm axis goes into the forearm)
        over = {'RightArm': up_q, 'RightForeArm': fo_q, 'RightHand': hand_q}
        # open hand: straighten the fingers in line with the hand
        hw = L.rebuild(cur, over)
        hand_dir = (hw['RightHand'] @ RQ['RightHand'].inverted()) @ HF
        for fn in ('Index', 'Middle', 'Ring', 'Pinky'):
            for seg in ('', '1', '2'):
                bn = 'RightHand' + fn + seg
                if bn not in hw: continue
                ch = [c.name for c in arm.data.bones[bn].children]
                seg_rest = (RH[ch[0]] if ch else L.S['W'] @ arm.data.bones[bn].tail_local) - RH[bn]
                bd = (hw[bn] @ RQ[bn].inverted()) @ seg_rest
                over[bn] = Quaternion().slerp(bd.rotation_difference(hand_dir), 0.85) @ hw[bn]
                hw = L.rebuild(cur, over)
        full = L.rebuild(cur, over)
        if k == -1: print('DBG T', tuple(round(x, 2) for x in (T - S_)), 'got', tuple(round(x, 2) for x in (L.fk(full, rh2)['RightHand'] - S_)), 'LA %.2f r %.2f' % (LA, r))
        if wA < 1:   # blend the arm chain (+ fingers) between the take and the procedural swing, parent-relative (shortest arcs)
            names = set([b.name for b in arm.data.bones['RightArm'].children_recursive] + ['RightArm'])
            relc = {nm: cur[PAR[nm]].inverted() @ cur[nm] for nm in names}; relf = {nm: full[PAR[nm]].inverted() @ full[nm] for nm in names}
            out = {}
            for b in L.S['order']:
                nm = b.name
                if nm not in names: continue
                qf = relf[nm] if relc[nm].dot(relf[nm]) >= 0 else -relf[nm]
                out[nm] = (out[PAR[nm]] if PAR[nm] in out else cur[PAR[nm]]) @ relc[nm].slerp(qf, wA)
            if k in (KE + 4, KE + 8): print('BLEND k %d hand rel angle %.0f deg' % (k, math.degrees(relc['RightHand'].rotation_difference(relf['RightHand']).angle)))
            cur = L.rebuild(cur, out)
        else: cur = full
    frames.append((cur, rh2))
    if k in (0, KW, KH, KE, KE + 8, n - 1):
        p = L.fk(cur, rh2); o = p['Hips']
        print('K %2d chest %+.0f (take %+.0f) pel %+.0f (take %+.0f) RH fwd %.2f rgt %+.2f up %+.2f' % (k, chest_t(k), che[k], pel_t(k), pel[k],
              (p['RightHand'] - o).dot(FWD), (p['RightHand'] - o).dot(RGT), (p['RightHand'] - o).z))
frames = L.apply_feet(frames, tg)
L.write(frames, OUT, 'Slap')
print('SLAP contact frame', KH, '(%.2f s)' % (KH / 30), 'frames', n)
