# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
# Shared helpers for the Brute anim_*.py Blender correction tools: load one clip GLB (as written by retarget_motion.py /
# clap_fix.py / throw_splice.py: target armature + mesh + one NLA track), sample per-frame WORLD bone rotations + hips head,
# forward kinematics from world rotations, rebuild a pose with some bones overridden (children keep their parent-relative
# rotation), 2-bone IK, heading helpers, and write the frames back out as a GLB with one NLA track.
# import from a Blender script:  sys.path.insert(0, os.path.dirname(__file__)); import anim_lib as L
import bpy, math
from mathutils import Vector, Quaternion, Matrix

ROOT = 'Hips'
UP = Vector((0, 0, 1))
S = {}   # rig state


def load(path, fps=30):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene; sc.render.fps = fps
    bpy.ops.import_scene.gltf(filepath=path)
    arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    ad = arm.animation_data
    act = ad.nla_tracks[0].strips[0].action if ad.nla_tracks else ad.action
    for t in list(ad.nla_tracks): ad.nla_tracks.remove(t)
    ad.action = act
    if hasattr(act, 'slots') and len(act.slots): ad.action_slot = act.slots[0]
    W = arm.matrix_world
    order = sorted(arm.data.bones, key=lambda b: len(b.parent_recursive))
    S.update(sc=sc, arm=arm, act=act, W=W, Wqi=W.to_quaternion().inverted(), order=order,
             RQ={b.name: (W @ b.matrix_local).to_quaternion() for b in arm.data.bones},
             RH={b.name: W @ b.head_local for b in arm.data.bones},
             tR={b.name: b.matrix_local.to_quaternion() for b in arm.data.bones},
             PAR={b.name: (b.parent.name if b.parent else None) for b in arm.data.bones})
    f0, f1 = (int(round(x)) for x in act.frame_range)
    S['f0'], S['f1'] = f0, f1
    return arm, act, f0, f1


def bind(arm, act):
    """use an armature already in the scene (e.g. inside assemble_motion.py) with `act` assigned"""
    W = arm.matrix_world
    order = sorted(arm.data.bones, key=lambda b: len(b.parent_recursive))
    S.update(sc=bpy.context.scene, arm=arm, act=act, W=W.copy(), Wqi=W.to_quaternion().inverted(), order=order,
             RQ={b.name: (W @ b.matrix_local).to_quaternion() for b in arm.data.bones},
             RH={b.name: W @ b.head_local for b in arm.data.bones},
             tR={b.name: b.matrix_local.to_quaternion() for b in arm.data.bones},
             PAR={b.name: (b.parent.name if b.parent else None) for b in arm.data.bones})
    S['f0'], S['f1'] = (int(round(x)) for x in act.frame_range)


def rekey_bones(act, frames, bones, f0):
    """overwrite the rotation_quaternion keys of `bones` in `act` with the world rotations of `frames` (one key per frame)"""
    Wqi, tR = S['Wqi'], S['tR']
    bags = [cb for L_ in act.layers for st in L_.strips for cb in st.channelbags] if hasattr(act, 'layers') else [act]
    for bn in bones:
        path = 'pose.bones["%s"].rotation_quaternion' % bn
        fcs = [next((fc for b in bags for fc in b.fcurves if fc.data_path == path and fc.array_index == i), None) for i in range(4)]
        for i in range(4):
            if fcs[i] is None: fcs[i] = bags[0].fcurves.new(path, index=i)
            fcs[i].keyframe_points.clear()
        prev = None
        for k, (world, rh) in enumerate(frames):
            aq = Wqi @ world[bn]; p = S['PAR'][bn]
            q = (((Wqi @ world[p]) @ (tR[p].inverted() @ tR[bn])).inverted() @ aq) if p else tR[bn].inverted() @ aq
            if prev is not None and q.dot(prev) < 0: q = -q
            prev = q
            for i in range(4): fcs[i].keyframe_points.insert(f0 + k, q[i], options={'FAST'})
        for fc in fcs: fc.update()


def sample(f):
    sc, arm, W = S['sc'], S['arm'], S['W']
    fi = int(math.floor(f)); sc.frame_set(fi, subframe=f - fi)
    return ({b.name: (W @ arm.pose.bones[b.name].matrix).to_quaternion() for b in S['order']}, (W @ arm.pose.bones[ROOT].head).copy())


def sample_all():
    return [sample(f) for f in range(S['f0'], S['f1'] + 1)]


def fk(world, rh):
    RQ, RH, PAR = S['RQ'], S['RH'], S['PAR']; pos = {}
    for b in S['order']:
        p = PAR[b.name]
        pos[b.name] = rh.copy() if p is None else pos[p] + (world[p] @ RQ[p].inverted()) @ (RH[b.name] - RH[p])
    return pos


def rebuild(ws, over):
    """world rotations top-down: overridden bones absolute, others keep their parent-relative rotation from ws"""
    out = {}; PAR = S['PAR']
    for b in S['order']:
        n = b.name; p = PAR[n]
        out[n] = over[n] if n in over else (ws[n] if p is None else out[p] @ (ws[p].inverted() @ ws[n]))
    return out


def smooth(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)


def blend(A, B, w):
    return {n: A[0][n].slerp(B[0][n], w) for n in A[0]}, A[1].lerp(B[1], w)


def heading(world, rh, a='LeftUpLeg', b='RightUpLeg'):
    """yaw (rad) of the a->b line's forward normal; forward = UP x (left->right)"""
    pos = fk(world, rh); lat = pos[b] - pos[a]; lat.z = 0
    if lat.length < 1e-6: return 0.0
    f = UP.cross(lat.normalized()); return math.atan2(f.y, f.x)


def wrap(a): return (a + math.pi) % (2 * math.pi) - math.pi


def ik2(A, K, T, l1=None, l2=None, pole=None):
    """2-bone IK: shoulder/hip A, current mid joint K (pole side), target T -> new mid joint, reached end"""
    l1 = l1 or (K - A).length; l2 = l2 or (T - K).length
    dv = T - A; d = min(dv.length, (l1 + l2) * 0.9995); u = dv.normalized()
    pl = (pole if pole is not None else (K - A)); pl = pl - pl.dot(u) * u
    pl = pl.normalized() if pl.length > 1e-6 else UP.cross(u).normalized()
    ca = max(-1.0, min(1.0, (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d)))
    return A + l1 * (ca * u + math.sqrt(max(0.0, 1 - ca * ca)) * pl), A + u * d


def leg_ik(world, rh, side, foot_target, foot_rot=None, pole=None):
    """re-solve UpLeg/Leg so the ankle (side+'Foot' head) reaches foot_target; foot keeps world rotation foot_rot (or its own)"""
    pos = fk(world, rh); RH = S['RH']
    A, K, T = pos[side + 'UpLeg'], pos[side + 'Leg'], pos[side + 'Foot']
    l1 = (RH[side + 'Leg'] - RH[side + 'UpLeg']).length; l2 = (RH[side + 'Foot'] - RH[side + 'Leg']).length
    K2, T2 = ik2(A, K, foot_target, l1, l2, pole if pole is not None else (K - A) - (K - A).dot((T - A).normalized()) * (T - A).normalized())
    over = {}
    up = (K - A).rotation_difference(K2 - A) @ world[side + 'UpLeg']
    w2 = rebuild(world, {side + 'UpLeg': up}); p2 = fk(w2, rh)
    lo = (p2[side + 'Foot'] - p2[side + 'Leg']).rotation_difference(T2 - K2) @ w2[side + 'Leg']
    over[side + 'UpLeg'] = up; over[side + 'Leg'] = lo
    over[side + 'Foot'] = foot_rot if foot_rot is not None else world[side + 'Foot']
    # keep the toes' world rotation too
    for c in (side + 'ToeBase',):
        if c in world: over[c] = world[c] if foot_rot is None else foot_rot @ (world[side + 'Foot'].inverted() @ world[c])
    return over


def partner(n):
    return 'Right' + n[4:] if n.startswith('Left') else 'Left' + n[5:] if n.startswith('Right') else n


def bind_lateral():
    RH = S['RH']; l = RH['RightUpLeg'] - RH['LeftUpLeg']; l.z = 0; return l.normalized()


def mirror_rot(q, n):
    """rotation mirrored by the plane with unit normal n (M R M): axis -> -(M axis), same angle"""
    v = Vector((q.x, q.y, q.z)); v2 = -v + 2 * v.dot(n) * n
    return Quaternion((q.w, v2.x, v2.y, v2.z))


def mirror_pose(world, rh, lat, origin):
    """the pose mirrored about the vertical plane through `origin` with normal `lat` (the pose's left -> right axis). Bone deltas are
    mirrored in the bind's own frame (the bind is symmetric about its sagittal plane, which need not face the clip's way)"""
    RQ = S['RQ']; nr = bind_lateral()
    Y = Quaternion(UP, math.atan2(lat.y, lat.x) - math.atan2(nr.y, nr.x)); Yi = Y.inverted()
    out = {}
    for b in S['order']:
        p = partner(b.name)
        e = Yi @ (world[p] @ RQ[p].inverted())
        out[b.name] = Y @ mirror_rot(e, nr) @ RQ[b.name]
    d = rh - origin; d = d - 2 * d.dot(lat) * lat
    return out, origin + d


def symmetrize(world, rh, lat, origin, master=None):
    """symmetric pose: each bone = halfway between itself and its mirrored partner; master='Left' copies the left side mirrored
    onto the right (exact mirror image), midline bones halfway"""
    m, mrh = mirror_pose(world, rh, lat, origin)
    out = {}
    for b in S['order']:
        n_ = b.name
        if master and n_.startswith('Left' if master == 'Right' else 'Right'): out[n_] = m[n_]
        elif master and n_.startswith(master): out[n_] = world[n_]
        else:
            q2 = m[n_] if world[n_].dot(m[n_]) >= 0 else -m[n_]
            out[n_] = world[n_].slerp(q2, 0.5)
    return out, rh.lerp(mrh, 0.5)


def leg_len(side='Left'):
    RH = S['RH']; return (RH[side + 'Leg'] - RH[side + 'UpLeg']).length + (RH[side + 'Foot'] - RH[side + 'Leg']).length


def plant_targets(frames, side, h_k=0.07, v_k=0.025, min_len=3, blend=3, keep=None):
    """foot lock targets: frames where the foot is near its lowest height and barely moving are grouped into plants; each plant's
    ankle is pinned (xy) to the plant's average, blending in/out over `blend` frames. Returns per-frame ankle targets (or None)"""
    l = leg_len(side); n = len(frames)
    P = [fk(w, rh) for w, rh in frames]
    ank = [p[side + 'Foot'] for p in P]; toe = [p[side + 'ToeBase'] for p in P]
    zt = min(t.z for t in toe); za = min(a.z for a in ank)
    def sp(i):
        j = max(0, i - 1); k = min(n - 1, i + 1)
        d = (toe[k] - toe[j]); d.z = 0; return d.length / max(1, k - j)
    # on the ground = toe or ankle near its lowest height (a planted foot that slides in the take is still planted: it gets pinned);
    # short lifts (<= 4 frames, foot stays below 2x the threshold) are a shuffle / slide in the take and are merged into one plant
    low = [toe[i].z < zt + h_k * l or ank[i].z < za + h_k * l for i in range(n)]
    lowish = [toe[i].z < zt + 2 * h_k * l or ank[i].z < za + 2 * h_k * l for i in range(n)]
    planted = list(low); i = 0
    while i < n:
        if not planted[i]:
            j = i
            while j + 1 < n and not planted[j + 1]: j += 1
            if 0 < i and j < n - 1 and j - i + 1 <= 4 and all(lowish[i:j + 1]):
                for k in range(i, j + 1): planted[k] = True
            i = j + 1
        else: i += 1
    if keep:   # forced plant frame ranges [(a, b)]
        for a_, b_ in keep:
            for i in range(max(0, a_), min(n, b_ + 1)): planted[i] = True
    segs = []; i = 0
    while i < n:
        if planted[i]:
            j = i
            while j + 1 < n and planted[j + 1]: j += 1
            if j - i + 1 >= min_len: segs.append((i, j))
            i = j + 1
        else: i += 1
    tgt = [None] * n; wts = [0.0] * n
    for a_, b_ in segs:
        c = sum((ank[i] for i in range(a_, b_ + 1)), Vector()) / (b_ - a_ + 1)
        for i in range(max(0, a_ - blend), min(n, b_ + blend + 1)):
            w = 1.0 if a_ <= i <= b_ else smooth(1 - (a_ - i) / (blend + 1)) if i < a_ else smooth(1 - (i - b_) / (blend + 1))
            if w > wts[i]:
                wts[i] = w; tgt[i] = Vector((ank[i].x + (c.x - ank[i].x) * w, ank[i].y + (c.y - ank[i].y) * w, ank[i].z))
    return tgt, segs


def apply_feet(frames, targets, sides=('Left', 'Right')):
    """leg IK every frame toward the given ankle targets (None = leave the leg alone)"""
    out = []
    for i, (w, rh) in enumerate(frames):
        over = {}
        for s in sides:
            t = targets[s][i]
            if t is None: continue
            over.update(leg_ik(rebuild(w, over), rh, s, t, foot_rot=w[s + 'Foot']))
        out.append((rebuild(w, over) if over else w, rh))
    return out


def write(frames, out, name, sf0=None):
    """frames: list of (world rotations, hips head world position); writes a GLB with one NLA track"""
    arm, W, Wqi, tR, RH = S['arm'], S['W'], S['Wqi'], S['tR'], S['RH']
    sf0 = S['f0'] if sf0 is None else sf0
    act = bpy.data.actions.new(name)
    arm.animation_data.action = act
    if hasattr(act, 'slots') and hasattr(arm.animation_data, 'action_slot') and len(act.slots): arm.animation_data.action_slot = act.slots[0]
    for k, (world, rh) in enumerate(frames):
        fr = sf0 + k
        for b in S['order']:
            pb = arm.pose.bones[b.name]; pb.rotation_mode = 'QUATERNION'
            aq = Wqi @ world[b.name]
            if b.parent: basis = ((Wqi @ world[b.parent.name]) @ (tR[b.parent.name].inverted() @ tR[b.name])).inverted() @ aq
            else: basis = tR[b.name].inverted() @ aq
            pb.rotation_quaternion = basis; pb.keyframe_insert('rotation_quaternion', frame=fr)
        pr = arm.pose.bones[ROOT]; pr.location = tR[ROOT].inverted() @ (W.inverted().to_3x3() @ (rh - RH[ROOT])); pr.keyframe_insert('location', frame=fr)
    # keep quaternion signs continuous (no long-way interpolation)
    for fcs in [cb.fcurves for L_ in act.layers for st in L_.strips for cb in st.channelbags] if hasattr(act, 'layers') else [act.fcurves]:
        groups = {}
        for fc in fcs:
            if fc.data_path.endswith('rotation_quaternion'): groups.setdefault(fc.data_path, {})[fc.array_index] = fc
        for g in groups.values():
            if len(g) < 4: continue
            n = len(g[0].keyframe_points)
            for i in range(1, n):
                dot = sum(g[j].keyframe_points[i].co.y * g[j].keyframe_points[i - 1].co.y for j in range(4))
                if dot < 0:
                    for j in range(4): g[j].keyframe_points[i].co.y *= -1
            for j in range(4):
                for kp in g[j].keyframe_points: kp.interpolation = 'LINEAR'
                g[j].update()
    old = S['act']
    for a_ in [a_ for a_ in bpy.data.actions if a_ != act]: bpy.data.actions.remove(a_)
    arm.animation_data.action = None
    trk = arm.animation_data.nla_tracks.new(); trk.name = name; st = trk.strips.new(name, sf0, act)
    if hasattr(st, 'action_slot') and hasattr(act, 'slots') and len(act.slots): st.action_slot = act.slots[0]
    for o in bpy.data.objects: o.select_set(o.type in ('ARMATURE', 'MESH'))
    bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', use_selection=True, export_animations=True, export_animation_mode='NLA_TRACKS',
                              export_force_sampling=True, export_yup=True)
    print('WROTE', name, len(frames), 'frames ->', out)
