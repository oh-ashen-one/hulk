# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
# Debug renders of the Brute skin: weight/dominant-bone colours + wireframe, close-ups (workbench, fast).
# usage: Blender -b --factory-startup -P tools/brute/mesh_viz.py -- <rig.glb> <out_prefix> [clip frame]
#   colours: arm chain red/orange, shoulder(clavicle) yellow, Spine2 blue, Spine/Spine1 cyan, Hips purple, Neck/Head green, legs grey
import bpy, sys, os, math
import numpy as np
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mesh_common as C
argv = sys.argv[sys.argv.index('--') + 1:]
RIG, PRE = argv[0], argv[1]
C.reset()
HASCLIP = len(argv) > 2 and not argv[2].startswith('--')
acts = C.load_anim_actions() if HASCLIP else {}
arm, me, objs = C.load_rig(RIG)
for o in objs:
    if o not in (arm, me): bpy.data.objects.remove(o)
C.rest_pose(arm)
W, names = C.weights(me)
if '--weights' in sys.argv:  # welded weight matrix from mesh_fix.py (*_weights_welded.npy)
    wid, _ = C.weld_map(C.rest_co(me)); W = np.load(sys.argv[sys.argv.index('--weights') + 1])[wid]
    C.set_weights(me, W, names)
pal = {}
for n in names:
    if n.endswith('Shoulder'): c = (1, .9, .1)
    elif n.endswith('ForeArm'): c = (1, .5, 0)
    elif n.endswith('Arm'): c = (.9, .05, .05)
    elif 'Hand' in n: c = (.6, .3, .1)
    elif n == 'Spine2': c = (.1, .2, 1)
    elif n in ('Spine', 'Spine1'): c = (0, .8, .9)
    elif n == 'Hips': c = (.6, .2, .8)
    elif n in ('Neck', 'Head'): c = (.1, .8, .2)
    else: c = (.5, .5, .5)
    pal[n] = np.array(c)
P = np.stack([pal[n] for n in names])
col = W @ P
d = me.data
attr = d.color_attributes.new('wcol', 'FLOAT_COLOR', 'POINT')
attr.data.foreach_set('color', np.concatenate([col, np.ones((len(col), 1))], 1).ravel())
sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'
sh = sc.display.shading; sh.light = 'STUDIO'; sh.color_type = 'VERTEX'; sh.show_object_outline = False
sc.render.resolution_x = 900; sc.render.resolution_y = 900
if HASCLIP:
    C.assign(arm, acts[argv[2]]); sc.frame_set(int(argv[3]))
mod = me.modifiers.new('wf', 'WIREFRAME'); mod.thickness = 0.0015; mod.use_replace = False; mod.use_even_offset = False
mod.material_offset = 1
mw = bpy.data.materials.new('wire'); mw.diffuse_color = (0, 0, 0, 1)
# workbench vertex colour applies to all; wire gets black via a second object instead
me.modifiers.remove(mod)
wire = me.copy(); wire.data = me.data.copy(); sc.collection.objects.link(wire)
wire.data.color_attributes['wcol'].data.foreach_set('color', np.tile([0.02, 0.02, 0.02, 1.0], len(col)))
wm = wire.modifiers.new('wf', 'WIREFRAME'); wm.thickness = 0.0012; wm.use_replace = True
wire.color = (0, 0, 0, 1)
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
cam.data.lens = 50
co = C.eval_co(me)
def b(n): return Vector((arm.matrix_world @ arm.pose.bones[n].head)[:])
SHOTS = {
    'front': (b('Spine1') + Vector((0, 0, 0.1)), Vector((1, 0, 0.1)), 1.6),
    'back': (b('Spine1') + Vector((0, 0, 0.1)), Vector((-1, 0, 0.1)), 1.6),
    'Rpit': ((b('RightArm') + b('RightForeArm')) / 2, Vector((0.6, -0.8, -0.1)), 0.9),
    'Rpit_front': ((b('RightArm') + b('RightForeArm')) / 2 + Vector((0, .1, 0)), Vector((1, 0, 0)), 0.8),
    'Rpit_back': ((b('RightArm') + b('RightForeArm')) / 2 + Vector((0, .1, 0)), Vector((-1, 0, 0)), 0.8),
    'Rside': ((b('RightArm') + b('RightForeArm')) / 2, Vector((0, -1, 0.1)), 1.0),
    'head': (b('Head') + Vector((0, 0, .1)), Vector((0.7, -0.7, 0.2)), 0.9),
    'headback': (b('Head') + Vector((0, 0, .1)), Vector((-0.7, 0.7, 0.3)), 0.9),
}
pb_ = arm.pose.bones['Hips']; Rh = (arm.matrix_world @ pb_.matrix @ arm.data.bones['Hips'].matrix_local.inverted()).to_3x3()
fw = Rh @ Vector((1, 0, 0)); fw.z = 0; fw.normalize(); lf = Vector((-fw.y, fw.x, 0))
up = (b('Spine2') + b('Neck')) / 2
SHOTS.update({'pf': (up, fw + Vector((0, 0, .3)), 1.5), 'pb': (up, -fw + Vector((0, 0, .3)), 1.5),
              'pR': (up, -lf + fw * .3 + Vector((0, 0, .2)), 1.5), 'pL': (up, lf + fw * .3 + Vector((0, 0, .2)), 1.5),
              'pRb': (up, -lf - fw * .6 + Vector((0, 0, .4)), 1.4), 'pLb': (up, lf - fw * .6 + Vector((0, 0, .4)), 1.4)})
sel = (sys.argv[sys.argv.index('--shots') + 1].split(',') if '--shots' in sys.argv else list(SHOTS))
for k in sel:
    tgt, dv, dist = SHOTS[k]
    cam.location = tgt + dv.normalized() * dist; cam.rotation_euler = (tgt - cam.location).to_track_quat('-Z', 'Y').to_euler()
    sh.color_type = 'VERTEX'; wire.color = (0, 0, 0, 1); sh.color_type = 'VERTEX'
    sc.render.filepath = '%s_%s.png' % (PRE, k); bpy.ops.render.render(write_still=True)
print('DONE')
