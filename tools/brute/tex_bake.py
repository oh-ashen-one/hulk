"""Bake Brute vein + cloth-fold detail into a new tangent-space normal map.

Run (from the repo root, ~1.5 min on the M3 Ultra):
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup \
      --python tools/brute/tex_bake.py -- --res 2048 --samples 16 [--ss 3]
then (v2) seam erasure, system python:  python3 tools/brute/tex_seams.py
(tex_seamdata.py must have been run once to create seam_data.npz)
QA renders: tools/brute/tex_render.py (+ tex_sheet.py for comparison sheets,
tex_findseam.py for vein/UV-seam crossing close-ups 'seam0..')
v2: detail is baked as a WORLD-space normal with ADJACENT_FACES padding at
SS=4 and converted to each island's tangent frame in numpy (see the
'seam-continuous baking' block), then box-filtered; tex_seams.py removes the
remaining bilinear seam mismatch.

Pipeline
  1. tex_common: load bind-pose mesh, compute region attributes from skin weights.
  2. Procedural 3D height (world space, continuous across UV seams):
       veins  = iso-contours of a smooth noise compressed along the per-vertex
                limb direction (limb_dir, about limb_ctr), calibre normalised by
                the surface gradient, orientation-filtered (opens loops into
                tapering ends), gated into branches; two layers (trunks +
                limb-only branches), masked by vein_amt (and not on the shorts)
       cloth  = soft horizontal/diagonal folds + basket-weave micro texture +
                torn-hem fray, masked by purple(D) * shorts_v
  3. Perturbed normal by central finite differences of the height along the
     UV tangent frame; Cycles bake NORMAL (tangent, OpenGL +Y) at SS x RES and
     box-filter down (Cycles bakes one point per texel -> no AA otherwise)
     -> pure *detail* normal map (float).
  4. Bake EMIT vein mask and shorts mask.
  5. Combine detail with the ORIGINAL Customuse N via Reoriented Normal Mapping,
     keeping original texels bit-exact wherever no detail was added.
Outputs (~/hulk-scratch/brute_tex/): T_Brute_Normal.png, T_Brute_Veins.png,
  detail_normal.npy (float16 detail-only normal), mask_shorts.png
"""
import sys, os, importlib
import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tex_common as tc
importlib.reload(tc)

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
RES = int(argv[argv.index('--res') + 1]) if '--res' in argv else 2048
SAMPLES = int(argv[argv.index('--samples') + 1]) if '--samples' in argv else 16
MARGIN = 16
DETAIL_PAD = 4          # texels of seam-continuous padding around islands (keeps 84%+ texels untouched)
DEBUG_SOCKETS = []
SUFFIX = argv[argv.index('--suffix') + 1] if '--suffix' in argv else ''
DEBUG = '--debug' in argv
SS = int(argv[argv.index('--ss') + 1]) if '--ss' in argv else 4   # bake supersampling

# ---- tunables (world units; character is ~2.37 m tall) -------------------
VEIN_H = 0.0055        # main vein raise
VEIN2_H = 0.0028       # secondary branch raise
FOLD_H = 0.010         # shorts fold depth
WEAVE_H = 0.00017      # woven micro texture
HEM_THREAD_H = 0.0034  # frayed loose threads at the leg openings
HEM_RAG_H = 0.0032     # ragged rolled edge
HEM_RIP_H = 0.0055     # rip slit depth (lips raised 0.45x)
GRAD_FLOOR = 1.5       # contour-gradient floor (1/m): stabilises vein junctions
VEIN_SCALE = 12.0      # noise scale across the vessel run (higher = more vessels)
VEIN_STRETCH = 8.0     # elongation along the limb
VOR_SCALE = 11.0       # main network cells per metre (across the limb)
VOR_W = 0.07           # main vessel half-width in cell units (~6 mm)
VEIN_HW = 0.0120       # main vessel half-width (m); branches 0.6x
FOLD_F = 60.0          # fold frequency (rad / m)
WEAVE_F = 700.0        # weave frequency (rad / m) ~9 mm repeat (>=4 texels @2048)
FD_E = 0.0015          # finite-difference step (m) ~ texel (2 mm @2048)


class G:
    """Tiny node-graph helper."""
    def __init__(self, nt):
        self.nt = nt
        self.x = 0

    def node(self, t, **kw):
        n = self.nt.nodes.new(t)
        n.location = (self.x, 0); self.x += 40
        for k, v in kw.items():
            if k.startswith('in_'):
                key = k[3:]
                key = int(key) if key.isdigit() else key.replace('__', ' ')
                n.inputs[key].default_value = v
            else:
                setattr(n, k, v)
        return n

    def link(self, a, b):
        self.nt.links.new(a, b)

    def math(self, op, a, b=None, c=None, clamp=False):
        n = self.node('ShaderNodeMath', operation=op, use_clamp=clamp)
        for i, v in enumerate((a, b, c)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                self.link(v, n.inputs[i])
        return n.outputs[0]

    def vmath(self, op, a, b=None):
        if op == 'SCALE_V':
            n = self.node('ShaderNodeVectorMath', operation='SCALE')
            self.link(a, n.inputs[0])
            if isinstance(b, (int, float)):
                n.inputs['Scale'].default_value = b
            else:
                self.link(b, n.inputs['Scale'])
            return n.outputs['Vector']
        n = self.node('ShaderNodeVectorMath', operation=op)
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (tuple, list)):
                n.inputs[i].default_value = v
            else:
                self.link(v, n.inputs[i])
        return n.outputs['Value'] if op in ('DOT_PRODUCT', 'LENGTH', 'DISTANCE') else n.outputs['Vector']

    def smooth(self, e0, e1, x):
        n = self.node('ShaderNodeMapRange', interpolation_type='SMOOTHSTEP', clamp=True)
        n.inputs['From Min'].default_value = e0
        n.inputs['From Max'].default_value = e1
        self.link(x, n.inputs['Value'])
        return n.outputs['Result']

    def attr(self, name):
        n = self.node('ShaderNodeAttribute', attribute_type='GEOMETRY', attribute_name=name)
        return n.outputs['Fac']

    def noise(self, vec, scale, detail=2.0, rough=0.5, out='Fac'):
        n = self.node('ShaderNodeTexNoise', noise_dimensions='3D')
        n.inputs['Scale'].default_value = scale
        n.inputs['Detail'].default_value = detail
        n.inputs['Roughness'].default_value = rough
        self.link(vec, n.inputs['Vector'])
        return n.outputs[out]

    def edge(self, vec, scale, rand=1.0):
        n = self.node('ShaderNodeTexVoronoi', voronoi_dimensions='3D', feature='DISTANCE_TO_EDGE')
        n.inputs['Scale'].default_value = scale
        n.inputs['Randomness'].default_value = rand
        self.link(vec, n.inputs['Vector'])
        return n.outputs['Distance']


CTR = []


def aniso(g, P, d, stretch):
    """Compress coordinates along unit vector d by 1/stretch (vessels run along d),
    about the local limb pivot so a slowly turning d does not shear the pattern."""
    L = g.vmath('SUBTRACT', P, CTR[0])
    pd = g.vmath('DOT_PRODUCT', L, d)
    k = g.math('MULTIPLY', pd, 1.0 - 1.0 / stretch)
    return g.vmath('ADD', g.vmath('SUBTRACT', L, g.vmath('SCALE_V', d, k)), g.vmath('SCALE_V', CTR[0], 0.5))


def tube(g, r, width):
    """distance r -> soft rounded vessel cross-section 0..1: (1 - t^2)^2,
    zero slope at the rim so the vein melts into the skin (no aliasing step)."""
    t = g.math('MINIMUM', g.math('DIVIDE', r, width), 1.0)
    a = g.math('SUBTRACT', 1.0, g.math('MULTIPLY', t, t))
    return g.math('MULTIPLY', a, a)


def vein_contour(g, P, T, Bv, d, stretch, scale, half_w, offset, gate_lo, gate_scale, seed, cos_lo=0.55, cos_hi=0.85, gate_w=0.16):
    """Vessels = iso-contour n=0.5 of a smooth anisotropic noise. The contour
    distance is normalised by the surface gradient (|n-.5| / |grad n|) so the
    calibre is in true metres and stays even; runs merge/split organically."""
    E = 0.003
    def field(p):
        q = g.vmath('ADD', aniso(g, p, d, stretch), offset)
        w = g.noise(q, scale * 0.45, 1.0, 0.5, out='Color')
        w = g.vmath('SUBTRACT', w, (0.5, 0.5, 0.5))
        q = g.vmath('ADD', q, g.vmath('SCALE_V', w, 0.22 / scale))
        return g.noise(q, scale, 0.0, 0.5)
    n0 = field(P)
    # central differences: frame-independent across UV islands (no seam notches)
    d1 = g.math('MULTIPLY', g.math('SUBTRACT', field(g.vmath('ADD', P, g.vmath('SCALE_V', T, E))),
                                   field(g.vmath('SUBTRACT', P, g.vmath('SCALE_V', T, E)))), 0.5)
    d2 = g.math('MULTIPLY', g.math('SUBTRACT', field(g.vmath('ADD', P, g.vmath('SCALE_V', Bv, E))),
                                   field(g.vmath('SUBTRACT', P, g.vmath('SCALE_V', Bv, E)))), 0.5)
    grad = g.math('DIVIDE', g.math('SQRT', g.math('MULTIPLY_ADD', d1, d1, g.math('MULTIPLY', d2, d2))), E)
    DEBUG_SOCKETS.append(grad)
    # gradient floor: near saddles (grad -> 0) the contour distance is 0/0 and the
    # junction topology becomes numerically unstable; a floor turns saddles into
    # a soft confluence blob instead of a pinched, flickering X.
    r = g.math('DIVIDE', g.math('ABSOLUTE', g.math('SUBTRACT', n0, 0.5)), g.math('MAXIMUM', grad, GRAD_FLOOR))
    q0 = g.vmath('ADD', aniso(g, P, d, stretch), offset)
    cal = g.noise(g.vmath('ADD', q0, (13.1 + seed, 7.7, 3.3)), scale * 0.5, 0.0)
    wid = g.math('MULTIPLY', g.math('MULTIPLY_ADD', cal, 0.6, 0.75), half_w)
    prof = tube(g, r, wid)
    # orientation filter: keep runs roughly along d (gradient ~ perpendicular to d);
    # this opens up closed contour loops / U-turns into tapering vessel ends.
    dT = g.vmath('DOT_PRODUCT', d, T)
    dB = g.vmath('DOT_PRODUCT', d, Bv)
    gd = g.math('ABSOLUTE', g.math('MULTIPLY_ADD', d1, dT, g.math('MULTIPLY', d2, dB)))
    gl = g.math('MULTIPLY', g.math('SQRT', g.math('MULTIPLY_ADD', d1, d1, g.math('MULTIPLY', d2, d2))),
                g.math('SQRT', g.math('MULTIPLY_ADD', dT, dT, g.math('MULTIPLY', dB, dB))))
    cosang = g.math('DIVIDE', gd, g.math('MAXIMUM', gl, 1e-6))
    keep = g.math('SUBTRACT', 1.0, g.smooth(cos_lo, cos_hi, cosang))
    # gradient direction is meaningless at saddles: let the filter pass there
    conf = g.smooth(0.25, 0.8, grad)   # only true saddles (grad ~ 0), not elongated loop tips
    keep = g.math('ADD', g.math('MULTIPLY', keep, conf), g.math('SUBTRACT', 1.0, conf))
    prof = g.math('MULTIPLY', prof, keep)
    gl0 = gate_lo
    gn = g.noise(g.vmath('ADD', q0, (41.0 + seed, 5.0, 17.0)), gate_scale, 1.0)
    if isinstance(gl0, (int, float)):
        gate = g.smooth(gl0, gl0 + gate_w, gn)
    else:   # spatially varying threshold socket
        gate = g.math('MINIMUM', g.math('MAXIMUM', g.math('DIVIDE', g.math('SUBTRACT', gn, gl0), gate_w), 0.0), 1.0)
        gate = g.math('MULTIPLY', g.math('MULTIPLY', gate, gate), g.math('MULTIPLY_ADD', gate, -2.0, 3.0))
    return g.math('MULTIPLY', prof, gate)


class Masks:
    pass


def build_masks(g):
    m = Masks()
    tco = g.node('ShaderNodeTexCoord')
    m.P = tco.outputs['Object']
    dimg = bpy.data.images.load(tc.TEX + 'SM_Character_Brute_D.png', check_existing=True)
    dtex = g.node('ShaderNodeTexImage', image=dimg, interpolation='Linear')
    g.link(tco.outputs['UV'], dtex.inputs['Vector'])
    sep = g.node('ShaderNodeSeparateColor')
    g.link(dtex.outputs['Color'], sep.inputs['Color'])
    R, Gc, B = sep.outputs[0], sep.outputs[1], sep.outputs[2]
    m.skin = g.smooth(0.0, 0.035, g.math('SUBTRACT', Gc, g.math('MAXIMUM', R, B)))
    purple = g.smooth(0.004, 0.03, g.math('MINIMUM', g.math('SUBTRACT', B, Gc), g.math('SUBTRACT', R, Gc)))
    amt = g.attr('vein_amt')
    # NOTE: no per-texel D-based skin test for veins: painted highlights sit
    # near the green/red threshold and made the veins stipple. Vertex-level
    # masks only (shorts excluded via the smoothed shorts_v attribute).
    noshorts = g.math('SUBTRACT', 1.0, g.smooth(0.05, 0.3, g.attr('shorts_v')))
    m.region = g.math('MULTIPLY', g.smooth(0.08, 0.6, amt), noshorts)
    m.sec_region = g.math('MULTIPLY', g.math('MULTIPLY', g.smooth(0.4, 0.9, amt), g.smooth(0.2, 0.7, g.attr('vein_sec'))), noshorts)
    an = g.node('ShaderNodeAttribute', attribute_type='GEOMETRY', attribute_name='limb_dir')
    m.d = g.vmath('NORMALIZE', an.outputs['Vector'])
    cn = g.node('ShaderNodeAttribute', attribute_type='GEOMETRY', attribute_name='limb_ctr')
    CTR[:] = [cn.outputs['Vector']]
    sv = g.math('MINIMUM', g.math('MULTIPLY', g.attr('shorts_v'), 2.5), 1.0)
    m.shorts = g.math('MULTIPLY', purple, sv)
    m.hem = g.attr('hem')
    m.hem_d = g.attr('hem_d')
    fore = g.smooth(0.2, 0.8, g.attr('vein_sec'))
    m.gate_main = g.math('MULTIPLY_ADD', g.math('SUBTRACT', 1.0, fore), 0.09, 0.35)
    return m


def height_at(g, m, P):
    """Total height (world metres) at position P; returns (height, vein01)."""
    # trunks: low-frequency gate -> long runs (no short fragments); away from the
    # forearm/hand the gate threshold rises -> fewer vessels on biceps/shoulders
    main = vein_contour(g, P, m.T, m.B, m.d, VEIN_STRETCH, VEIN_SCALE, VEIN_HW, (0.0, 0.0, 0.0), m.gate_main, 1.5, 0.0,
                        gate_w=0.12)
    sec = vein_contour(g, P, m.T, m.B, m.d, 5.0, VEIN_SCALE * 1.6, VEIN_HW * 0.62, (3.7, 9.1, 1.3), 0.47, 2.2, 5.0, 0.65, 0.92,
                       gate_w=0.12)
    vm = g.math('MULTIPLY', main, m.region)
    vs = g.math('MULTIPLY', sec, m.sec_region)
    vein01 = g.math('MAXIMUM', vm, g.math('MULTIPLY', vs, 0.7))
    vh = g.math('ADD', g.math('MULTIPLY', vm, VEIN_H), g.math('MULTIPLY', vs, VEIN2_H))

    # ---------------- shorts cloth ----------------
    sxyz = g.node('ShaderNodeSeparateXYZ'); g.link(P, sxyz.inputs['Vector'])
    X, Y, Z = sxyz.outputs[0], sxyz.outputs[1], sxyz.outputs[2]
    Hc = g.math('ADD', X, Y)            # horizontal coordinate around the body
    fw = g.noise(P, 3.5, 3.0, 0.55)
    def band(coord, freq, phase_warp):
        a = g.math('MULTIPLY_ADD', coord, freq, g.math('MULTIPLY', fw, phase_warp))
        # broad rounded ridge, narrow crease valley
        return g.math('POWER', g.math('MULTIPLY_ADD', g.math('SINE', a), 0.5, 0.5), 0.75)
    f1 = band(g.math('ADD', Z, g.math('MULTIPLY', Hc, 0.12)), FOLD_F, 9.0)          # near-horizontal
    f2 = band(g.math('ADD', Z, g.math('MULTIPLY', Hc, 0.9)), FOLD_F * 0.85, 7.0)    # diagonal pull
    f3 = band(g.math('SUBTRACT', Z, g.math('MULTIPLY', Hc, 0.75)), FOLD_F * 0.8, 7.0)
    fm1 = g.smooth(0.40, 0.60, g.noise(g.vmath('ADD', P, (2.0, 0.0, 0.0)), 2.6, 1.0))
    # one diagonal direction per region (no criss-cross scallops)
    side = g.smooth(0.42, 0.58, g.noise(g.vmath('ADD', P, (0.0, 7.0, 0.0)), 1.8, 0.0))
    diag = g.math('ADD', g.math('MULTIPLY', f2, side), g.math('MULTIPLY', f3, g.math('SUBTRACT', 1.0, side)))
    fmd = g.smooth(0.44, 0.62, g.noise(g.vmath('ADD', P, (0.0, 0.0, 5.0)), 2.2, 1.0))
    fmd = g.math('MULTIPLY', fmd, g.math('SUBTRACT', 1.0, g.math('MULTIPLY', fm1, 0.8)))
    folds = g.math('MAXIMUM', g.math('MULTIPLY', f1, fm1), g.math('MULTIPLY', diag, fmd))
    folds = g.math('ADD', folds, g.math('MULTIPLY', g.noise(P, 9.0, 2.0, 0.5), 0.25))
    # woven micro texture: basket weave (warp/weft threads alternating over/under) + slubs
    t1 = g.math('MULTIPLY_ADD', g.math('SINE', g.math('MULTIPLY', Z, WEAVE_F)), 0.5, 0.5)
    t2 = g.math('MULTIPLY_ADD', g.math('SINE', g.math('MULTIPLY', Hc, WEAVE_F / 1.414)), 0.5, 0.5)
    chk = g.math('MULTIPLY', g.math('SINE', g.math('MULTIPLY', Z, WEAVE_F * 0.5)),
                 g.math('SINE', g.math('MULTIPLY', Hc, WEAVE_F * 0.5 / 1.414)))
    chk = g.smooth(-0.25, 0.25, chk)
    weave = g.math('ADD', g.math('MULTIPLY', t1, chk), g.math('MULTIPLY', t2, g.math('SUBTRACT', 1.0, chk)))
    slub = g.noise(g.vmath('MULTIPLY', P, (1.0, 1.0, 5.0)), 40.0, 1.0)
    weave = g.math('MULTIPLY', weave, g.math('MULTIPLY_ADD', slub, 0.6, 0.7))
    # torn hem (leg openings only, driven by hem_d = distance from the cut edge):
    #   * frayed band: dense loose threads hanging along the leg (vertical), random
    #     lengths 1-5 cm, densest right at the edge
    #   * ragged rolled edge lumps in the first ~1 cm
    #   * a few vertical rips: deep slit with raised lips running up from the edge
    hd = m.hem_d
    tq = g.vmath('MULTIPLY', P, (1.0, 1.0, 0.04))                # columns along Z
    tn = g.noise(g.vmath('MULTIPLY', P, (1.0, 1.0, 0.06)), 95.0, 1.0, 0.5)
    thread = g.math('SUBTRACT', 1.0, g.smooth(0.0, 0.09, g.math('ABSOLUTE', g.math('SUBTRACT', tn, 0.5))))
    tn2 = g.noise(g.vmath('ADD', g.vmath('MULTIPLY', P, (1.0, 1.0, 0.05)), (3.0, 1.0, 0.0)), 140.0, 1.0, 0.5)
    thread2 = g.math('SUBTRACT', 1.0, g.smooth(0.0, 0.07, g.math('ABSOLUTE', g.math('SUBTRACT', tn2, 0.5))))
    thread = g.math('MAXIMUM', thread, g.math('MULTIPLY', thread2, 0.7))
    tlen = g.math('MULTIPLY_ADD', g.noise(tq, 60.0, 1.0), 0.08, -0.01)   # ~1..6 cm per column
    tfade = g.math('MINIMUM', g.math('DIVIDE', hd, g.math('MAXIMUM', tlen, 0.008)), 1.0)
    thread = g.math('MULTIPLY', thread, g.math('SUBTRACT', 1.0, g.math('MULTIPLY', tfade, tfade)))
    edge = g.math('SUBTRACT', 1.0, g.smooth(0.0, 0.012, hd))
    rag = g.math('MULTIPLY', g.noise(P, 38.0, 3.0, 0.6), edge)
    # rips: rare columns, slit length 3-9 cm
    ripcol = g.smooth(0.60, 0.64, g.noise(g.vmath('MULTIPLY', P, (1.0, 1.0, 0.05)), 9.0, 0.0))
    sn = g.noise(g.vmath('MULTIPLY', P, (1.0, 1.0, 0.12)), 30.0, 1.0, 0.5)
    sdist = g.math('ABSOLUTE', g.math('SUBTRACT', sn, 0.5))
    slit = g.math('SUBTRACT', 1.0, g.smooth(0.0, 0.035, sdist))
    lips = g.math('SUBTRACT', 1.0, g.smooth(0.02, 0.09, sdist))
    rlen = g.math('MULTIPLY_ADD', g.noise(g.vmath('MULTIPLY', P, (1.0, 1.0, 0.05)), 17.0, 0.0), 0.10, -0.02)
    rfade = g.math('SUBTRACT', 1.0, g.smooth(0.0, 1.0, g.math('DIVIDE', hd, g.math('MAXIMUM', rlen, 0.01))))
    rip = g.math('MULTIPLY', g.math('MULTIPLY', ripcol, rfade),
                 g.math('SUBTRACT', g.math('MULTIPLY', lips, 0.45), slit))
    fray = g.math('ADD', g.math('MULTIPLY', thread, HEM_THREAD_H),
                  g.math('ADD', g.math('MULTIPLY', rag, HEM_RAG_H), g.math('MULTIPLY', rip, HEM_RIP_H)))
    fray = g.math('MULTIPLY', fray, m.hem)
    # fraying replaces the clean weave right at the cut edge
    weave = g.math('MULTIPLY', weave, g.math('SUBTRACT', 1.0, g.math('MULTIPLY', edge, m.hem)))
    ch = g.math('ADD', g.math('MULTIPLY', folds, FOLD_H),
                g.math('ADD', g.math('MULTIPLY', weave, WEAVE_H), fray))
    ch = g.math('MULTIPLY', ch, m.shorts)
    return g.math('ADD', vh, ch), vein01


def build_normal(nt):
    """Finite-difference normal perturbation along the UV tangent frame
    (more robust than the Bump node during baking)."""
    g = G(nt)
    m = build_masks(g)
    geo = g.node('ShaderNodeNewGeometry')
    N = geo.outputs['Normal']
    # Seam-free local frame: built from the welded, smooth vessel direction
    # (limb_dir), NOT from the per-island UV tangent, so every quantity is the
    # same on both sides of a UV seam. The result is a world-space normal; the
    # bake converts it to each island's tangent space.
    T = g.vmath('ADD', m.d, (0.013, 0.021, 0.007))
    T = g.vmath('NORMALIZE', g.vmath('SUBTRACT', T, g.vmath('SCALE_V', N, g.vmath('DOT_PRODUCT', T, N))))
    Bv = g.vmath('CROSS_PRODUCT', N, T)
    m.T, m.B = T, Bv
    # central differences (frame-independent: no half-step bias that would
    # differ between UV islands with different tangent frames -> no seam notch)
    _, vein01 = height_at(g, m, m.P)
    hTp, _ = height_at(g, m, g.vmath('ADD', m.P, g.vmath('SCALE_V', T, FD_E)))
    hTm, _ = height_at(g, m, g.vmath('SUBTRACT', m.P, g.vmath('SCALE_V', T, FD_E)))
    hBp, _ = height_at(g, m, g.vmath('ADD', m.P, g.vmath('SCALE_V', Bv, FD_E)))
    hBm, _ = height_at(g, m, g.vmath('SUBTRACT', m.P, g.vmath('SCALE_V', Bv, FD_E)))
    g1 = g.math('DIVIDE', g.math('SUBTRACT', hTp, hTm), 2 * FD_E)
    g2 = g.math('DIVIDE', g.math('SUBTRACT', hBp, hBm), 2 * FD_E)
    nn = g.vmath('SUBTRACT', N, g.vmath('ADD', g.vmath('SCALE_V', T, g1), g.vmath('SCALE_V', Bv, g2)))
    nn = g.vmath('NORMALIZE', nn)
    return nn, vein01, m.shorts


def setup_cycles(samples):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type = 'METAL'
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
        sc.cycles.device = 'GPU'
    except Exception as e:
        print('[tex] GPU setup failed, CPU', e)
    sc.cycles.samples = samples
    sc.cycles.use_denoising = False


def bake_pass(obj, mat, img, kind, shader_out, margin=0, margin_type='EXTEND'):
    """Bake into img and return the raw float array (H, W, 4)."""
    nt = mat.node_tree
    out = [n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'][0]
    for l in list(out.inputs['Surface'].links):
        nt.links.remove(l)
    nt.links.new(shader_out, out.inputs['Surface'])
    tn = nt.nodes.get('BAKE_TARGET') or nt.nodes.new('ShaderNodeTexImage')
    tn.name = 'BAKE_TARGET'
    tn.image = img
    for n in nt.nodes:
        n.select = False
    tn.select = True
    nt.nodes.active = tn
    sc = bpy.context.scene
    sc.render.bake.margin = margin
    sc.render.bake.margin_type = margin_type
    sc.render.bake.use_clear = True
    if kind == 'NORMAL':
        sc.render.bake.normal_space = 'TANGENT'
        sc.render.bake.normal_r, sc.render.bake.normal_g, sc.render.bake.normal_b = 'POS_X', 'POS_Y', 'POS_Z'
    bpy.ops.object.bake(type=kind, margin=margin, use_clear=True)
    a = np.empty(img.size[0] * img.size[1] * 4, np.float32)
    img.pixels.foreach_get(a)
    return a.reshape(img.size[1], img.size[0], 4)


# ------------------------------------------------- seam-continuous baking
# Why: a tangent-space bake can only pad islands by repeating border texels
# (EXTEND) - the frames of neighbouring islands differ, so content cannot be
# copied across seams. With bilinear sampling (and the supersample filter) the
# last half texel of every island then shows a flattened / shifted strip, which
# is visible as a thin line where a steep vein flank crosses a seam.
# Fix: bake the detail as a WORLD-space normal (frame-free) with
# ADJACENT_FACES padding, i.e. each island's margin is filled with the true
# continuation of the surface across its seam; bake the island's own tangent
# frame (T, N, bitangent sign) with EXTEND padding; convert world->tangent per
# hi-res texel ourselves (identical maths to Blender's tangent bake: x=n.T,
# y=n.(s*NxT), z=n.N); then a plain box filter down to RES is unbiased.

def _enc(g, v):
    n = g.node('ShaderNodeVectorMath', operation='MULTIPLY_ADD')
    g.link(v, n.inputs[0]); n.inputs[1].default_value = (0.5, 0.5, 0.5); n.inputs[2].default_value = (0.5, 0.5, 0.5)
    return n.outputs[0]


def decode(a):
    return a[..., :3] * 2.0 - 1.0


def box(a):
    """Box filter SS x SS hi-res texels down to RES (area filter)."""
    C = a.shape[-1]
    return a.reshape(RES, SS, RES, SS, C).mean((1, 3))


def main():
    tc.clear_scene()
    obj = tc.load_mesh()
    tc.compute_attributes(obj)
    setup_cycles(SAMPLES)
    mat = bpy.data.materials.new('BruteBake')
    obj.data.materials.clear(); obj.data.materials.append(mat)
    nt = mat.node_tree
    nn, vmask, smask = build_normal(nt)
    bsdf = nt.nodes.get('Principled BSDF') or nt.nodes.new('ShaderNodeBsdfPrincipled')
    nt.links.new(nn, bsdf.inputs['Normal'])
    em = nt.nodes.new('ShaderNodeEmission')
    em2 = nt.nodes.new('ShaderNodeEmission')
    nt.links.new(vmask, em.inputs['Color'])
    nt.links.new(smask, em2.inputs['Color'])

    def mk(name, flt):
        im = bpy.data.images.new(name, RES * SS, RES * SS, alpha=False, float_buffer=flt)
        im.colorspace_settings.name = 'Non-Color'
        return im
    if DEBUG:   # bake main-layer |grad n| / 40 for inspection and stop
        emd = nt.nodes.new('ShaderNodeEmission')
        nt.links.new(nt.nodes.new('ShaderNodeMath').outputs[0], emd.inputs['Color'])
        mm = emd.inputs['Color'].links[0].from_node; mm.operation = 'MULTIPLY'; mm.inputs[1].default_value = 1 / 40.0
        nt.links.new(DEBUG_SOCKETS[0], mm.inputs[0])
        a = bake_pass(obj, mat, mk('dbg', True), 'EMIT', emd.outputs['Emission'])
        np.save(tc.OUT + 'dbg_grad.npy', a[..., 0])
        print('[tex] grad pct', np.percentile(a[..., 0] * 40, [1, 10, 50, 90, 99]))
        return
    g = G(nt)
    pad = DETAIL_PAD * SS
    HI = RES * SS
    # 1) detail as world-space normal + masks, padded across seams
    nn01 = _enc(g, nn)
    emn = nt.nodes.new('ShaderNodeEmission'); nt.links.new(nn01, emn.inputs['Color'])
    wn = bake_pass(obj, mat, mk('wnormal', True), 'EMIT', emn.outputs['Emission'], pad, 'ADJACENT_FACES')
    cm = nt.nodes.new('ShaderNodeCombineXYZ')
    nt.links.new(vmask, cm.inputs[0]); nt.links.new(smask, cm.inputs[1]); cm.inputs[2].default_value = 1.0
    emm = nt.nodes.new('ShaderNodeEmission'); nt.links.new(cm.outputs[0], emm.inputs['Color'])
    msk = bake_pass(obj, mat, mk('masks', True), 'EMIT', emm.outputs['Emission'], pad, 'ADJACENT_FACES')
    print('[tex] detail + masks baked')
    if '--detail-png' in argv:   # diagnostics: object-space (world) normal map
        np.save(tc.OUT + 'wnormal_lo.npy', box(wn[..., :3]).astype(np.float16))
    # 2) each island's own tangent frame, EXTEND-padded (cheap shaders)
    tan = g.node('ShaderNodeTangent', direction_type='UV_MAP', uv_map='UVMap')
    geo = g.node('ShaderNodeNewGeometry')
    emt = nt.nodes.new('ShaderNodeEmission'); nt.links.new(_enc(g, tan.outputs['Tangent']), emt.inputs['Color'])
    Tm = decode(bake_pass(obj, mat, mk('T', True), 'EMIT', emt.outputs['Emission'], pad, 'EXTEND'))
    emN = nt.nodes.new('ShaderNodeEmission'); nt.links.new(_enc(g, geo.outputs['Normal']), emN.inputs['Color'])
    Nm = decode(bake_pass(obj, mat, mk('N', True), 'EMIT', emN.outputs['Emission'], pad, 'EXTEND'))
    # bitangent sign: tangent-bake a normal tilted toward +cross(N,T); y>0 <=> sign=+1
    tilt = g.vmath('NORMALIZE', g.vmath('ADD', geo.outputs['Normal'],
                   g.vmath('SCALE_V', g.vmath('CROSS_PRODUCT', geo.outputs['Normal'], tan.outputs['Tangent']), 0.5)))
    bs2 = nt.nodes.new('ShaderNodeBsdfDiffuse'); nt.links.new(tilt, bs2.inputs['Normal'])
    sg = bake_pass(obj, mat, mk('S', True), 'NORMAL', bs2.outputs['BSDF'], pad, 'EXTEND')
    sign = np.where(sg[..., 1] >= 0.5, 1.0, -1.0).astype(np.float32)
    del sg
    # 3) world -> tangent per hi-res texel (in row chunks), then box filter
    det_hi = np.empty((HI, HI, 3), np.float32)
    for r0 in range(0, HI, 1024):
        sl = slice(r0, r0 + 1024)
        n_w = decode(wn[sl]); n_w /= np.linalg.norm(n_w, axis=-1, keepdims=True) + 1e-9
        T_ = Tm[sl]; N_ = Nm[sl]
        B_ = np.cross(N_, T_) * sign[sl][..., None]
        det_hi[sl] = np.stack([(n_w * T_).sum(-1), (n_w * B_).sum(-1), (n_w * N_).sum(-1)], -1)
    del wn, Tm, Nm, sign
    valid_hi = msk[..., 2] > 0.5
    det_hi[~valid_hi] = (0.0, 0.0, 1.0)
    det = box(det_hi); del det_hi
    det /= np.linalg.norm(det, axis=-1, keepdims=True) + 1e-9
    # a handful of padding texels in gaps between islands can pair one island's
    # frame with a neighbour's continuation -> clamp to the upper hemisphere
    det[..., 2] = np.maximum(det[..., 2], 0.25)
    det /= np.linalg.norm(det, axis=-1, keepdims=True) + 1e-9
    det = np.concatenate([det * 0.5 + 0.5, np.ones_like(det[..., :1])], -1)
    mlo = box(msk); del msk
    valid = mlo[..., 2] > 0.999      # fully inside islands + padding
    vm = mlo[..., 0:1]; sm = mlo[..., 1:2]
    np.save(tc.OUT + 'detail_normal.npy', det[..., :3].astype(np.float16))

    # ---- combine with original N (RNM) ----
    from_img = bpy.data.images.load(tc.TEX + 'SM_Character_Brute_N.png')
    from_img.colorspace_settings.name = 'Non-Color'
    if from_img.size[0] != RES:
        from_img.scale(RES, RES)
    base = np.array(from_img.pixels[:], np.float32).reshape(RES, RES, 4)
    t = base[..., :3] * 2 - 1
    t[..., 2] += 1
    u = det[..., :3] * np.array([-2, -2, 2]) + np.array([1, 1, -1])
    r = t * (np.sum(t * u, -1, keepdims=True) / np.maximum(t[..., 2:3], 1e-4)) - u
    r /= np.linalg.norm(r, axis=-1, keepdims=True) + 1e-9
    r[..., 2] = np.maximum(r[..., 2], 0.2)
    r /= np.linalg.norm(r, axis=-1, keepdims=True) + 1e-9
    newc = r * 0.5 + 0.5
    flat = np.abs(det[..., :3] - np.array([0.5, 0.5, 1.0])).max(-1) < 1.5 / 255
    flat |= ~valid                      # outside islands + padding: keep the source texel
    newc[flat] = base[..., :3][flat]
    outpx = np.concatenate([newc, np.ones_like(newc[..., :1])], -1)
    # float results for the seam-erasure pass (tools/brute/tex_seams.py), Blender bottom-up rows
    np.save(tc.OUT + f'final_normal_f32{SUFFIX}.npy', newc.astype(np.float32))
    np.save(tc.OUT + f'final_flat{SUFFIX}.npy', flat)
    np.save(tc.OUT + f'final_veins_f32{SUFFIX}.npy', np.clip(vm[..., 0] * 1.25, 0, 1).astype(np.float32))
    vmc = np.clip(vm[..., 0] * 1.25, 0, 1)

    def save(name, arr, gray=False):
        im = bpy.data.images.new(name, RES, RES, alpha=False)
        im.colorspace_settings.name = 'Non-Color'
        if gray:
            arr = np.concatenate([np.repeat(arr[..., None], 3, -1), np.ones_like(arr[..., None])], -1)
        im.pixels.foreach_set(arr.astype(np.float32).ravel())
        im.filepath_raw = tc.OUT + name
        im.file_format = 'PNG'
        bpy.context.scene.render.image_settings.color_depth = '8'
        im.save()
        print('[tex] wrote', tc.OUT + name)
    sfx = SUFFIX
    save(f'T_Brute_Normal{sfx}.png', outpx)
    save(f'T_Brute_Veins{sfx}.png', vmc, gray=True)
    save(f'mask_shorts{sfx}.png', np.clip(sm[..., 0], 0, 1), gray=True)
    if '--detail-png' in argv:   # detail-only normal map (flat base) for diagnostics
        dd = det.copy(); dd[..., 3] = 1
        save(f'detail_only{sfx}.png', dd)
    print('[tex] changed texels %.2f%%' % (100.0 * (~flat).mean()))


if __name__ == '__main__':
    main()
