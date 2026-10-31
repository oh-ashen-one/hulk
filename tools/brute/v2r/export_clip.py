# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
# video2rig Action on the ALIGNED Brute rig -> one motion GLB on the SHIPPED rig that tools/brute/assemble_motion.py ingests.
#
#   Blender -b --factory-startup -P tools/brute/v2r/export_clip.py -- <fit.blend> <Clip> <motion_dir> [options]
#     <fit.blend>   a .blend saved by video2rig's import_motion.py (or refine_brute.py): aligned armature + mesh + the clip Action
#     <Clip>        assemble_motion CLIPS name: Idle Walk Run StopLunge Jump WallAttach WallClimb PunchL PunchR Slap Clap Smash
#                   Lift Throw Uppercut Fall Land
#     <motion_dir>  where <name>.glb goes (the file name is chosen so assemble_motion's CLIPS regex picks it for <Clip>)
#   options: --action NAME (default: the armature's active action)  --tag v1 (file suffix, e.g. Brute_v2r_idle_v1.glb)
#            --rig PATH (shipped rig, default brute_rigged_corr.glb = assemble_motion's first arg)  --fps 30
#            --gate-frames 5  --gate-mm 1.0
#   Blender -b --factory-startup -P tools/brute/v2r/export_clip.py -- --self-test      (file-name table vs assemble_motion CLIPS only)
#
# What it does
#   1. self-test: reads CLIPS from assemble_motion.py (ast, nothing imported) and checks every file name against assemble's own
#      lookup (first pattern alternative, then the whole pattern, first match in sorted order), alone and with all 17 names together.
#   2. rig check: bone names, parents and heads (armature space) of the aligned and shipped rigs agree within 1e-4, or it stops.
#   3. retarget: every output frame, armature-space pose matrices of the aligned rig -> shipped pose basis (v2r_rig.py), parent-aware.
#      Output is 30 fps (assemble_motion runs at 30): the fit's keys sit at its scene fps (import_motion: 24); each 30 fps frame
#      samples the source Action at the same time (linear, as Blender evaluates it), so nothing is re-timed.
#   4. writes <motion_dir>/<name>.glb: shipped armature (its own glb transform, so assemble's location-scale factor stays 1) + mesh +
#      one NLA track, the same export settings as tools/brute/anim_lib.py write().
#   5. EXPORT_GATE: the aligned model's mesh, deformed by the aligned rig, vs the same mesh deformed by the shipped rig carrying the
#      RE-IMPORTED glb action (imported the way assemble_motion does), on N frames spread over the clip; armature space, reported in
#      mm of the fit scene (aligned armature object scale applied). FAIL over --gate-mm, exit code 3.
import ast
import json
import math
import os
import re
import sys

import bpy
import numpy as np
from mathutils import Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v2r_rig as R  # noqa: E402

ASSEMBLE = os.path.join(os.path.dirname(HERE), 'assemble_motion.py')
OLD_MOTION_DIR = '/Users/midir/hulk-scratch/brute_v2/motion'
# file stems; locomotion clips use Brute_v2r_<key>, the combat/air clips must carry assemble's literal 'brute_<key>' keyword.
# The '-' (sorts before '.') makes every v2r file win over the old file of the same clip when both sit in one motion dir
# (assemble takes the first match in sorted order), so 'v2r wins' holds for all 17 clips: put a v2r file in the motion dir
# only once it has won its A/B. The self-test prints this precedence against the old motion dir.
NAMES = {'Idle': 'Brute_v2r_idle', 'Walk': 'Brute_v2r_walk', 'Run': 'Brute_v2r_run', 'StopLunge': 'Brute_v2r_stoplunge',
         'Jump': 'Brute_v2r_jump', 'WallAttach': 'Brute_v2r_wallattach', 'WallClimb': 'Brute_v2r_wallclimb',
         'PunchL': 'Brute_punchl-v2r', 'PunchR': 'Brute_punchr-v2r', 'Slap': 'Brute_slap-v2r', 'Clap': 'Brute_clap-v2r',
         'Smash': 'Brute_smash-v2r', 'Lift': 'Brute_liftthrow-v2r', 'Throw': 'Brute_throw-v2r', 'Uppercut': 'Brute_uppercut-v2r',
         'Fall': 'Brute_fall-v2r', 'Land': 'Brute_land-v2r'}


def file_name(clip, tag=''):
    return NAMES[clip] + (('_' + tag) if tag else '') + '.glb'


# ------------------------------------------------------------------ 1. file names vs assemble_motion's CLIPS
def read_clips():
    tree = ast.parse(open(ASSEMBLE).read())
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'CLIPS' for t in node.targets):
            return ast.literal_eval(node.value)
    raise SystemExit('export_clip: CLIPS not found in ' + ASSEMBLE)


def assemble_pick(pat, files):
    """assemble_motion.py's lookup, verbatim logic"""
    files = sorted(files)
    return next((x for x in files if re.search(pat.split('|')[0], os.path.basename(x).lower())), None) or \
        next((x for x in files if re.search(pat, os.path.basename(x).lower())), None)


def self_test(tag=''):
    clips = read_clips()
    names = {c: file_name(c, tag) for c, _, _ in clips}
    bad = []
    missing = [c for c, _, _ in clips if c not in NAMES]
    if missing:
        bad.append('clips without a file name: %s' % missing)
    for c, pat, _ in clips:
        if c not in names:
            continue
        if assemble_pick(pat, [names[c]]) != names[c]:
            bad.append('%s: %s does not match %r' % (c, names[c], pat))
        got = assemble_pick(pat, list(names.values()))
        if got != names[c]:
            bad.append('%s: with all v2r files present assemble picks %s, not %s' % (c, got, names[c]))
    old = sorted(os.listdir(OLD_MOTION_DIR)) if os.path.isdir(OLD_MOTION_DIR) else []
    prec = {}
    for c, pat, _ in clips:
        if c not in names:
            continue
        o = assemble_pick(pat, old)
        if o:
            prec[c] = 'v2r wins' if assemble_pick(pat, old + [names[c]]) == names[c] else 'OLD %s wins' % o
    print('EXPORT_SELFTEST names', json.dumps(names))
    print('EXPORT_SELFTEST mixed with %s (who assemble picks if both are in one motion dir):' % OLD_MOTION_DIR, json.dumps(prec))
    print('EXPORT_SELFTEST %s (%d clips from assemble_motion CLIPS)%s' % ('PASS' if not bad else 'FAIL', len(clips), ''.join('\n  ' + b for b in bad)))
    return not bad


# ------------------------------------------------------------------ args
def parse():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    import argparse
    ap = argparse.ArgumentParser(prog='export_clip.py')
    ap.add_argument('blend', nargs='?')
    ap.add_argument('clip', nargs='?')
    ap.add_argument('motion_dir', nargs='?')
    ap.add_argument('--action', default='')
    ap.add_argument('--tag', default='')
    ap.add_argument('--rig', default=R.SHIPPED_RIG)
    ap.add_argument('--fps', type=float, default=30.0)
    ap.add_argument('--gate-frames', type=int, default=5)
    ap.add_argument('--gate-mm', type=float, default=1.0)
    ap.add_argument('--self-test', action='store_true')
    return ap.parse_args(argv)


def drop_helpers(objs):
    for o in [o for o in objs if o.type == 'MESH' and re.match(r'(icosphere|sphere|plane|cube)', o.name.lower())]:
        objs.remove(o)
        bpy.data.objects.remove(o)
    return objs


def arm_local(mesh_obj, arm):
    V = R.mesh_world(mesh_obj)
    Ai = np.array(arm.matrix_world.inverted())
    return V @ Ai[:3, :3].T + Ai[:3, 3]


def main():
    a = parse()
    if not self_test(a.tag):
        sys.exit(2)
    if a.self_test:
        return
    if not (a.blend and a.clip and a.motion_dir):
        sys.exit('export_clip: need <fit.blend> <Clip> <motion_dir>')
    if a.clip not in NAMES:
        sys.exit('export_clip: unknown clip %r (one of %s)' % (a.clip, ', '.join(NAMES)))
    src_blend = os.path.abspath(a.blend)
    bpy.ops.wm.open_mainfile(filepath=src_blend, load_ui=False)  # never saved
    sc = bpy.context.scene
    arms = [o for o in sc.objects if o.type == 'ARMATURE']
    al = next((o for o in arms if o.animation_data and o.animation_data.action), arms[0] if arms else None)
    if al is None:
        sys.exit('export_clip: no armature in ' + src_blend)
    act = bpy.data.actions[a.action] if a.action else (al.animation_data.action if al.animation_data else None)
    if act is None:
        sys.exit('export_clip: no action (give --action)')
    R.assign_action(al, act)
    mesh_al = next(o for o in sc.objects if o.type == 'MESH' and any(m.type == 'ARMATURE' and m.object == al for m in o.modifiers))
    fps_src = sc.render.fps / sc.render.fps_base
    k0, k1 = R.key_range(act)
    nkeys = len({round(kp.co.x, 4) for fc in R.action_fcurves(act) for kp in fc.keyframe_points})
    T = (k1 - k0) / fps_src
    n_out = int(math.floor(T * a.fps + 1e-6)) + 1
    src_frames = [k0 + k * fps_src / a.fps for k in range(n_out)]
    resampled = abs(fps_src - a.fps) > 1e-6 or any(abs(f - round(f)) > 1e-6 for f in src_frames)
    print('EXPORT %s source action %r: keys %.3f..%.3f at %g fps (%d distinct key times) = %.3f s' % (a.clip, act.name, k0, k1, fps_src, nkeys, T))
    print('EXPORT %s output: %d frames (0..%d) at %g fps = %.3f s; %s' % (
        a.clip, n_out, n_out - 1, a.fps, (n_out - 1) / a.fps,
        ('resampled %g -> %g fps: output frame k samples the source Action at frame %.3f + k*%.4f (same time, linear)' % (fps_src, a.fps, k0, fps_src / a.fps))
        if resampled else 'no resampling (source already %g fps on integer frames)' % a.fps))
    kb = R.keyed_bones(act)
    print('EXPORT %s source keyed bones %d of %d (unkeyed bones keep the fit .blend stance)' % (a.clip, len(kb), len(al.data.bones)))

    # ---- 2. shipped rig + check
    objs = drop_helpers(R.import_glb(a.rig))
    sh = next(o for o in objs if o.type == 'ARMATURE')
    sh_meshes = [o for o in objs if o.type == 'MESH']
    if sh.animation_data:
        sh.animation_data_clear()
    for pb in sh.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.matrix_basis = Matrix.Identity(4)
    ok, lines = R.check_match(al, sh, 1e-4)
    for ln in lines:
        print('EXPORT rig check:', ln)
    if not ok:
        print('EXPORT_GATE %s max_vertex_delta_mm nan frames 0 FAIL (rig mismatch)' % a.clip)
        sys.exit(4)
    R_al, R_sh, PAR_sh = R.rest(al), R.rest(sh), R.parents(sh)

    # ---- 3. retarget every output frame
    bases = []
    for f in src_frames:
        R.set_frame(f)
        bases.append(R.retarget_basis(R.sample_pose(al), R_al, R_sh, PAR_sh))
    smax = max(abs(s - 1.0) for B in bases for M in B.values() for s in M.to_scale())
    gate_k = sorted(set(int(round(x)) for x in np.linspace(0, n_out - 1, max(1, a.gate_frames))))

    # retarget-only check (before any file): the aligned mesh driven by the aligned rig vs a copy driven by the shipped rig
    sh_w = sh.matrix_world.copy()
    sh.matrix_world = al.matrix_world.copy()
    probe = mesh_al.copy()
    sc.collection.objects.link(probe)
    probe.parent = sh
    probe.matrix_parent_inverse = mesh_al.matrix_parent_inverse.copy()
    for m in probe.modifiers:
        if m.type == 'ARMATURE':
            m.object = sh
    bpy.context.view_layer.update()
    scale_al = al.matrix_world.to_scale().x
    ref, d_ret = {}, []
    for k in gate_k:
        R.set_frame(src_frames[k])
        for n, M in bases[k].items():
            sh.pose.bones[n].matrix_basis = M
        bpy.context.view_layer.update()
        va, vs = arm_local(mesh_al, al), arm_local(probe, sh)
        ref[k] = va
        d_ret.append(float(np.linalg.norm(va - vs, axis=1).max()) * scale_al * 1000)
    bpy.data.objects.remove(probe)
    sh.matrix_world = sh_w
    print('EXPORT %s retarget-only (in memory) max vertex delta %.4f mm on frames %s; max |pose scale-1| %.2e' % (a.clip, max(d_ret), gate_k, smax))

    # ---- 4. write the motion glb (30 fps scene, one NLA track, anim_lib.write settings)
    for pb in sh.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    sc.render.fps, sc.render.fps_base = int(round(a.fps)), 1.0
    stem = os.path.splitext(file_name(a.clip, a.tag))[0]
    new = bpy.data.actions.new(stem)
    loc_bones = R.write_basis_frames(sh, new, list(range(n_out)), bases)
    sh.animation_data.action = None
    trk = sh.animation_data.nla_tracks.new()
    trk.name = stem
    st = trk.strips.new(stem, 0, new)
    if hasattr(st, 'action_slot') and hasattr(new, 'slots') and len(new.slots):
        st.action_slot = new.slots[0]
    os.makedirs(a.motion_dir, exist_ok=True)
    out = os.path.join(os.path.abspath(a.motion_dir), stem + '.glb')
    for o in bpy.data.objects:
        o.select_set(o == sh or o in sh_meshes)
    sc.frame_start, sc.frame_end = 0, n_out - 1
    bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', use_selection=True, export_animations=True,
                              export_animation_mode='NLA_TRACKS', export_force_sampling=True, export_yup=True)
    print('EXPORT %s wrote %s (%.1f MB); location keys on %s' % (a.clip, out, os.path.getsize(out) / 1e6, loc_bones))

    # ---- 5. end-to-end gate: re-import exactly like assemble_motion and compare on the aligned mesh
    mesh_name, act_name = mesh_al.name, act.name
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps = int(round(a.fps))
    rig_objs = drop_helpers(R.import_glb(a.rig))
    rig = next(o for o in rig_objs if o.type == 'ARMATURE')
    for ac in list(bpy.data.actions):
        bpy.data.actions.remove(ac)
    if rig.animation_data:
        rig.animation_data_clear()
    for pb in rig.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.matrix_basis = Matrix.Identity(4)
    mo = R.import_glb(out)
    src = next(o for o in mo if o.type == 'ARMATURE')
    mact = src.animation_data.action if src.animation_data else None
    if mact is None:
        print('EXPORT_GATE %s max_vertex_delta_mm nan frames 0 FAIL (no action in the re-imported glb)' % a.clip)
        sys.exit(3)
    ks = src.matrix_world.to_scale().x / rig.matrix_world.to_scale().x
    mact = mact.copy()
    mact.name = a.clip
    for o in mo:
        bpy.data.objects.remove(o)
    fr = tuple(int(round(x)) for x in mact.frame_range)
    R.assign_action(rig, mact)
    with bpy.data.libraries.load(src_blend, link=False) as (df, dt):
        dt.objects = [mesh_name]
    gm = dt.objects[0]
    sc.collection.objects.link(gm)
    stray = gm.parent
    gm.parent = rig
    for m in gm.modifiers:
        if m.type == 'ARMATURE':
            m.object = rig
    if stray is not None and stray.name in bpy.data.objects:
        bpy.data.objects.remove(stray)
    bpy.context.view_layer.update()
    d = []
    for k in gate_k:
        sc.frame_set(k)
        vs = arm_local(gm, rig)
        d.append(float(np.linalg.norm(ref[k] - vs, axis=1).max()) * scale_al * 1000)
    mx = max(d)
    res = 'PASS' if (mx <= a.gate_mm and max(d_ret) <= a.gate_mm and abs(ks - 1) < 1e-4 and fr == (0, n_out - 1)) else 'FAIL'
    rep = dict(clip=a.clip, source=src_blend, action=act_name, out=out, fps_source=fps_src, fps_out=a.fps, resampled=resampled,
               source_keys=[k0, k1], frames_out=n_out, seconds=(n_out - 1) / a.fps, gate_frames=gate_k,
               delta_mm_reimported=[round(x, 4) for x in d], delta_mm_retarget_only=[round(x, 4) for x in d_ret],
               reimported_frame_range=list(fr), assemble_location_scale=ks, location_bones=loc_bones, result=res)
    json.dump(rep, open(os.path.splitext(out)[0] + '.export.json', 'w'), indent=1)
    print('EXPORT %s re-imported action frames %s, assemble location scale %.4f, per-frame mm %s' % (a.clip, fr, ks, [round(x, 4) for x in d]))
    print('EXPORT_GATE %s max_vertex_delta_mm %.4f frames %d %s' % (a.clip, mx, len(gate_k), res), flush=True)
    if res != 'PASS':
        sys.exit(3)



if __name__ == '__main__':
    main()
