# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
# Per-frame readout of one clip GLB (Blender): pelvis + chest heading vs frame 0 (deg, unwrapped), hips height, hands and feet
# in the frame-0 facing frame (x = right, y = forward, z = up, metres in the clip's units), hand gap.
# usage: Blender -b --factory-startup -P tools/brute/anim_measure.py -- <clip.glb> [every=1]
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import anim_lib as L
from mathutils import Vector
a = sys.argv[sys.argv.index('--') + 1:]
arm, act, f0, f1 = L.load(a[0]); EV = int(a[1]) if len(a) > 1 else 1
fr = L.sample_all()
h0 = L.heading(*fr[0]); ph = ch = None; up = uc = 0
fwd = Vector((math.cos(h0), math.sin(h0), 0)); rgt = fwd.cross(L.UP)
o = L.fk(*fr[0])['Hips'].copy(); o.z = 0
def loc(p): d = p - o; return '(%+.2f %+.2f %+.2f)' % (d.dot(rgt), d.dot(fwd), d.z)
print('CLIP', act.name, 'frames', f0, f1)
for i, (w, rh) in enumerate(fr):
    hp = L.heading(w, rh); hc = L.heading(w, rh, 'LeftArm', 'RightArm')
    if ph is not None: up += L.wrap(hp - ph); uc += L.wrap(hc - pc)
    else: up, uc = L.wrap(hp - h0), L.wrap(hc - h0)
    ph, pc = hp, hc
    if i % EV == 0:
        p = L.fk(w, rh)
        print('M %3d t%.2f pel %+5.0f chest %+5.0f hipsz %.2f  LH %s RH %s  LF %s RF %s gap %.2f' % (i, i / 30, math.degrees(up), math.degrees(uc), p['Hips'].z,
              loc(p['LeftHand']), loc(p['RightHand']), loc(p['LeftFoot']), loc(p['RightFoot']), (p['LeftHand'] - p['RightHand']).length))
