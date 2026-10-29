# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
# Blind A/B render: one subject, three fixed cameras (front, left side, three-quarter), 24 fps mp4, looping clips twice.
#
#   Blender -b --factory-startup -P tools/brute/v2r/ab_render.py -- --subject <file.glb>[:<Action>] --label A --out <dir> [options]
#     --subject   a shipped-rig glb (+ Action name when the glb holds several), see ab_common.py; the brute_v5 glb works
#     --label     file prefix; writes <out>/<label>_{front,left,threequarter}.mp4 (nothing in the files names the source)
#     --clip      clip name (Idle, Walk, ...) used only to look up whether the clip loops (default: the Action name)
#     --loop / --no-loop   override the clips_meta.json loop flag; loops are played twice so the seam is visible
#     --root game|raw   game (default) = what BruteCharacter.cpp shows: Hips XY pinned (the sim moves him, clip travel dropped),
#                ground clips get their lowest foot put back on the street every frame (air clips Jump/Fall/Wall*: first-frame
#                correction only); raw = the Action as exported (cameras are fixed, a travelling clip walks out of frame)
#     --material clay|texture    clay = one flat grey for every subject (default), texture = the exported tripo material
#     --cams front,left,threequarter   subset (default all three)       --samples N   Eevee samples (default 10)
#     --base PATH  character the Action is played on (default the brute_v5 glb)
#
# Look: Eevee (10 samples), 854 x 480, flat clay character with the corrective shape keys as exported (values from the glb), light
# grey floor with a soft sun shadow, grey backdrop, no text. The camera table lives in ab_common.py and is the same for every
# subject. One Blender process, three cameras one after the other; PNG frames go to a temp dir and are deleted after ffmpeg.
import argparse
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ab_common as C  # noqa: E402
import v2r_rig as R  # noqa: E402

CLAY = (0.20, 0.215, 0.205, 1.0)
FLOOR = (0.72, 0.72, 0.72, 1.0)
BACKDROP = (0.88, 0.89, 0.90)
WORLD_STRENGTH, KEY_ENERGY, FILL_ENERGY, FILL_PITCH, FILL_YAW = 0.30, 1.6, 1.5, 28.0, -32.0
FFMPEG = shutil.which('ffmpeg') or '/opt/homebrew/bin/ffmpeg'


def parse():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    ap = argparse.ArgumentParser(prog='ab_render.py')
    ap.add_argument('--subject', required=True)
    ap.add_argument('--label', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--clip', default='')
    ap.add_argument('--loop', dest='loop', action='store_true', default=None)
    ap.add_argument('--no-loop', dest='loop', action='store_false')
    ap.add_argument('--root', choices=['game', 'raw'], default='game')
    ap.add_argument('--material', choices=['clay', 'texture'], default='clay')
    ap.add_argument('--samples', type=int, default=10, help='Eevee TAA samples (10 = soft shadow, ~0.27 s/frame at 854x480)')
    ap.add_argument('--cams', default=','.join(C.CAM_ORDER))
    ap.add_argument('--base', default=C.BASE_GLB)
    ap.add_argument('--max-frames', type=int, default=0, help='debug: stop after N frames')
    ap.add_argument('--keep-frames', action='store_true')
    return ap.parse_args(argv)


def mat_flat(name, rgba):
    m = bpy.data.materials.new(name)
    m.diffuse_color = rgba
    m.use_nodes = True
    bsdf = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs['Base Color'].default_value = rgba
    bsdf.inputs['Roughness'].default_value = 0.85
    for k in ('Specular IOR Level', 'Specular'):
        if k in bsdf.inputs:
            bsdf.inputs[k].default_value = 0.1
    return m


def build_floor(scene):
    me = bpy.data.meshes.new('floor')
    S = 30.0
    me.from_pydata([(-S, -S, 0), (S, -S, 0), (S, S, 0), (-S, S, 0)], [], [(0, 1, 2, 3)])
    ob = bpy.data.objects.new('floor', me)
    scene.collection.objects.link(ob)
    me.materials.append(mat_flat('floor', FLOOR))
    return ob


def eevee_name():
    ids = [i.identifier for i in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items]
    return next(i for i in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE') if i in ids)


def setup_scene(base, material, samples):
    sc = base.scene
    sc.render.engine = eevee_name()
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = C.RES[0], C.RES[1], 100
    sc.render.fps, sc.render.fps_base = C.FPS, 1.0
    sc.render.film_transparent = False
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGB'
    for vt in ('Standard',):
        try:
            sc.view_settings.view_transform = vt
        except TypeError:
            pass
    if sc.world is None:
        sc.world = bpy.data.worlds.new('w')
    sc.world.use_nodes = True
    bg = next(n for n in sc.world.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs['Color'].default_value = (*BACKDROP, 1.0)
    bg.inputs['Strength'].default_value = WORLD_STRENGTH
    try:
        sc.eevee.taa_render_samples = samples
        sc.eevee.use_shadows = True
    except Exception:  # noqa
        pass
    if material == 'clay':
        base.mesh.data.materials.clear()
        base.mesh.data.materials.append(mat_flat('clay', CLAY))
    build_floor(sc)
    # key: steep sun with a soft edge (the pool of shadow under the feet shows contact); the same for every camera
    key = bpy.data.objects.new('key', bpy.data.lights.new('key', 'SUN'))
    key.data.energy, key.data.angle = KEY_ENERGY, math.radians(12)
    key.rotation_euler = Vector((0.05, -0.07, -1.0)).to_track_quat('-Z', 'Y').to_euler()
    sc.collection.objects.link(key)


def add_fill(sc, cam):
    """camera-relative fill without shadows so the arms read against the torso from every camera"""
    f = bpy.data.objects.new('fill', bpy.data.lights.new('fill', 'SUN'))
    f.data.energy = FILL_ENERGY
    f.data.use_shadow = False
    sc.collection.objects.link(f)
    f.parent = cam
    f.rotation_euler = (math.radians(FILL_PITCH), math.radians(FILL_YAW), 0.0)
    return f


def encode(png_dir, out_mp4, n):
    cmd = [FFMPEG, '-y', '-loglevel', 'error', '-framerate', str(C.FPS), '-i', os.path.join(png_dir, '%04d.png'),
           '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '19', '-preset', 'medium', '-movflags', '+faststart',
           '-map_metadata', '-1', '-fflags', '+bitexact', '-flags:v', '+bitexact', out_mp4]
    subprocess.run(cmd, check=True)


def main():
    a = parse()
    t_start = time.time()
    base = C.Base(a.base)
    act, info = base.import_action(a.subject)
    base.play(act)
    clip = a.clip or os.path.basename(C.parse_subject(a.subject)[1] or '').split('.')[0] or 'clip'
    loop = C.clip_is_loop(clip) if a.loop is None else a.loop
    times = C.sample_times(act, loop)
    n = len(times)

    grounding = C.grounding_for(clip)
    dz0 = C.first_dz(base, times, a.root)
    ang0 = None
    C.pose_frame(base, times[0], a.root, grounding, dz0)
    ang0 = C.check_facing(base)
    print('AB_RENDER %s subject %s loop %s frames %d (%.3f s) root %s grounding %s; facing off by %s deg at frame 0; shape keys %d%s' % (
        a.label, os.path.basename(a.subject), loop, n, (n - 1) / C.FPS, a.root, grounding if a.root == 'game' else 'n/a',
        'n/a' if ang0 is None else '%.0f' % ang0, len(base.shape_keys), ' (!) FACING warning' if (ang0 or 0) > 35 else ''))
    setup_scene(base, a.material, a.samples)
    sc = base.scene
    os.makedirs(a.out, exist_ok=True)
    passes = 2 if loop else 1
    seq = [(p, i) for p in range(passes) for i in range(n)]
    if a.max_frames:
        seq = seq[:a.max_frames]
    cams = [c for c in a.cams.split(',') if c]
    for cname in cams:
        cam = C.make_camera(sc, cname)
        sc.camera = cam
        fill = add_fill(sc, cam)
        tmp = tempfile.mkdtemp(prefix='.frames_%s_%s_' % (a.label, cname), dir=os.path.abspath(a.out))
        t0 = time.time()
        for j, (p, i) in enumerate(seq):
            C.pose_frame(base, times[i], a.root, grounding, dz0)
            sc.render.filepath = os.path.join(tmp, '%04d.png' % (j + 1))
            bpy.ops.render.render(write_still=True)
        out = os.path.join(a.out, '%s_%s.mp4' % (a.label, cname))
        encode(tmp, out, len(seq))
        if not a.keep_frames:
            shutil.rmtree(tmp, ignore_errors=True)
        bpy.data.objects.remove(fill)
        bpy.data.objects.remove(cam)
        print('AB_RENDER %s %s -> %s (%d frames, %.1f s)' % (a.label, cname, out, len(seq), time.time() - t0), flush=True)
    print('AB_RENDER_DONE %s %.1f s total' % (a.label, time.time() - t_start), flush=True)


if __name__ == '__main__':
    main()
