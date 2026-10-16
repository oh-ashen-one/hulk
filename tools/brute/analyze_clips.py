# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
# Reads the assembled brute_anim.fbx (tools/brute/assemble_motion.py) and writes the clip timing markers the game needs
# (unreal/WebHomage/Config/BruteAnim.json): body forward axis, foot stride speed of the loops, jump charge / launch / apex /
# touchdown times, wall-attach fist impact time. Everything is measured from bone world positions, never hand-typed.
# usage: Blender -b --factory-startup -P tools/brute/analyze_clips.py -- <brute_anim.fbx> <out.json>
import bpy, sys, json
from mathutils import Vector

FBX, OUT = sys.argv[sys.argv.index('--') + 1:][:2]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=FBX)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
sc = bpy.context.scene
FPS = 30.0
sc.render.fps = 30


def P(name):
    return arm.matrix_world @ arm.pose.bones[name].head


def sample(act):
    arm.animation_data_create()
    arm.animation_data.action = act
    if hasattr(arm.animation_data, 'action_slot') and act.slots:
        arm.animation_data.action_slot = act.slots[0]
    f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
    rows = []
    for f in range(f0, f1 + 1):
        sc.frame_set(f)
        rows.append({k: P(k).copy() for k in ('Hips', 'LeftHand', 'RightHand', 'LeftFoot', 'RightFoot', 'LeftToeBase', 'RightToeBase', 'Head')})
    return rows


acts = {a.name.split('|')[-1]: a for a in bpy.data.actions}
out = {'fps': FPS, 'clips': {}}
# forward = toes ahead of ankles in the rest-ish first idle frame
idle = sample(acts['Idle'])
fw = ((idle[0]['LeftToeBase'] - idle[0]['LeftFoot']) + (idle[0]['RightToeBase'] - idle[0]['RightFoot']))
fw.z = 0; fw.normalize()
out['forward'] = [round(fw.x, 4), round(fw.y, 4), 0.0]
rest_hips = idle[0]['Hips'].z
out['hips_z'] = round(rest_hips, 4)
print('FORWARD', fw, 'hips', rest_hips)

for name, act in acts.items():
    rows = sample(act)
    n = len(rows); dur = (n - 1) / FPS
    c = {'dur': round(dur, 4)}
    hz = [r['Hips'].z for r in rows]
    if name in ('Walk', 'Run', 'Idle', 'StopLunge'):
        # stride speed: the lower foot's backward speed along forward (in-place clips: the planted foot slides back at the body speed)
        sp = []
        for i in range(1, n):
            a, b = rows[i - 1], rows[i]
            low = 'LeftFoot' if b['LeftFoot'].z < b['RightFoot'].z else 'RightFoot'
            sp.append(-(b[low] - a[low]).dot(fw) * FPS)
        sp.sort()
        c['stride_speed'] = round(sp[len(sp) // 2], 4) if sp else 0.0
    if name == 'Jump':
        # frame 0 is the bind pose and the last frames settle oddly: search inside [5, n-10]
        vz = [(hz[i + 1] - hz[i]) * FPS for i in range(n - 1)]
        launch = max(range(5, n - 10), key=lambda i: vz[i])                   # fastest rise
        lo = min(range(5, launch + 1), key=lambda i: hz[i])                  # deepest crouch before it
        start = 5
        apex = max(range(launch, n - 10), key=lambda i: hz[i])
        touch = min(range(apex, n - 3), key=lambda i: hz[i])                 # lowest point after the apex
        c.update(crouch_start=round(start / FPS, 4), crouch_low=round(lo / FPS, 4), launch=round(launch / FPS, 4),
                 apex=round(apex / FPS, 4), touchdown=round(touch / FPS, 4), crouch_depth=round(hz[5] - hz[lo], 4))
    if name in ('WallAttach', 'WallClimb'):
        # fists in = hands at their highest, both above the head
        hh = [min(r['LeftHand'].z, r['RightHand'].z) - r['Head'].z for r in rows]
        imp = max(range(n), key=lambda i: hh[i])
        first = next((i for i in range(n) if hh[i] > hh[imp] - 0.08), imp)  # first moment the fists reach (nearly) full height
        reach = max(0, first - int(0.5 * FPS))
        c.update(impact=round(first / FPS, 4), reach=round(reach / FPS, 4), hands_hi=round(hh[imp], 4))
    c['hips_min'] = round(min(hz) - rest_hips, 4); c['hips_max'] = round(max(hz) - rest_hips, 4)
    out['clips'][name] = c
    print('CLIP', name, c)

json.dump(out, open(OUT, 'w'), indent=1)
print('WROTE', OUT)
