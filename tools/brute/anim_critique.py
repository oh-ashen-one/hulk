# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
# Numeric animation critique of every Brute clip (NLA track) in a GLB, Blender headless. Per clip:
#   - planted-foot slide (foot joint near its lowest height and not lifting: horizontal drift while planted, m)
#   - knee / elbow angle range (hyperextension = >178 deg straight) and the fastest per-frame change (pops)
#   - wrist bend vs forearm: fastest per-frame change (snaps)
#   - rotation pops: any bone whose local rotation accelerates by more than POP deg/frame^2 (second difference)
#   - hands inside the torso (wrist closer than TORSO_R to the hips->neck segment)
#   - loop seam (loops): largest bone rotation jump last -> first frame vs the typical per-frame step
#   - start / end: rotation speed on the first and last frame (a one-shot should start and end calm)
# usage: Blender -b --factory-startup -P tools/brute/anim_critique.py -- <in.glb> <out.json> [Clip,Clip,...]
import bpy, sys, os, json, math
from mathutils import Vector

a = sys.argv[sys.argv.index('--') + 1:]
GLB, OUT = a[0], a[1]
ONLY = a[2].split(',') if len(a) > 2 and a[2] not in ('', 'all') else None
POP = float(os.environ.get('CRIT_POP', '6'))       # deg / frame^2
TORSO_R = float(os.environ.get('CRIT_TORSO_R', '0.22'))
LOOPS = {'Idle', 'Walk', 'Run', 'Fall', 'WallClimb'}
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; sc.render.fps = 30
bpy.ops.import_scene.gltf(filepath=GLB)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
tracks = {t.name: t.strips[0].action for t in arm.animation_data.nla_tracks}
for t in list(arm.animation_data.nla_tracks): arm.animation_data.nla_tracks.remove(t)
MW = arm.matrix_world
BODY = [b.name for b in arm.data.bones if not any(k in b.name for k in ('Index', 'Middle', 'Ring', 'Pinky', 'Thumb'))]
def P(n): return MW @ arm.pose.bones[n].head
def qang(q):
    a_ = math.degrees(q.angle); return min(a_, 360 - a_)
def ang(u, v): return math.degrees(u.angle(v)) if u.length > 1e-6 and v.length > 1e-6 else 0.0
def seg_dist(p, a_, b_):
    ab = b_ - a_; t = max(0.0, min(1.0, (p - a_).dot(ab) / max(1e-9, ab.dot(ab)))); return (p - (a_ + ab * t)).length
res = {}
for name, act in tracks.items():
    if ONLY and name not in ONLY: continue
    arm.animation_data.action = act
    if hasattr(act, 'slots') and len(act.slots): arm.animation_data.action_slot = act.slots[0]
    f0, f1 = (int(round(x)) for x in act.frame_range)
    fr_ = []
    for fr in range(f0, f1 + 1):
        sc.frame_set(fr)
        d = {'pos': {n: P(n).copy() for n in ('Hips', 'Neck', 'Spine', 'Head', 'LeftHand', 'RightHand', 'LeftForeArm', 'RightForeArm', 'LeftArm', 'RightArm',
                                                'LeftUpLeg', 'RightUpLeg', 'LeftLeg', 'RightLeg', 'LeftFoot', 'RightFoot', 'LeftToeBase', 'RightToeBase')},
             'q': {n: arm.pose.bones[n].matrix_basis.to_quaternion().copy() for n in BODY}}
        fr_.append(d)
    n = len(fr_); out = dict(frames=n, dur=round((n - 1) / 30, 3))
    # feet
    feet = {}
    for s in ('Left', 'Right'):
        best = 0; tot = 0; worst_fr = None
        for jb in (s + 'Foot', s + 'ToeBase'):
            zs = [f['pos'][jb].z for f in fr_]; zmin = min(zs)
            for i in range(1, n):
                p0, p1 = fr_[i - 1]['pos'][jb], fr_[i]['pos'][jb]
                if p0.z < zmin + 0.04 and p1.z < zmin + 0.04 and abs(p1.z - p0.z) < 0.01:
                    dv = (p1 - p0); dv.z = 0
                    if dv.length > 0.004: tot += dv.length
                    if dv.length > best: best, worst_fr = dv.length, i
        feet[s] = dict(slide_total_m=round(tot, 3), max_step_m=round(best, 4), at=worst_fr)
    out['feet'] = feet
    # joint angles
    def chain(a_, b_, c_):
        angs = [ang(f['pos'][a_] - f['pos'][b_], f['pos'][c_] - f['pos'][b_]) for f in fr_]
        dd = [abs(angs[i] - angs[i - 1]) for i in range(1, n)]
        return dict(min=round(min(angs), 1), max=round(max(angs), 1), max_step=round(max(dd), 1), at=dd.index(max(dd)) + 1)
    out['knee'] = {s: chain(s + 'UpLeg', s + 'Leg', s + 'Foot') for s in ('Left', 'Right')}
    out['elbow'] = {s: chain(s + 'Arm', s + 'ForeArm', s + 'Hand') for s in ('Left', 'Right')}
    # wrist: hand local rotation step
    wr = {}
    for s in ('Left', 'Right'):
        st = [qang(fr_[i]['q'][s + 'Hand'].rotation_difference(fr_[i - 1]['q'][s + 'Hand'])) for i in range(1, n)]
        wr[s] = dict(max_step=round(max(st), 1), at=st.index(max(st)) + 1)
    out['wrist'] = wr
    # pops: second difference of local rotation
    pops = []
    for b in BODY:
        qs = [f['q'][b] for f in fr_]
        for i in range(1, n - 1):
            d1 = qs[i - 1].rotation_difference(qs[i]); d2 = qs[i].rotation_difference(qs[i + 1])
            acc = qang(d1.rotation_difference(d2))
            if acc > POP: pops.append((round(acc, 1), b, i))
    pops.sort(reverse=True); out['pops'] = pops[:8]; out['pop_count'] = len(pops)
    # hands in torso
    inside = []
    for i, f in enumerate(fr_):
        for s in ('Left', 'Right'):
            dd = seg_dist(f['pos'][s + 'Hand'], f['pos']['Hips'], f['pos']['Neck'])
            if dd < TORSO_R: inside.append((i, s, round(dd, 3)))
    out['hand_in_torso'] = inside[:10]; out['hand_in_torso_n'] = len(inside)
    hg = [(f['pos']['LeftHand'] - f['pos']['RightHand']).length for f in fr_]
    out['hand_gap_min'] = round(min(hg), 3); out['hand_gap_min_at'] = hg.index(min(hg))
    # start / end speed + seam
    def step(i, j): return max(qang(fr_[i]['q'][b].rotation_difference(fr_[j]['q'][b])) for b in BODY)
    typical = sorted(step(i - 1, i) for i in range(1, n))[n // 2]
    out['typ_step_deg'] = round(typical, 2)
    out['start_step_deg'] = round(step(0, 1), 2); out['end_step_deg'] = round(step(n - 2, n - 1), 2)
    if name in LOOPS:
        out['seam_deg'] = round(step(n - 1, 0), 2)
        hp = fr_[-1]['pos']['Hips'] - fr_[0]['pos']['Hips']; out['seam_hips_m'] = round(hp.length, 3)
    hz = [f['pos']['Hips'].z for f in fr_]
    out['hips_z'] = [round(min(hz), 3), round(max(hz), 3)]
    res[name] = out
    print('CRIT %-10s %s' % (name, json.dumps({k: v for k, v in out.items() if k not in ('pops', 'hand_in_torso')})))
    print('     pops', out['pops'][:5])
json.dump(res, open(OUT, 'w'), indent=1)
