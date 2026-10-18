"""Before/after QA renders for the Brute normal map.

Run:
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup \
      --python tools/brute/tex_render.py -- [--normal PATH] [--tag after] [--views a,b] [--res 700]
Renders base colour D + given normal map (default: new T_Brute_Normal.png),
Principled, studio area lights, Cycles. Output: ~/hulk-scratch/brute_tex/renders/<tag>_<view>.png
"""
import sys, os, importlib, math
import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tex_common as tc
importlib.reload(tc)

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
def arg(k, d):
    return argv[argv.index(k) + 1] if k in argv else d
NORMAL = arg('--normal', tc.OUT + 'T_Brute_Normal.png')
TAG = arg('--tag', 'after')
RES = int(arg('--res', '700'))
VIEWS = arg('--views', '')
STRENGTH = float(arg('--strength', '1.0'))
ATTR = arg('--attr', '')
LIVE = '--live' in argv
OUTD = tc.OUT + 'renders/'
os.makedirs(OUTD, exist_ok=True)


def centroid(obj, names):
    me = obj.data
    gi = {g.name: g.index for g in obj.vertex_groups}
    want = {gi[n] for n in names}
    acc = Vector(); ws = 0.0
    for v in me.vertices:
        for ge in v.groups:
            if ge.group in want and ge.weight > 0.05:
                acc += v.co * ge.weight; ws += ge.weight
    return acc / max(ws, 1e-6)


# view: (target groups, direction from target to camera, distance, lens)
VIEWDEF = {
    'forearm_front': (['LeftForeArm'], (1, 0.15, 0.35), 0.55, 50),
    'forearm_top':   (['LeftForeArm'], (0.25, 0.1, 1), 0.55, 50),
    'forearm_under': (['LeftForeArm'], (0.5, 0.0, -1), 0.55, 50),
    'hand_back':     (['LeftHand'], (0.3, 0.2, 1), 0.45, 50),
    'upperarm':      (['LeftArm'], (1, -0.1, 0.0), 0.6, 50),
    'neck_34':       (['Neck'], (1, 0.8, 0.15), 0.6, 50),
    'chest_front':   (['Spine2'], (1, 0.0, 0.25), 1.0, 50),
    'shorts_front':  (['Hips'], (1, 0.0, 0.05), 1.1, 50),
    'shorts_34':     (['Hips'], (0.7, 0.7, 0.05), 1.1, 50),
    'shorts_back':   (['Hips'], (-1, 0.0, 0.05), 1.1, 50),
    'back':          (['Spine1'], (-1, 0.0, 0.2), 1.4, 50),
    'full_front':    (['Spine'], (1, 0.0, 0.05), 4.2, 50),
    'full_back':     (['Spine'], (-1, 0.0, 0.05), 4.2, 50),
    'full_side':     (['Spine'], (0.2, 1.0, 0.05), 4.2, 50),
}


# pick views: (base view, pixel x/w, pixel y/h, distance, lens) -> ray-cast the base
# camera through that pixel and frame the hit point from along its normal
VIEWPICK = {
    'junction':  ('forearm_front', 330 / 700, 590 / 700, 0.09, 50),   # vein junction on a UV border
    'junction2': ('forearm_front', 470 / 700, 75 / 700, 0.09, 50),
    'hem_front': ('shorts_front', 175 / 700, 625 / 700, 0.40, 50),
    'hem_close': ('shorts_front', 175 / 700, 625 / 700, 0.18, 50),
    'hem_34':    ('shorts_34', 470 / 700, 640 / 700, 0.40, 50),
}


def pick_point(sc, cam, obj, px, py):
    import bpy_extras
    fr = [cam.matrix_world @ v for v in cam.data.view_frame(scene=sc)]
    # view_frame order: top-right, bottom-right, bottom-left, top-left
    tr, br, bl, tl = fr
    top = tl.lerp(tr, px); bot = bl.lerp(br, px)
    target = top.lerp(bot, py)
    o = cam.matrix_world.translation
    dg = bpy.context.evaluated_depsgraph_get()
    hit, loc, nrm, idx, ob, mat = sc.ray_cast(dg, o, (target - o).normalized())
    return loc, nrm


def main():
    tc.clear_scene()
    obj = tc.load_mesh()
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type = 'METAL'; prefs.get_devices()
        for d in prefs.devices:
            d.use = True
        sc.cycles.device = 'GPU'
    except Exception as e:
        print(e)
    sc.cycles.samples = 48
    sc.cycles.use_denoising = True
    sc.render.resolution_x = sc.render.resolution_y = RES
    sc.view_settings.view_transform = 'AgX'
    sc.world = bpy.data.worlds.new('w')
    sc.world.color = (0.05, 0.05, 0.055)

    mat = bpy.data.materials.new('BruteQA')
    obj.data.materials.clear(); obj.data.materials.append(mat)
    nt = mat.node_tree
    bsdf = nt.nodes.get('Principled BSDF')
    d = nt.nodes.new('ShaderNodeTexImage')
    d.image = bpy.data.images.load(arg('--base', tc.TEX + 'SM_Character_Brute_D.png'))
    nt.links.new(d.outputs['Color'], bsdf.inputs['Base Color'])
    n = nt.nodes.new('ShaderNodeTexImage')
    n.image = bpy.data.images.load(NORMAL)
    n.image.colorspace_settings.name = 'Non-Color'
    nm = nt.nodes.new('ShaderNodeNormalMap')
    nm.inputs['Strength'].default_value = STRENGTH
    nt.links.new(n.outputs['Color'], nm.inputs['Color'])
    nt.links.new(nm.outputs['Normal'], bsdf.inputs['Normal'])
    if '--objnormal' in argv:   # decode an object/world-space normal map instead
        for l in list(nm.outputs['Normal'].links):
            nt.links.remove(l)
        vm_ = nt.nodes.new('ShaderNodeVectorMath'); vm_.operation = 'MULTIPLY_ADD'
        vm_.inputs[1].default_value = (2, 2, 2); vm_.inputs[2].default_value = (-1, -1, -1)
        nt.links.new(n.outputs['Color'], vm_.inputs[0])
        vn_ = nt.nodes.new('ShaderNodeVectorMath'); vn_.operation = 'NORMALIZE'
        nt.links.new(vm_.outputs[0], vn_.inputs[0]); nt.links.new(vn_.outputs[0], bsdf.inputs['Normal'])
    if '--live-checker' in argv:   # debug: 3D checker evaluated live (registration test)
        tco = nt.nodes.new('ShaderNodeTexCoord'); ck = nt.nodes.new('ShaderNodeTexChecker')
        ck.inputs['Scale'].default_value = 40
        ck.inputs['Color1'].default_value = (1, 1, 1, 1); ck.inputs['Color2'].default_value = (0, 0, 0, 1)
        nt.links.new(tco.outputs['Object'], ck.inputs['Vector']); nt.links.new(ck.outputs['Color'], bsdf.inputs['Base Color'])
    if LIVE:   # debug: evaluate the procedural detail live (no bake / no normal map)
        import tex_bake as tb
        tc.compute_attributes(obj)
        nn, vm, sm = tb.build_normal(nt)
        if '--live-mask' in argv:
            nt.links.new(vm, bsdf.inputs['Base Color'])
        else:
            nt.links.new(nn, bsdf.inputs['Normal'])
    if ATTR:   # debug: show a mesh attribute (red) over the base colour
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        tc.compute_attributes(obj)
        at = nt.nodes.new('ShaderNodeAttribute'); at.attribute_name = ATTR
        mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'
        nt.links.new(at.outputs['Fac'], mix.inputs['Factor'])
        nt.links.new(d.outputs['Color'], mix.inputs['A'])
        mix.inputs['B'].default_value = (1, 0, 0, 1)
        nt.links.new(mix.outputs['Result'], bsdf.inputs['Base Color'])
    bsdf.inputs['Roughness'].default_value = 0.5
    bsdf.inputs['Specular IOR Level'].default_value = 0.5

    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
    sc.collection.objects.link(cam); sc.camera = cam
    cam.data.clip_start = 0.005
    trk = cam.constraints.new('TRACK_TO')
    tgt = bpy.data.objects.new('tgt', None); sc.collection.objects.link(tgt)
    trk.target = tgt; trk.track_axis = 'TRACK_NEGATIVE_Z'; trk.up_axis = 'UP_Y'

    # key light rides with the camera (upper side, raking), plus fill + rim
    def area(name, energy, size, col=(1, 1, 1)):
        L = bpy.data.lights.new(name, 'AREA'); L.energy = energy; L.size = size; L.color = col
        o = bpy.data.objects.new(name, L); sc.collection.objects.link(o)
        c = o.constraints.new('TRACK_TO'); c.target = tgt; c.track_axis = 'TRACK_NEGATIVE_Z'; c.up_axis = 'UP_Y'
        return o
    key = area('key', 60, 0.4)
    fill = area('fill', 12, 1.5, (0.85, 0.9, 1.0))
    rim = area('rim', 40, 0.6)

    views = VIEWS.split(',') if VIEWS else list(VIEWDEF) + list(VIEWPICK)
    for vn in views:
        if vn.startswith('seam'):   # vein crossing a UV seam (tex_findseam.py), extreme close-up
            import json
            sp = json.load(open(tc.OUT + 'seam_vein_points.json'))[int(vn[4:])]
            c = Vector(sp['co']); nrm = Vector(sp['n']).normalized()
            dist, lens = 0.07, 50
            dv = (nrm + Vector((1, 0, 0.3)) * 0.25).normalized()
        elif vn in VIEWPICK:
            base, px, py, dist, lens = VIEWPICK[vn]
            g0, d0, dist0, l0 = VIEWDEF[base]
            c0 = centroid(obj, g0); dv0 = Vector(d0).normalized()
            tgt.location = c0; cam.location = c0 + dv0 * dist0; cam.data.lens = l0
            bpy.context.view_layer.update()
            c, nrm = pick_point(sc, cam, obj, px, py)
            dv = (nrm.normalized() + dv0 * 0.6).normalized()
        else:
            groups, dirv, dist, lens = VIEWDEF[vn]
            c = centroid(obj, groups)
            dv = Vector(dirv).normalized()
        tgt.location = c
        cam.location = c + dv * dist
        cam.data.lens = lens
        up = Vector((0, 0, 1)) if abs(dv.z) < 0.9 else Vector((1, 0, 0))
        side = dv.cross(up).normalized()
        ld = max(dist, 0.6)   # close-ups keep the lights at a sane distance (no self-occlusion)
        key.location = c + (dv + side * 0.9 + up * 0.8).normalized() * ld * 1.3
        fill.location = c + (dv - side * 1.0).normalized() * ld * 2.0
        rim.location = c + (-dv + up * 0.5 - side * 0.3).normalized() * ld * 1.5
        for o, e in ((key, 60), (fill, 12), (rim, 40)):
            o.data.energy = e * (ld / 0.6) ** 2
        sc.render.filepath = OUTD + f'{TAG}_{vn}.png'
        bpy.ops.render.render(write_still=True)
        print('[tex] render', sc.render.filepath)


if __name__ == '__main__':
    main()
