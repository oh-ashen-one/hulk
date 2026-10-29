# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
# Shared pieces of the blind A/B harness (ab_render.py, ab_measure.py, ab_pair.py): the fixed camera table, subject loading,
# frame sampling. Runs inside Blender. Nothing here ever knows which subject is "old" or "new".
#
# SUBJECT = <file.glb>[:<Action>]  a glb on the SHIPPED Brute rig (the 52 Mixamo-named bones, brute_v5 mesh bind):
#     * the brute_v5 glb (one Action per clip, name = clip name):                 ~/hulk-scratch/brute_v5/brute.glb:Idle
#     * a motion glb written by export_clip.py (one Action, name optional):       work-tools/motion_refined/Brute_v2r_idle.glb
#     * any assembled brute.glb with several Actions (name required).
# Every subject is rendered on the SAME character: the brute_v5 mesh (game height, corrective shape keys as exported, same
# bind), driven by the subject's Action. A motion glb carries an unscaled rig, so its location keys are multiplied by
# (its armature scale / base armature scale), exactly as assemble_motion.py does (ks), and the old and new clip differ only
# in the Action. That is the only way the pair can differ in pixels.
import json
import os
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector
from bpy_extras.object_utils import world_to_camera_view

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v2r_rig as R  # noqa: E402

BASE_GLB = '/Users/midir/hulk-scratch/brute_v5/brute.glb'
CLIPS_META = '/Users/midir/hulk-scratch/brute_v5/clips_meta.json'
FPS = 24                       # every video is 24 fps; Action keys of the glb import sit on the 24 fps scene grid
RES = (854, 480)
AIR_CLIPS = ('Jump', 'Fall', 'WallAttach', 'WallClimb')   # BruteCharacter.cpp keeps these off the per-frame foot grounding
FOOT_BONES = ('LeftFoot', 'LeftToeBase', 'RightFoot', 'RightToeBase')
CONTACT_M = 0.02               # a foot counts as grounded within 2 cm of its floor
CONTACT_PATCH_M = 0.01         # contact point = centroid of the foot vertices within 1 cm of the foot's lowest vertex

# ---------------------------------------------------------------------------------------------------- the fixed cameras
# One table for every subject (never rescaled per clip). Units: metres. The character stands at the origin on z = 0 and faces
# FACING (world XY, unit); a camera sits `yaw` degrees counter-clockwise (seen from above) from the facing direction, DIST
# metres away horizontally, HEIGHT above the floor, looking at the point (0, 0, TARGET_Z). 50 mm lens on a 36 mm sensor,
# 854 x 480: the frame covers z = -0.55 .. 3.9 m at the character's distance (a 2.6 m brute, hands overhead for Smash / Lift /
# Uppercut reach ~3.5 m, 0.4 m to spare) and +-4.4 m sideways (arm spread of Clap / Slap fits).
FACING = (0.0, -1.0)           # brute_v5 / shipped rig: he faces -Y (checked at load, see check_facing)
CAMERAS = {                    # name: yaw degrees from his facing direction (0 = in front of him, 90 = on his LEFT side)
    'front': 0.0,
    'left': 90.0,
    'threequarter': 45.0,
}
DIST = 10.8
HEIGHT = 3.4
TARGET_Z = 1.75
LENS_MM = 50.0
SENSOR_MM = 36.0
CAM_ORDER = ['front', 'left', 'threequarter']


def facing_vec():
    return np.array([FACING[0], FACING[1], 0.0])


def cam_location(name, root_xy=(0.0, 0.0)):
    a = np.radians(CAMERAS[name])
    f = facing_vec()
    d = np.array([f[0] * np.cos(a) - f[1] * np.sin(a), f[0] * np.sin(a) + f[1] * np.cos(a), 0.0])
    return Vector((d[0] * DIST + root_xy[0], d[1] * DIST + root_xy[1], HEIGHT))


def make_camera(scene, name, root_xy=(0.0, 0.0)):
    """camera object `name` for the fixed table, aimed at the character's origin column"""
    cam = bpy.data.cameras.new('cam_' + name)
    cam.lens, cam.sensor_width, cam.sensor_fit = LENS_MM, SENSOR_MM, 'HORIZONTAL'
    cam.clip_start, cam.clip_end = 0.5, 200.0
    ob = bpy.data.objects.new('cam_' + name, cam)
    scene.collection.objects.link(ob)
    aim_camera(ob, name, root_xy)
    return ob


def aim_camera(ob, name, root_xy=(0.0, 0.0)):
    loc = cam_location(name, root_xy)
    tgt = Vector((root_xy[0], root_xy[1], TARGET_Z))
    ob.location = loc
    ob.rotation_euler = (tgt - loc).to_track_quat('-Z', 'Y').to_euler()


def project_px(scene, cam_ob, p):
    """world point -> (x, y) pixels of the render, y down"""
    v = world_to_camera_view(scene, cam_ob, Vector(p))
    return np.array([v.x * RES[0], (1.0 - v.y) * RES[1]])


# ---------------------------------------------------------------------------------------------------- subjects
def parse_subject(spec):
    """'<file.glb>[:<Action>]' -> (path, action or None)"""
    path, _, act = spec.partition('.glb:')
    if act:
        return os.path.abspath(os.path.expanduser(path + '.glb')), act
    return os.path.abspath(os.path.expanduser(spec)), None


def clip_is_loop(clip):
    try:
        return bool(json.load(open(CLIPS_META))[clip]['loop'])
    except Exception:  # noqa
        return clip in ('Idle', 'Walk', 'Run', 'WallClimb', 'Fall')


def _find_action(name):
    for a in bpy.data.actions:
        if a.name == name:
            return a
    for a in bpy.data.actions:
        if a.name.split('.')[0] == name:
            return a
    raise SystemExit('ab: action %r not found (have %s)' % (name, [a.name for a in bpy.data.actions]))


def _helpers_off(objs):
    for o in list(objs):
        if o.type == 'MESH' and o.name.lower().startswith(('icosphere', 'sphere', 'plane', 'cube')):
            objs.remove(o)
            bpy.data.objects.remove(o)
    return objs


class Base:
    """the brute_v5 character in an empty scene: .arm .mesh, Actions all removed, NLA and shape-key animation cleared"""

    def __init__(self, base_glb=BASE_GLB):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.scene = bpy.context.scene
        self.scene.render.fps, self.scene.render.fps_base = FPS, 1.0
        self.path = os.path.abspath(base_glb)
        objs = _helpers_off(R.import_glb(self.path))
        self.arm = next(o for o in objs if o.type == 'ARMATURE')
        self.mesh = max((o for o in objs if o.type == 'MESH'), key=lambda o: len(o.data.vertices))
        self.base_actions = {a.name: a for a in bpy.data.actions}
        self.scale = self.arm.matrix_world.to_scale().x
        self.arm_loc0 = self.arm.location.copy()
        self.shape_keys = [k.name for k in self.mesh.data.shape_keys.key_blocks] if self.mesh.data.shape_keys else []
        for o in (self.arm, self.mesh):
            if o.animation_data:
                o.animation_data_clear()
        if self.mesh.data.shape_keys and self.mesh.data.shape_keys.animation_data:
            self.mesh.data.shape_keys.animation_data_clear()
        self.rest_pose()
        self.sets = None
        # the bind pose stands with its soles on the floor: drop the whole character so that floor is z = 0
        bpy.context.view_layer.update()
        self.arm.location.z -= float(R.mesh_world(self.mesh)[:, 2].min())
        self.arm_loc0 = self.arm.location.copy()
        bpy.context.view_layer.update()
        self.rest_hips = hips_xy(self)
        self.rest_foot_z = self.foot_bone_z()

    def foot_bone_z(self):
        m = self.arm.matrix_world
        return min((m @ self.arm.pose.bones[n].head).z for n in FOOT_BONES)

    def rest_pose(self):
        for pb in self.arm.pose.bones:
            pb.rotation_mode = 'QUATERNION'
            pb.matrix_basis = Matrix.Identity(4)

    def import_action(self, spec):
        """-> bpy Action (a copy owned by this scene) on the base rig, location keys rescaled (ks), plus info dict"""
        path, name = parse_subject(spec)
        if path == self.path:
            if not name:
                raise SystemExit('ab: %s is the base glb, give :<Action>' % spec)
            act, ks = _find_action(name).copy(), 1.0
        else:
            before = set(bpy.data.actions)
            objs = R.import_glb(path)
            src = next(o for o in objs if o.type == 'ARMATURE')
            new = [a for a in bpy.data.actions if a not in before]
            if name:
                src_act = next((a for a in new if a.name == name or a.name.split('.')[0] == name), None)
            else:
                src_act = src.animation_data.action if src.animation_data and src.animation_data.action else (new[0] if len(new) == 1 else None)
            if src_act is None:
                raise SystemExit('ab: %s: cannot pick an action from %s (give :<Action>)' % (path, [a.name for a in new]))
            ks = src.matrix_world.to_scale().x / self.scale
            act = src_act.copy()
            for o in objs:
                bpy.data.objects.remove(o)
            for a in new:
                if a.users == 0:
                    bpy.data.actions.remove(a)
        if abs(ks - 1.0) > 1e-3:   # motion translation units, as assemble_motion.py does
            for fc in R.action_fcurves(act):
                if fc.data_path.endswith('.location'):
                    for kp in fc.keyframe_points:
                        kp.co.y *= ks
                        kp.handle_left.y *= ks
                        kp.handle_right.y *= ks
        act.name = 'ab_subject'
        return act, dict(source_scale_ratio=ks)

    def play(self, act):
        self.arm.animation_data_clear()
        R.assign_action(self.arm, act)
        self.arm.location = self.arm_loc0

    # --- vertex groups -> foot vertex sets (dominant influence), cached
    def foot_sets(self):
        if self.sets is None:
            me = self.mesh.data
            names = {g.index: g.name for g in self.mesh.vertex_groups}
            want = {'L': ('LeftFoot', 'LeftToeBase'), 'R': ('RightFoot', 'RightToeBase')}
            idx = {'L': [], 'R': []}
            for v in me.vertices:
                if not v.groups:
                    continue
                g = max(v.groups, key=lambda x: x.weight)
                nm = names.get(g.group)
                for k, ws in want.items():
                    if nm in ws:
                        idx[k].append(v.index)
            self.sets = {k: np.array(v, dtype=np.int64) for k, v in idx.items()}
        return self.sets


def sample_times(act, loop):
    """24 fps sample times in scene frames over the Action's key range. One-shots get a last sample at the exact end."""
    k0, k1 = R.key_range(act)
    n = int(np.floor(k1 - k0 + 1e-6)) + 1
    t = [k0 + i for i in range(n)]
    if not loop and k1 - t[-1] > 0.25:
        t.append(k1)
    return t


def hips_xy(base):
    h = base.arm.matrix_world @ base.arm.pose.bones['Hips'].head
    return np.array([h.x, h.y])


def check_facing(base, tol_deg=25.0):
    """warn when the character's toes point away from FACING at frame 0 of the playing action"""
    pbs = base.arm.pose.bones
    m = base.arm.matrix_world
    v = np.array([(m @ pbs['LeftToeBase'].head - m @ pbs['LeftFoot'].head)[i] for i in range(2)])
    v += np.array([(m @ pbs['RightToeBase'].head - m @ pbs['RightFoot'].head)[i] for i in range(2)])
    n = np.linalg.norm(v)
    if n < 1e-6:
        return None
    ang = np.degrees(np.arccos(np.clip(v @ np.array(FACING) / n, -1, 1)))
    return float(ang)


def mesh_world_np(base, sel=None):
    co = R.mesh_world(base.mesh)
    return co if sel is None else co[sel]


def pose_frame(base, t, mode='game', grounding='frame', first_dz=None):
    """Evaluate the playing Action at scene frame t and place the character the way BruteCharacter.cpp does.
    mode 'game': Hips XY pinned to the rest pose (the sim moves him; the clip's own travel is dropped), and for ground clips
                 (grounding 'frame') the lowest foot bone is put back on its rest height every frame; grounding 'first' applies
                 the first sample's correction to every frame (air clips: the hop / launch keeps its height); 'none' = no z fix.
    mode 'raw':  the Action as exported (only the constant rest alignment of Base).
    Returns (dx, dy, dz) applied to the armature object."""
    base.arm.location = base.arm_loc0
    R.set_frame(t)
    if mode == 'raw':
        return (0.0, 0.0, 0.0)
    h = hips_xy(base)
    dx, dy = base.rest_hips[0] - h[0], base.rest_hips[1] - h[1]
    dz = 0.0
    if grounding == 'frame':
        dz = base.rest_foot_z - base.foot_bone_z()
    elif grounding == 'first' and first_dz is not None:
        dz = first_dz
    base.arm.location = base.arm_loc0 + Vector((dx, dy, dz))
    bpy.context.view_layer.update()
    return (dx, dy, dz)


def grounding_for(clip):
    return 'first' if clip in AIR_CLIPS else 'frame'


def first_dz(base, times, mode):
    """z correction of the first sample (for grounding 'first')"""
    if mode == 'raw':
        return 0.0
    base.arm.location = base.arm_loc0
    R.set_frame(times[0])
    return base.rest_foot_z - base.foot_bone_z()
