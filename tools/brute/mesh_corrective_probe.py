# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
# Probe for the corrective-shape pass: arm elevation (upper arm vs torso-down) per clip frame, bind pose values, mesh stats.
# usage: Blender -b --factory-startup -P tools/brute/mesh_corrective_probe.py -- <rig.glb>
import bpy, sys, os, json, math
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mesh_common as C
from mesh_corrective_lib import elevation

argv = sys.argv[sys.argv.index('--') + 1:]
RIG = argv[0]
C.reset()
acts = C.load_anim_actions()
arm, me, objs = C.load_rig(RIG)
C.rest_pose(arm); bpy.context.view_layer.update()
print('VERTS', len(me.data.vertices), 'shape keys', me.data.shape_keys)
print('BIND elev L %.1f R %.1f' % (elevation(arm, 'Left'), elevation(arm, 'Right')))
sc = bpy.context.scene
out = {}
for clip, a in sorted(acts.items()):
    C.assign(arm, a); f0, f1 = int(a.frame_range[0]), int(a.frame_range[1])
    rows = []
    for f in range(f0, f1 + 1):
        sc.frame_set(f); rows.append((f, round(elevation(arm, 'Left'), 1), round(elevation(arm, 'Right'), 1)))
    out[clip] = rows
    L = [r[1] for r in rows]; R = [r[2] for r in rows]
    print('%-10s f%d-%d  L %.0f..%.0f  R %.0f..%.0f  frames>120 L %d R %d' % (clip, f0, f1, min(L), max(L), min(R), max(R),
          sum(x > 120 for x in L), sum(x > 120 for x in R)))
os.makedirs(os.path.expanduser('~/hulk-scratch/brute_corr'), exist_ok=True)
json.dump(out, open(os.path.expanduser('~/hulk-scratch/brute_corr/elevations_probe.json'), 'w'))
