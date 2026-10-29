# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
# Synthetic "fit" for testing refine_brute.py / export_clip.py offline (no video, no reader, no spend): a shipped clip from an
# assembled brute.glb, retargeted ONTO the aligned rig (v2r_rig.py, the inverse of export_clip's transform) and keyed the way
# video2rig's import_motion.py keys a fit: an Action on the aligned armature, quaternion rotations + Hips location, linear keys at
# the clip's real times in the fit scene's frame rate (model.blend: 24 fps, start frame 1), so a 30 fps source lands on
# fractional frames 1 + k*0.8 exactly like a 30 fps video fit would.
#   Blender -b --factory-startup -P tools/brute/v2r/make_test_fit.py -- <aligned_model.blend COPY> <assembled brute.glb> <Clip> <out.blend>
#          [--spike BONE:SAMPLE:DEG ...]  inject a one-sample rotation spike (test for refine_brute's spike filter)
#          [--twist BONE:SAMPLE:DEG[:N]]  inject a persistent twist-branch switch: DEG about the bone's local Y (its length axis),
#                                         ramped over N samples (default 3) from SAMPLE, kept to the end (test for refine's burst pass)
#          [--hold SEC]                   append SEC seconds of the last pose (a still tail, test for refine_brute's trim)
#          [--cut N]                      drop the last N samples (opens a closed loop, test for refine_brute --loop)
# The aligned model.blend is opened and saved under a NEW name only; pass a copy anyway (the reader may be using the original).
import math
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v2r_rig as R  # noqa: E402

argv = sys.argv[sys.argv.index('--') + 1:]
MODEL, GLB, CLIP, OUT = argv[0], argv[1], argv[2], os.path.abspath(argv[3])
SPIKES = [x.split(':') for i, x in enumerate(argv) if i > 0 and argv[i - 1] == '--spike']
TWISTS = [x.split(':') for i, x in enumerate(argv) if i > 0 and argv[i - 1] == '--twist']
HOLD = float(argv[argv.index('--hold') + 1]) if '--hold' in argv else 0.0
CUT = int(argv[argv.index('--cut') + 1]) if '--cut' in argv else 0
assert os.path.abspath(MODEL) != os.path.abspath(R.ALIGNED_BLEND), 'pass a COPY of the aligned model.blend'
assert OUT != os.path.abspath(MODEL), 'refusing to overwrite the input'
SRC_FPS = 30

bpy.ops.wm.open_mainfile(filepath=os.path.abspath(MODEL), load_ui=False)
sc = bpy.context.scene
fit_fps = sc.render.fps / sc.render.fps_base
fstart = sc.frame_start
al = next(o for o in sc.objects if o.type == 'ARMATURE')
keep = set(bpy.data.objects)
sc.render.fps, sc.render.fps_base = SRC_FPS, 1.0           # the assembled glb is 30 fps: its keys land on integer frames
objs = R.import_glb(GLB)
sh = next(o for o in objs if o.type == 'ARMATURE')
act = bpy.data.actions[CLIP] if CLIP in bpy.data.actions else next(a for a in bpy.data.actions if a.name.split('.')[0] == CLIP)
for t in list(sh.animation_data.nla_tracks):
    sh.animation_data.nla_tracks.remove(t)
R.assign_action(sh, act)
ok, lines = R.check_match(sh, al, 1e-4)
print('TESTFIT rig check', ok, lines)
assert ok
k0, k1 = R.key_range(act)
frames = list(range(int(round(k0)), int(round(k1)) + 1))
R_sh, R_al, PAR_al = R.rest(sh), R.rest(al), R.parents(al)
bases = []
for f in frames:
    R.set_frame(f)
    bases.append(R.retarget_basis(R.sample_pose(sh), R_sh, R_al, PAR_al))
from mathutils import Matrix  # noqa: E402
for bn, k, deg in SPIKES:
    k = int(k)
    bases[k][bn] = bases[k][bn] @ Matrix.Rotation(math.radians(float(deg)), 4, 'X')
    print('TESTFIT injected spike: %s sample %d %+.1f deg about its local X' % (bn, k, float(deg)))
for tw in TWISTS:
    bn, k, deg = tw[0], int(tw[1]), float(tw[2]); n = int(tw[3]) if len(tw) > 3 else 3
    for j in range(k, len(bases)):
        f = min(1.0, (j - k + 1) / n)
        bases[j][bn] = bases[j][bn] @ Matrix.Rotation(math.radians(deg * f), 4, 'Y')
    print('TESTFIT injected twist switch: %s from sample %d, %+.1f deg about its local Y over %d samples, kept to the end' % (bn, k, deg, n))
if CUT > 0:
    bases, frames = bases[:-CUT], frames[:-CUT]
    print('TESTFIT dropped the last %d samples (open loop)' % CUT)
if HOLD > 0:
    nh = int(round(HOLD * SRC_FPS))
    bases += [dict(bases[-1]) for _ in range(nh)]
    frames += list(range(frames[-1] + 1, frames[-1] + 1 + nh))
    print('TESTFIT appended a still tail: %d samples (%.2f s)' % (nh, HOLD))
for o in objs:
    bpy.data.objects.remove(o)
for a in [a for a in bpy.data.actions]:
    bpy.data.actions.remove(a)
sc.render.fps, sc.render.fps_base = int(fit_fps), 1.0
fit = bpy.data.actions.new(CLIP + '_testfit')
fit.use_fake_user = True
times = [(f - frames[0]) / SRC_FPS for f in frames]
keys = [fstart + t * fit_fps for t in times]
loc = R.write_basis_frames(al, fit, keys, bases)
sc.frame_end = max(sc.frame_end, int(keys[-1]) + 1)
print('TESTFIT %s: %d frames of %s (%.3f s at %d fps) -> aligned rig keys %.2f..%.2f at %g fps; location keys on %s' % (
    CLIP, len(frames), os.path.basename(GLB), times[-1], SRC_FPS, keys[0], keys[-1], fit_fps, loc))
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print('TESTFIT saved', OUT)
