# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
# Soft-clamp an over-folded generated crouch (2026-10-17 critique: the Uppercut take curls the Brute into a ball, face on the floor,
# for ~0.4 s before the rise). Per frame: the forward torso pitch (Spine -> Neck vs vertical, along the hips' heading) is soft-limited
# to MAXP deg (tanh knee, so poses below the limit are untouched and the limit is approached smoothly), the correction is spread
# over Spine / Spine1 / Spine2; the hips are kept at least HMIN x their frame-0 height above the floor (soft), and both legs are
# re-solved (2-bone IK) so the feet stay exactly where they were.
# usage: Blender -b --factory-startup -P tools/brute/anim_clamp.py -- <clip.glb> <out.glb> <Name> [MAXP=50] [HMIN=0.62]
# 2026-10-17 Uppercut: anim_clamp.py -- motion_bak_anim/Brute_uppercut.glb Brute_uppercut.glb Uppercut 40 0.6 (timing unchanged, hit 0.6 s)
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import anim_lib as L
from mathutils import Vector, Quaternion
a = sys.argv[sys.argv.index('--') + 1:]
SRC, OUT, NAME = a[0], a[1], a[2]
MAXP = float(a[3]) if len(a) > 3 else 50.0; HMIN = float(a[4]) if len(a) > 4 else 0.62
HEADP = float(os.environ.get('CLAMP_HEADP', '35'))
L.load(SRC); src = L.sample_all(); UP = L.UP
P0 = L.fk(*src[0]); floor = min(min(L.fk(w, r)[s + 'ToeBase'].z for s in ('Left', 'Right')) for w, r in src)
H0 = P0['Hips'].z - floor
def softmax(x, lim, k):   # x below lim - k untouched, approaches lim smoothly
    if x <= lim - k: return x
    return lim - k + k * math.tanh((x - (lim - k)) / k)
out = []
for i, (w, rh) in enumerate(src):
    p = L.fk(w, rh)
    lat = p['RightUpLeg'] - p['LeftUpLeg']; lat.z = 0; lat.normalize(); fwd = UP.cross(lat)
    v = p['Neck'] - p['Spine']; pitch = math.degrees(math.atan2(v.dot(fwd), v.z))
    newp = softmax(pitch, MAXP, 15.0)
    h = rh.z - floor; hmin = HMIN * H0
    newh = h if h >= hmin + 0.08 * H0 else hmin + 0.08 * H0 * math.exp((h - hmin - 0.08 * H0) / (0.08 * H0))   # soft floor at hmin
    rh2 = Vector((rh.x, rh.y, floor + newh))
    cur = w
    if pitch - newp > 0.05:
        dq = Quaternion(lat, math.radians((pitch - newp) / 3))
        if (dq @ UP).dot(fwd) > 0: dq = Quaternion(lat, -math.radians((pitch - newp) / 3))
        for b in ('Spine', 'Spine1', 'Spine2'): cur = L.rebuild(cur, {b: dq @ cur[b]})
    # the neck is part of the fold: the neck -> head line is soft-limited to HEADP deg forward pitch (eyes come up)
    p2 = L.fk(cur, rh2); vh = p2['Head'] - p2['Neck']; hp = math.degrees(math.atan2(vh.dot(fwd), vh.z)); nh = softmax(hp, HEADP, 15.0)
    if hp - nh > 0.05:
        dn = Quaternion(lat, math.radians(hp - nh))
        if (dn @ UP).dot(fwd) > 0: dn = Quaternion(lat, -math.radians(hp - nh))
        cur = L.rebuild(cur, {'Neck': dn @ cur['Neck']})
    over = {}
    for s in ('Left', 'Right'): over.update(L.leg_ik(L.rebuild(cur, over), rh2, s, p[s + 'Foot'], foot_rot=w[s + 'Foot']))
    cur = L.rebuild(cur, over)
    out.append((cur, rh2))
    if abs(pitch - newp) > 0.5 or abs(newh - h) > 0.005:
        print('CLAMP f %2d head %.0f pitch %.0f -> %.0f  hips %.2f -> %.2f (x H0 %.2f -> %.2f)' % (i, hp, pitch, newp, h, newh, h / H0, newh / H0))
L.write(out, OUT, NAME)
