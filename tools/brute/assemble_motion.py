# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
# Brute clips from Cartwheel AI motion (generated on Customuse for the auto-rigged Emerald Behemoth), cleaned up in Blender:
#   - every motion FBX is imported, its action copied onto ONE armature (the rigged model, same 52-bone skeleton)
#   - root (pelvis) forward travel is removed for in-place clips and its speed measured (for the game's speed matching)
#   - looping clips get a seamless loop: the last 0.25 s cross-fade into the first frames
#   - the model is scaled to the game height (2.6 m), feet on the ground
# Writes <out>/brute.glb (+ brute_anim.fbx) with the CLIPS below (locomotion/wall + combat/air) and clips.json (once/loop, hit times).
# usage: Blender -b --factory-startup -P tools/brute/assemble_motion.py -- <rigged.fbx> <motion_dir> <out_dir>
#   motion_dir holds the downloaded FBX files; the clip is found by keyword in the file name (idle, walk, run, stop, climb, jump, fall, land)
import bpy, sys, os, json, math, glob, re
from mathutils import Vector, Quaternion

argv = sys.argv[sys.argv.index('--') + 1:]
RIG, MDIR, OUT = argv[0], argv[1], argv[2]
HEIGHT = float(os.environ.get('BRUTE_HEIGHT_M', '2.6'))
os.makedirs(OUT, exist_ok=True)
CLIPS = [('Idle', r'idle', True), ('Walk', r'walk', True), ('Run', r'(?<!sk)run(?!.*stop)', True), ('StopLunge', r'stoplunge', False),
         ('Jump', r'_jump', False), ('WallAttach', r'attach', False), ('WallClimb', r'climb|attach', True),
         # 2026-10-16 combat + air clips (Meshy Text-to-Motion raw SMPL clips -> retarget_motion.py; files Brute_<name>.glb)
         ('PunchL', r'brute_punchl', False), ('PunchR', r'brute_punchr', False), ('Slap', r'brute_slap', False), ('Clap', r'brute_clap', False),
         ('Smash', r'brute_smash', False), ('Lift', r'brute_liftthrow', False), ('Throw', r'brute_liftthrow', False),
         ('Uppercut', r'brute_uppercut', False), ('Fall', r'brute_fall', True), ('Land', r'brute_land', False)]
INPLACE = {'Walk', 'Run', 'StopLunge', 'PunchL', 'PunchR', 'Slap', 'Clap', 'Smash', 'Lift', 'Throw', 'Uppercut', 'Fall', 'Land'}
# keep only [a, b] frames (offsets from the clip's first frame), re-based to the first frame: Lift / Throw are the two halves of one
# lift-hold-hurl take (Throw starts exactly on Lift's overhead hold); punches / clap drop a messy generated tail
TRIM = {'PunchL': (0, 46), 'PunchR': (0, 46), 'Clap': (0, 62), 'Lift': (19, 109), 'Throw': (109, 174)}
# contact moment (seconds from the clip start, after TRIM): fist / palm / ground contact, measured from hand telemetry
HIT = {'PunchL': 1.0, 'PunchR': 1.0, 'Slap': 0.83, 'Clap': 0.8, 'Smash': 1.17, 'Uppercut': 0.6, 'Throw': 1.0, 'Land': 0.5}

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.render.fps = 30
def bags(act):
    """F-curve containers of an action (Blender 5 layered actions: layers -> strips -> channelbags; older: the action itself)"""
    if hasattr(act, 'layers'):
        return [cb for L in act.layers for st in L.strips for cb in st.channelbags]
    return [act]
def assign(act):
    arm.animation_data_create(); arm.animation_data.action = act
    if hasattr(act, 'slots') and len(act.slots) and hasattr(arm.animation_data, 'action_slot'):
        try: arm.animation_data.action_slot = act.slots[0]
        except Exception as ex: print('slot assign failed', ex)
def fcs(act): return [fc for b in bags(act) for fc in b.fcurves]
def remove_fc(act, fc):
    for b in bags(act):
        if fc in list(b.fcurves): b.fcurves.remove(fc); return
def find_fc(act, path, index):
    return next((fc for fc in fcs(act) if fc.data_path == path and fc.array_index == index), None)
def imp(f):
    before = set(bpy.data.objects)
    if f.lower().endswith('.fbx'): bpy.ops.import_scene.fbx(filepath=f, ignore_leaf_bones=False, automatic_bone_orientation=False)
    else: bpy.ops.import_scene.gltf(filepath=f)
    return [o for o in bpy.data.objects if o not in before]
main = imp(RIG)
for o in [o for o in main if o.type == 'MESH' and re.match(r'(icosphere|sphere|plane|cube)', o.name.lower())]: main.remove(o); bpy.data.objects.remove(o)
arm = next(o for o in main if o.type == 'ARMATURE')
meshes = [o for o in main if o.type == 'MESH']
for a in list(bpy.data.actions): bpy.data.actions.remove(a)
if arm.animation_data: arm.animation_data_clear()
for pb in arm.pose.bones: pb.rotation_mode = 'QUATERNION'; pb.rotation_quaternion = Quaternion(); pb.location = Vector(); pb.scale = Vector((1, 1, 1))
bones = set(b.name for b in arm.data.bones)

files = sorted(glob.glob(os.path.join(MDIR, '**', '*.fbx'), recursive=True) + glob.glob(os.path.join(MDIR, '**', '*.glb'), recursive=True))
print('MOTION FILES', [os.path.basename(f) for f in files])
clips, meta = {}, {}
for name, pat, loop in CLIPS:
    # owner 2026-10-15: no separate climb clip; WallClimb reuses the WallAttach slam (fists into the wall) as the climb step
    f = next((x for x in files if re.search(pat.split('|')[0], os.path.basename(x).lower())), None) or next((x for x in files if re.search(pat, os.path.basename(x).lower())), None)
    if not f: print('MISSING clip', name); continue
    objs = imp(f)
    src = next((o for o in objs if o.type == 'ARMATURE'), None)
    act = src.animation_data.action if src and src.animation_data else None
    if not act:
        acts = [a for a in bpy.data.actions if a.users and a not in clips.values()]
        act = acts[-1] if acts else None
    if not act: print('NO ACTION in', f); [bpy.data.objects.remove(o) for o in objs]; continue
    # keep only channels of bones the rig has
    srcb = set(b.name for b in src.data.bones) if src else bones
    miss = sorted(bones - srcb)
    if miss: print('WARN', name, 'bones missing in motion', miss[:10])
    act = act.copy(); act.name = name
    for fc in list(fcs(act)):
        m = re.match(r'pose\.bones\["(.+?)"\]', fc.data_path)
        if m and m.group(1) not in bones: remove_fc(act, fc)
    if name in TRIM:
        fa = int(round(act.frame_range[0])); ta, tb = TRIM[name]
        for fc in fcs(act):
            pts = fc.keyframe_points
            for idx in range(len(pts) - 1, -1, -1):
                if not (fa + ta - 0.01 <= pts[idx].co.x <= fa + tb + 0.01): pts.remove(pts[idx])
            for kp in pts: kp.co.x -= ta; kp.handle_left.x -= ta; kp.handle_right.x -= ta
            fc.update()
        act.frame_range = (fa, fa + tb - ta); act.use_frame_range = True
        print('TRIM', name, 'frames', fa + ta, '..', fa + tb, '-> start', fa)
    # source armature scale vs ours (motion translation units)
    ks = (src.matrix_world.to_scale().x / arm.matrix_world.to_scale().x) if src else 1.0
    if abs(ks - 1.0) > 1e-3:
        for fc in fcs(act):
            if fc.data_path.endswith('.location'):
                for kp in fc.keyframe_points: kp.co.y *= ks; kp.handle_left.y *= ks; kp.handle_right.y *= ks
    for o in objs: bpy.data.objects.remove(o)
    clips[name] = act; meta[name] = dict(loop=loop, src=os.path.basename(f))

# ---- pelvis travel: measure speed, remove horizontal drift for in-place clips (the game moves the capsule)
root = next((r for r in ('Hips', 'pelvis', 'hips', 'Pelvis') if r in bones), arm.data.bones[0].name)
for name, act in clips.items():
    assign(act)
    f0, f1 = (int(x) for x in act.frame_range)
    sc = bpy.context.scene
    sc.frame_set(f0); p0 = (arm.matrix_world @ arm.pose.bones[root].head).copy()
    sc.frame_set(f1); p1 = (arm.matrix_world @ arm.pose.bones[root].head).copy()
    d = p1 - p0; d.z = 0; T = max(1e-3, (f1 - f0) / sc.render.fps)
    meta[name].update(speed=round(d.length / T, 3), dur=round(T, 3))
    if name in ('WallAttach', 'WallClimb'):
        # where his hands end up (forward of the start): the viewer puts its test wall there
        hb = [b for b in ('LeftHand', 'RightHand', 'left_wrist', 'right_wrist') if b in bones]
        sc.frame_set(f1); fwd = max(((arm.matrix_world @ arm.pose.bones[b].head) - p0).dot(Vector((0, -1, 0))) for b in hb) if hb else 0.8
        meta[name]['wall_fwd'] = round(fwd, 3)
    if name in ('Walk', 'Run') and meta[name]['speed'] < 0.3:
        # generated in place: the ground speed is how fast a planted foot slides backwards
        feet = [b for b in ('LeftFoot', 'RightFoot', 'left_ankle', 'right_ankle', 'LeftToeBase', 'RightToeBase') if b in bones][:2]
        vs = []
        for fb in feet:
            pts = []
            for fr in range(f0, f1 + 1):
                sc.frame_set(fr); pts.append((arm.matrix_world @ arm.pose.bones[fb].head).copy())
            zmin = min(p.z for p in pts)
            for i in range(1, len(pts)):
                if pts[i].z < zmin + 0.04 and pts[i - 1].z < zmin + 0.04:
                    v = pts[i] - pts[i - 1]; v.z = 0; vs.append(v.length * sc.render.fps)
        if vs:
            vs.sort(); meta[name]['speed'] = round(vs[len(vs) // 2], 3); meta[name]['speed_from'] = 'planted foot'

    if name == 'StopLunge':
        # end on the deepest coil (it leads straight into Jump); the generated tail stands up and throws the head back
        zs_ = []
        for fr in range(f0, f1 + 1):
            sc.frame_set(fr); zs_.append((arm.matrix_world @ arm.pose.bones[root].head).z)
        lo = f0 + min(range(len(zs_)), key=lambda i: zs_[i])
        for fc in fcs(act):
            for idx in range(len(fc.keyframe_points) - 1, -1, -1):
                if fc.keyframe_points[idx].co.x > lo + 2: fc.keyframe_points.remove(fc.keyframe_points[idx])
            fc.update()
        act.frame_range = (f0, lo + 2); act.use_frame_range = True
        f1 = lo + 2; T = (f1 - f0) / sc.render.fps; meta[name]['dur'] = round(T, 3)
        print('TRIM StopLunge at frame', lo)
    if name in INPLACE:
        # in place: take the root's horizontal path out FRAME BY FRAME (a sprint-then-stop is not a straight line). Loops keep their
        # in-stride sway (only a 1 s moving average of the path is removed); one-shots are pinned to the start position.
        rb = arm.data.bones[root]; Rinv = (arm.matrix_world.to_quaternion() @ rb.matrix_local.to_quaternion()).inverted()
        path = []
        for fr in range(f0, f1 + 1):
            sc.frame_set(fr); h = (arm.matrix_world @ arm.pose.bones[root].head).copy(); path.append(Vector((h.x - p0.x, h.y - p0.y, 0)))
        if meta[name]['loop']:
            w = sc.render.fps // 2; sm = []
            for i in range(len(path)):
                seg = path[max(0, i - w):i + w + 1]; sm.append(sum(seg, Vector()) / len(seg))
            path = sm
        locs = [find_fc(act, 'pose.bones["%s"].location' % root, i) for i in range(3)]
        if not all(locs):
            for i in range(3):
                if not locs[i]:
                    b0 = bags(act)[0]; locs[i] = b0.fcurves.new('pose.bones["%s"].location' % root, index=i)
        base = [[fc.evaluate(fr) for fr in range(f0, f1 + 1)] for fc in locs]
        for fc in locs: fc.keyframe_points.clear()
        for k_, fr in enumerate(range(f0, f1 + 1)):
            dl = Rinv @ path[k_]
            for i in range(3): locs[i].keyframe_points.insert(fr, base[i][k_] - dl[i], options={'FAST'})
        for fc in locs: fc.update()
    if meta[name]['loop']:
        # seamless loop: blend the tail into the head (last 25 % of 0.5 s)
        n = max(2, min(8, (f1 - f0) // 4))
        for fc in fcs(act):
            for k in range(n):
                fa, fb = f1 - n + k, f0 + k
                w = (k + 1) / (n + 1)
                va, vb = fc.evaluate(fa), fc.evaluate(f0)
                for kp in fc.keyframe_points:
                    if int(round(kp.co.x)) == fa: kp.co.y = va * (1 - w) + vb * w
            fc.update()
    arm.animation_data.action = None
    print('CLIP %-10s %5.2f s  speed %.2f m/s  in-place %s  loop %s  from %s' % (name, meta[name]['dur'], meta[name]['speed'], name in INPLACE, meta[name]['loop'], meta[name]['src']))

# ---- scale to the game height
zs = [(m.matrix_world @ v.co).z for m in meshes for v in m.data.vertices]
k = HEIGHT / (max(zs) - min(zs))
for o in [arm] + [m for m in meshes if m.parent is None]: o.scale *= k; o.location *= k
bpy.context.view_layer.update()
zs = [(m.matrix_world @ v.co).z for m in meshes for v in m.data.vertices]
for o in [arm] + [m for m in meshes if m.parent is None]: o.location.z -= min(zs)
for name in meta: meta[name]['speed'] = round(meta[name]['speed'] * k, 3)
print('SCALE k %.3f' % k)

arm.animation_data_create(); arm.animation_data.action = None
for name, act in clips.items():
    trk = arm.animation_data.nla_tracks.new(); trk.name = name; st = trk.strips.new(name, int(act.frame_range[0]), act)
    if hasattr(st, 'action_slot') and hasattr(act, 'slots') and len(act.slots): st.action_slot = act.slots[0]
for o in [o for o in bpy.data.objects if o.type == 'MESH' and not any(md.type == 'ARMATURE' for md in o.modifiers)]:
    print('DROP non-skinned mesh', o.name); bpy.data.objects.remove(o)
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
for o in bpy.data.objects: o.select_set(o in [arm] + meshes)
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, 'brute.glb'), export_format='GLB', use_selection=True, export_animations=True,
                          export_animation_mode='NLA_TRACKS', export_force_sampling=True, export_yup=True)
bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, 'brute_anim.fbx'), use_selection=True, object_types={'MESH', 'ARMATURE'}, axis_forward='X', axis_up='Z',
                         apply_scale_options='FBX_SCALE_ALL', add_leaf_bones=False, bake_anim=True, bake_anim_use_nla_strips=True, bake_anim_use_all_actions=False,
                         path_mode='COPY', embed_textures=True)
labels = {'Idle': 'idle, breathing', 'StopLunge': 'sprint, stop, coil to leap', 'Jump': 'launch', 'WallAttach': 'slam into a wall, fists in', 'WallClimb': 'climb step = the WallAttach slam', 'Land': 'superhero landing, fist planted',
          'PunchL': 'left haymaker', 'PunchR': 'right haymaker', 'Slap': 'big backhand slap', 'Clap': 'thunderclap', 'Smash': 'double-fist ground smash',
          'Lift': 'grab low, heave overhead, hold', 'Throw': 'hurl forward from overhead', 'Uppercut': 'crouch, rising uppercut', 'Fall': 'airborne, arms spread'}
cj = {n: dict(label=labels.get(n, '%.1f m/s' % m['speed']), speed=(m['speed'] if n in ('Walk', 'Run') else 0), loop=24 if n in ('Walk', 'Run') else 0,
              dir=[0, 0, 1], once=not m['loop'], **({'wallZ': m['wall_fwd'] * k} if 'wall_fwd' in m else {}),
              **({'hit': HIT[n]} if n in HIT else {})) for n, m in meta.items()}
json.dump(cj, open(os.path.join(OUT, 'clips.json'), 'w'), indent=1)
json.dump(meta, open(os.path.join(OUT, 'clips_meta.json'), 'w'), indent=1)
print('WROTE', OUT, list(clips))
