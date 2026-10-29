# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
# Test helper for run_clip.sh (see TESTS-runclip.md): a synthetic fit .blend (make_test_fit.py) -> a motion .npz in the format of
# video2rig's `out/<clip>.npz` (times, bones, root, quaternions, root_location, armature_world, props), so import_motion.py can be run
# for real without a reader. The fit's Action is sampled at 30 fps over the Action's frame range (the grid the synthetic fit was keyed on).
#   Blender -b --factory-startup -P tools/brute/v2r/make_test_npz.py -- <fit.blend> <out.npz> [--fps 30]
import os
import sys

import bpy
import numpy as np

argv = sys.argv[sys.argv.index('--') + 1:]
SRC, OUT = os.path.abspath(argv[0]), os.path.abspath(argv[1])
FPS = float(argv[argv.index('--fps') + 1]) if '--fps' in argv else 30.0
assert SRC != OUT
bpy.ops.wm.open_mainfile(filepath=SRC, load_ui=False)
sc = bpy.context.scene
arm = next(o for o in sc.objects if o.type == 'ARMATURE')
fps_scene = sc.render.fps / sc.render.fps_base
fr = arm.animation_data.action.frame_range
f0, f1 = float(fr[0]), float(fr[1])
step = fps_scene / FPS
n = int(round((f1 - f0) / step)) + 1
bones = [b.name for b in arm.pose.bones]
root = next(b.name for b in arm.pose.bones if b.parent is None) if 'Hips' not in bones else 'Hips'
Q = np.zeros((n, len(bones), 4))
L = np.zeros((n, 3))
for k in range(n):
    f = f0 + k * step
    sc.frame_set(int(np.floor(f)), subframe=float(f - np.floor(f)))
    for j, name in enumerate(bones):
        pb = arm.pose.bones[name]
        Q[k, j] = pb.rotation_quaternion[:]
    L[k] = arm.pose.bones[root].location[:]
np.savez(OUT, times=np.arange(n) / FPS, bones=np.array(bones), root=np.array(root), quaternions=Q, root_location=L,
         armature_world=np.array(arm.matrix_world), props=np.array([], dtype='<U1'))
print('TESTNPZ wrote %s: %d frames at %g fps, %d bones, root %s' % (OUT, n, FPS, len(bones), root))
