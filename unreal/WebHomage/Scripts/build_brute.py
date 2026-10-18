# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
# Brute body content: imports the SKINNED Customuse model (tools/brute/rig_brute.py -> brute_skel.fbx) as the skeletal mesh
# /Game/Brute/Body/SK_Brute (+ A_Brute_<Clip> anims, M_Brute from its PBR maps) and the impact fx, idempotent (folders are deleted first). Content is git-ignored;
# this script + rig_brute.py + the source GLB (Customuse task, see docs/brute/ASSETS.md) are the source of truth.
#
#   plain python3 (orchestrator; YOUR editor/game of this project closed):
#       python3 unreal/WebHomage/Scripts/build_brute.py [--fbx ~/hulk-scratch/brute_skel/brute_skel.fbx]
#   runs ONE headless commandlet (-nullrhi) of this project through tools/gpu/gpu_slot.sh capture (shared coordinator ~/.cache/gpu-slot).
import os, sys, json, subprocess, time

HOME = os.path.expanduser('~')
HERE = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.path.join(HOME, 'hulk/unreal/WebHomage/Scripts')
PROJ = os.path.dirname(HERE)
WT = os.path.dirname(os.path.dirname(PROJ))
UPROJECT = os.path.join(PROJ, 'WebHomage.uproject')
UE = '/Users/Shared/Epic Games/UE_5.8/Engine/Binaries/Mac/UnrealEditor.app/Contents/MacOS/UnrealEditor'
GPU_SLOT = os.path.join(WT, 'tools', 'gpu', 'gpu_slot.sh')
DEST = '/Game/Brute/Parts'

try:
    import unreal  # noqa: F401
    IN_UE = hasattr(unreal, 'EditorAssetLibrary')
except ImportError:
    IN_UE = False


def build_material(src_dir, tools, dest=None):
    """M_Brute: base colour + normal + ORM (R occlusion, G roughness, B metallic) from the Customuse PBR maps."""
    MEL = unreal.MaterialEditingLibrary
    dest = dest or DEST
    tex = {}
    for kind, comp, srgb in (('BaseColor', unreal.TextureCompressionSettings.TC_DEFAULT, True),
                             ('Normal', unreal.TextureCompressionSettings.TC_NORMALMAP, False),
                             ('ORM', unreal.TextureCompressionSettings.TC_MASKS, False),
                             ('AO', unreal.TextureCompressionSettings.TC_GRAYSCALE, False),   # tools/brute/bake_ao.py (optional)
                             ('Veins', unreal.TextureCompressionSettings.TC_GRAYSCALE, False)):   # tools/brute/tex_bake.py (optional)
        f = os.path.join(src_dir, 'T_Brute_%s.png' % kind)
        if not os.path.isfile(f):
            unreal.log_warning('[brute] texture missing ' + f); continue
        t = unreal.AssetImportTask()
        t.set_editor_property('filename', f); t.set_editor_property('destination_path', dest)
        t.set_editor_property('automated', True); t.set_editor_property('replace_existing', True); t.set_editor_property('save', True)
        tools.import_asset_tasks([t])
        a = unreal.load_asset('%s/T_Brute_%s' % (dest, kind))
        if not a: continue
        a.set_editor_property('compression_settings', comp); a.set_editor_property('srgb', srgb)
        if kind == 'Normal': a.set_editor_property('flip_green_channel', os.environ.get('BRUTE_NORMAL_FLIP', '1') == '1')   # OpenGL (+Y) maps -> UE's DirectX convention
        unreal.EditorAssetLibrary.save_asset(a.get_path_name())
        tex[kind] = a
    if 'BaseColor' not in tex: return None
    if unreal.EditorAssetLibrary.does_asset_exist(dest + '/M_Brute'): unreal.EditorAssetLibrary.delete_asset(dest + '/M_Brute')
    m = tools.create_asset('M_Brute', dest, unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property('used_with_skeletal_mesh', True)   # without the usage flag -game silently falls back to the default grey
    def sample(kind, x, y, stype):
        n = MEL.create_material_expression(m, unreal.MaterialExpressionTextureSample, x, y)
        n.set_editor_property('texture', tex[kind]); n.set_editor_property('sampler_type', stype)
        return n
    def const3(x, y, v):
        n = MEL.create_material_expression(m, unreal.MaterialExpressionConstant3Vector, x, y); n.set_editor_property('constant', unreal.LinearColor(v[0], v[1], v[2], 1)); return n
    def const1(x, y, v):
        n = MEL.create_material_expression(m, unreal.MaterialExpressionConstant, x, y); n.set_editor_property('r', v); return n
    def op(cls, x, y, a, b=None, ai='', bi=''):
        n = MEL.create_material_expression(m, cls, x, y)
        MEL.connect_material_expressions(a, ai, n, 'A' if b is not None else '')
        if b is not None: MEL.connect_material_expressions(b, bi, n, 'B')
        return n
    # 2026-10-16 look pass (owner: "the visual look of the hulk ... highest quality"): the raw Customuse albedo reads lime / plastic.
    #   skin mask = how much greener than red / blue a texel is (shorts purple, hair black, nails / teeth stay as authored)
    #   skin: a little more contrast, pulled from yellow-lime toward a deep emerald; subsurface scattering (dark green-red) so it
    #   reads as flesh, not plastic; roughness lifted slightly; normal detail strengthened
    bc = sample('BaseColor', -1400, -300, unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
    if os.environ.get('BRUTE_LOOK_PLAIN') == '1':   # A/B reference: the raw maps, default lit
        MEL.connect_material_property(bc, 'RGB', unreal.MaterialProperty.MP_BASE_COLOR)
        if 'Normal' in tex: MEL.connect_material_property(sample('Normal', -1000, 200, unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL), 'RGB', unreal.MaterialProperty.MP_NORMAL)
        if 'ORM' in tex:
            orm = sample('ORM', -1000, 500, unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
            MEL.connect_material_property(orm, 'G', unreal.MaterialProperty.MP_ROUGHNESS); MEL.connect_material_property(orm, 'B', unreal.MaterialProperty.MP_METALLIC)
        MEL.recompile_material(m); unreal.EditorAssetLibrary.save_asset(m.get_path_name()); return m
    # (MSM_SUBSURFACE was tried 2026-10-16: it washed the muscle definition out into flat bright lime -- default lit keeps the form)
    mr = op(unreal.MaterialExpressionComponentMask, -1150, -500, bc, None, 'R'); mr.set_editor_property('r', True); mr.set_editor_property('g', False); mr.set_editor_property('b', False); mr.set_editor_property('a', False)
    mg = op(unreal.MaterialExpressionComponentMask, -1150, -420, bc, None, 'RGB'); mg.set_editor_property('r', False); mg.set_editor_property('g', True); mg.set_editor_property('b', False); mg.set_editor_property('a', False)
    mb = op(unreal.MaterialExpressionComponentMask, -1150, -340, bc, None, 'RGB'); mb.set_editor_property('r', False); mb.set_editor_property('g', False); mb.set_editor_property('b', True); mb.set_editor_property('a', False)
    # skin = green over blue AND not redder than green (the olive skin is ~(64,65,33)/255; shorts purple, hair black, nails / lips orange)
    gb = op(unreal.MaterialExpressionSubtract, -1000, -440, mg, mb)
    rg_ = op(unreal.MaterialExpressionSubtract, -1000, -360, mr, mg)
    a1 = op(unreal.MaterialExpressionMultiply, -880, -440, gb, const1(-1000, -520, 6.0))
    a2 = op(unreal.MaterialExpressionMultiply, -880, -360, rg_, const1(-1000, -280, 8.0))
    mk = op(unreal.MaterialExpressionSubtract, -760, -420, a1, a2)
    mask = op(unreal.MaterialExpressionSaturate, -640, -420, mk)
    # skin: deepened toward a darker emerald (critic 2026-10-17: the raw olive reads as flat lime rubber)
    skin = op(unreal.MaterialExpressionMultiply, -860, -220, bc, const3(-1000, -120, (0.80, 0.92, 0.76)), 'RGB')
    lerp = MEL.create_material_expression(m, unreal.MaterialExpressionLinearInterpolate, -520, -260)
    MEL.connect_material_expressions(bc, 'RGB', lerp, 'A'); MEL.connect_material_expressions(skin, '', lerp, 'B'); MEL.connect_material_expressions(mask, '', lerp, 'Alpha')
    if 'Veins' in tex:
        # raised veins (tools/brute/tex_bake.py) a touch darker and greener than the skin around them
        vn = sample('Veins', -1000, -40, unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE)
        vk = op(unreal.MaterialExpressionMultiply, -700, -40, vn, const1(-860, 20, 0.55), 'R')
        vc = MEL.create_material_expression(m, unreal.MaterialExpressionLinearInterpolate, -420, -60)
        MEL.connect_material_expressions(lerp, '', vc, 'A'); MEL.connect_material_expressions(op(unreal.MaterialExpressionMultiply, -560, -100, lerp, const3(-700, -120, (0.72, 0.86, 0.70))), '', vc, 'B')
        MEL.connect_material_expressions(vk, '', vc, 'Alpha')
        lerp = vc
    MEL.connect_material_property(lerp, '', unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(const1(-300, 80, 0.42), '', unreal.MaterialProperty.MP_SPECULAR)
    if 'Normal' in tex:
        nm = sample('Normal', -1000, 200, unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
        nb = op(unreal.MaterialExpressionMultiply, -700, 200, nm, const3(-860, 300, (1.4, 1.4, 1.0)), 'RGB')
        MEL.connect_material_property(nb, '', unreal.MaterialProperty.MP_NORMAL)
    if 'AO' in tex:
        # baked occlusion: real depth in the muscle grooves / armpits / fingers -- as occlusion AND a soft cavity darkening of the albedo
        ao = sample('AO', -1000, 820, unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE)
        MEL.connect_material_property(ao, 'R', unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
        cav = MEL.create_material_expression(m, unreal.MaterialExpressionLinearInterpolate, -380, -160)
        MEL.connect_material_expressions(const1(-520, -120, 1.0), '', cav, 'A'); MEL.connect_material_expressions(ao, 'R', cav, 'B'); MEL.connect_material_expressions(const1(-520, -80, 0.55), '', cav, 'Alpha')
        bcf = op(unreal.MaterialExpressionMultiply, -260, -240, lerp, cav)
        MEL.connect_material_property(bcf, '', unreal.MaterialProperty.MP_BASE_COLOR)
    if 'ORM' in tex:
        orm = sample('ORM', -1000, 500, unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
        if 'AO' not in tex: MEL.connect_material_property(orm, 'R', unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
        rg = op(unreal.MaterialExpressionMultiply, -700, 520, orm, const1(-860, 600, 0.9), 'G')
        ra = op(unreal.MaterialExpressionAdd, -560, 520, rg, const1(-700, 620, 0.08))
        # critic 2026-10-17 "flat, plasticky": break the skin's sheen up with fine noise in UV space (pores / sweat variation) and
        # make the purple shorts a matte cloth (cloth mask = bluer than green)
        tc = MEL.create_material_expression(m, unreal.MaterialExpressionTextureCoordinate, -1300, 980)
        tcs = op(unreal.MaterialExpressionMultiply, -1150, 980, tc, const1(-1300, 1060, 900.0))
        tc3 = MEL.create_material_expression(m, unreal.MaterialExpressionAppendVector, -1000, 980)
        MEL.connect_material_expressions(tcs, '', tc3, 'A'); MEL.connect_material_expressions(const1(-1150, 1060, 0.0), '', tc3, 'B')
        nz = MEL.create_material_expression(m, unreal.MaterialExpressionNoise, -860, 980)
        try:
            nz.set_editor_property('scale', 1.0); nz.set_editor_property('levels', 3); nz.set_editor_property('output_min', -1.0); nz.set_editor_property('output_max', 1.0)
        except Exception as ex: unreal.log_warning('[brute] noise props: %s' % ex)
        MEL.connect_material_expressions(tc3, '', nz, 'Position')
        nzs = op(unreal.MaterialExpressionMultiply, -700, 980, nz, mask)
        nzk = op(unreal.MaterialExpressionMultiply, -560, 980, nzs, const1(-700, 1060, 0.12))
        rs = op(unreal.MaterialExpressionAdd, -420, 600, ra, nzk)
        bg = op(unreal.MaterialExpressionSubtract, -1000, 1180, mb, mg)
        cm = op(unreal.MaterialExpressionSaturate, -700, 1180, op(unreal.MaterialExpressionMultiply, -860, 1180, bg, const1(-1000, 1260, 6.0)))
        rc = MEL.create_material_expression(m, unreal.MaterialExpressionLinearInterpolate, -280, 640)
        MEL.connect_material_expressions(rs, '', rc, 'A'); MEL.connect_material_expressions(const1(-420, 720, 0.88), '', rc, 'B'); MEL.connect_material_expressions(cm, '', rc, 'Alpha')
        MEL.connect_material_property(rc, '', unreal.MaterialProperty.MP_ROUGHNESS)
        MEL.connect_material_property(orm, 'B', unreal.MaterialProperty.MP_METALLIC)
    MEL.recompile_material(m)
    unreal.EditorAssetLibrary.save_asset(m.get_path_name())
    unreal.log('[brute] material %s (%s)' % (m.get_path_name(), ', '.join(sorted(tex))))
    return m


FX_DEST = '/Game/Brute/Fx'


def fx_material(tools, name, dust):
    """translucent unlit, two-sided: emissive = Color * Glow; opacity = Opacity x (shock: fades up the band, V) / (dust: soft edges, 1 - fresnel)."""
    MEL = unreal.MaterialEditingLibrary
    m = tools.create_asset(name, FX_DEST, unreal.Material, unreal.MaterialFactoryNew())
    # LIT translucency: the city runs physical sun / exposure, so unlit emissive dust at ~1 reads near-black in daylight; the sun
    # lights these like any surface and Glow only adds a little emissive (night)
    m.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
    m.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
    m.set_editor_property('two_sided', True)
    try: m.set_editor_property('translucency_lighting_mode', unreal.TranslucencyLightingMode.TLM_SURFACE)
    except Exception as ex: unreal.log_warning('[brute] translucency lighting mode: %s' % ex)
    col = MEL.create_material_expression(m, unreal.MaterialExpressionVectorParameter, -700, -200)
    col.set_editor_property('parameter_name', 'Color'); col.set_editor_property('default_value', unreal.LinearColor(1, 1, 1, 1))
    MEL.connect_material_property(col, '', unreal.MaterialProperty.MP_BASE_COLOR)
    rough = MEL.create_material_expression(m, unreal.MaterialExpressionConstant, -700, 40)
    rough.set_editor_property('r', 1.0)
    MEL.connect_material_property(rough, '', unreal.MaterialProperty.MP_ROUGHNESS)
    glow = MEL.create_material_expression(m, unreal.MaterialExpressionScalarParameter, -700, -50)
    glow.set_editor_property('parameter_name', 'Glow'); glow.set_editor_property('default_value', 1.0)
    em = MEL.create_material_expression(m, unreal.MaterialExpressionMultiply, -400, -150)
    MEL.connect_material_expressions(col, '', em, 'A'); MEL.connect_material_expressions(glow, '', em, 'B')
    k = MEL.create_material_expression(m, unreal.MaterialExpressionConstant, -400, -40)
    k.set_editor_property('r', 0.04)   # a faint self-glow only (night); daylight look comes from the lighting
    em2 = MEL.create_material_expression(m, unreal.MaterialExpressionMultiply, -250, -120)
    MEL.connect_material_expressions(em, '', em2, 'A'); MEL.connect_material_expressions(k, '', em2, 'B')
    MEL.connect_material_property(em2, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    op = MEL.create_material_expression(m, unreal.MaterialExpressionScalarParameter, -700, 150)
    op.set_editor_property('parameter_name', 'Opacity'); op.set_editor_property('default_value', 0.6)
    if dust:
        fr = MEL.create_material_expression(m, unreal.MaterialExpressionFresnel, -700, 300)
        fr.set_editor_property('exponent', 1.6)
        one = MEL.create_material_expression(m, unreal.MaterialExpressionOneMinus, -500, 300)
        MEL.connect_material_expressions(fr, '', one, '')
        shape = one
    else:
        tc = MEL.create_material_expression(m, unreal.MaterialExpressionTextureCoordinate, -900, 300)
        mask = MEL.create_material_expression(m, unreal.MaterialExpressionComponentMask, -700, 300)
        mask.set_editor_property('r', False); mask.set_editor_property('g', True); mask.set_editor_property('b', False); mask.set_editor_property('a', False)
        MEL.connect_material_expressions(tc, '', mask, '')
        one = MEL.create_material_expression(m, unreal.MaterialExpressionOneMinus, -500, 300)
        MEL.connect_material_expressions(mask, '', one, '')
        shape = MEL.create_material_expression(m, unreal.MaterialExpressionMultiply, -350, 300)
        MEL.connect_material_expressions(one, '', shape, 'A'); MEL.connect_material_expressions(one, '', shape, 'B')
    mul = MEL.create_material_expression(m, unreal.MaterialExpressionMultiply, -200, 200)
    MEL.connect_material_expressions(op, '', mul, 'A'); MEL.connect_material_expressions(shape, '', mul, 'B')
    df = MEL.create_material_expression(m, unreal.MaterialExpressionDepthFade, -60, 200)
    df.set_editor_property('fade_distance_default', 60.0)
    MEL.connect_material_expressions(mul, '', df, 'Opacity')
    MEL.connect_material_property(df, '', unreal.MaterialProperty.MP_OPACITY)
    MEL.recompile_material(m)
    unreal.EditorAssetLibrary.save_asset(m.get_path_name())
    unreal.log('[brute] fx material ' + m.get_path_name())
    return m


def crack_decal(tools, src_dir):
    """M_BruteCrackDecal: deferred decal from tools/brute/make_crack_decal.py (crushed centre + branching cracks, alpha + normal)"""
    MEL = unreal.MaterialEditingLibrary
    tex = {}
    for kind, comp, srgb in (('D', unreal.TextureCompressionSettings.TC_DEFAULT, True), ('N', unreal.TextureCompressionSettings.TC_NORMALMAP, False)):
        f = os.path.join(src_dir, 'T_BruteCrack_%s.png' % kind)
        if not os.path.isfile(f): unreal.log_warning('[brute] crack decal texture missing ' + f); return
        t = unreal.AssetImportTask()
        for k, v in (('filename', f), ('destination_path', FX_DEST), ('automated', True), ('replace_existing', True), ('save', True)): t.set_editor_property(k, v)
        tools.import_asset_tasks([t])
        a = unreal.load_asset('%s/T_BruteCrack_%s' % (FX_DEST, kind))
        a.set_editor_property('compression_settings', comp); a.set_editor_property('srgb', srgb)
        if kind == 'N': a.set_editor_property('flip_green_channel', False)
        a.set_editor_property('never_stream', True)   # a streaming placeholder showed the whole decal box as a dark square for a frame
        unreal.EditorAssetLibrary.save_asset(a.get_path_name()); tex[kind] = a
    m = tools.create_asset('M_BruteCrackDecal', FX_DEST, unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property('material_domain', unreal.MaterialDomain.MD_DEFERRED_DECAL)
    m.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
    d = MEL.create_material_expression(m, unreal.MaterialExpressionTextureSample, -600, -100); d.set_editor_property('texture', tex['D'])
    n = MEL.create_material_expression(m, unreal.MaterialExpressionTextureSample, -600, 200); n.set_editor_property('texture', tex['N'])
    n.set_editor_property('sampler_type', unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    MEL.connect_material_property(d, 'RGB', unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(d, 'A', unreal.MaterialProperty.MP_OPACITY)
    MEL.connect_material_property(n, 'RGB', unreal.MaterialProperty.MP_NORMAL)
    r = MEL.create_material_expression(m, unreal.MaterialExpressionConstant, -300, 120); r.set_editor_property('r', 0.92)
    MEL.connect_material_property(r, '', unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.recompile_material(m)
    unreal.EditorAssetLibrary.save_asset(m.get_path_name())
    unreal.log('[brute] crack decal ' + m.get_path_name())


def build_fx(tools):
    fbx = os.environ.get('BRUTE_FX_FBX', '')
    if not fbx or not os.path.isfile(fbx):
        unreal.log_warning('[brute] no fx fbx (%s): impacts fall back to engine shapes' % fbx); return
    EAL = unreal.EditorAssetLibrary
    if EAL.does_directory_exist(FX_DEST): EAL.delete_directory(FX_DEST)
    ui = unreal.FbxImportUI()
    for k, v in (('import_mesh', True), ('import_as_skeletal', False), ('import_materials', False), ('import_textures', False), ('import_animations', False)):
        ui.set_editor_property(k, v)
    ui.set_editor_property('mesh_type_to_import', unreal.FBXImportType.FBXIT_STATIC_MESH)
    sm = ui.get_editor_property('static_mesh_import_data')
    sm.set_editor_property('combine_meshes', False); sm.set_editor_property('auto_generate_collision', False)
    sm.set_editor_property('generate_lightmap_u_vs', False); sm.set_editor_property('convert_scene', True)
    t = unreal.AssetImportTask()
    for k, v in (('filename', fbx), ('destination_path', FX_DEST), ('automated', True), ('replace_existing', True), ('save', True), ('options', ui)):
        t.set_editor_property(k, v)
    tools.import_asset_tasks([t])
    fx_material(tools, 'M_BruteShock', False)
    fx_material(tools, 'M_BruteDust', True)
    crack_decal(tools, os.path.dirname(fbx))
    for a in EAL.list_assets(FX_DEST, recursive=True):
        unreal.log('[brute] fx asset ' + a)


SKEL = '/Game/Brute/Body'   # v2 (a fresh folder: re-importing over the v1 SK_Brute in /Game/Brute/Skel cannot merge the new bone tree)
OLD_SKEL = '/Game/Brute/Skel'


CLIPS = ('Idle', 'Walk', 'Run', 'StopLunge', 'Jump', 'WallAttach', 'WallClimb',
         'PunchL', 'PunchR', 'Slap', 'Clap', 'Smash', 'Lift', 'Throw', 'Uppercut', 'Fall', 'Land')


def rename_anims(EAL):
    """the FBX takes import as <mesh>_Anim_<armature>_<Clip>: rename them to A_Brute_<Clip> (the names BruteCharacter loads)"""
    found = []
    for a in EAL.list_assets(SKEL, recursive=True):
        o = unreal.load_asset(a)
        if not isinstance(o, unreal.AnimSequence): continue
        nm = a.split('.')[0].split('/')[-1]
        clip = next((c for c in sorted(CLIPS, key=len, reverse=True) if nm.endswith(c)), None)
        if not clip: unreal.log_warning('[brute] unmatched anim ' + a); continue
        dst = '%s/A_Brute_%s' % (SKEL, clip)
        if a.split('.')[0] != dst: EAL.rename_asset(a.split('.')[0], dst)
        s = unreal.load_asset(dst)
        unreal.log('[brute] anim %s %.2f s' % (dst, s.get_play_length()))
        found.append(clip)
    missing = [c for c in CLIPS if c not in found]
    if missing: unreal.log_error('SM2_BUILD_FAILED: clips missing %s' % missing); raise RuntimeError('clips missing')


def build_in_ue():
    """the v2 body (Customuse CR 2.1 'Emerald Behemoth', Customuse auto-rig, clips assembled by tools/brute/assemble_motion.py):
    one SkeletalMesh /Game/Brute/Body/SK_Brute + its AnimSequences A_Brute_<Clip> + M_Brute; the old rigid parts are removed"""
    fbx = os.environ['BRUTE_FBX']
    EAL = unreal.EditorAssetLibrary
    if os.environ.get('BRUTE_PHASE') == 'material':
        # look-dev: rebuild only M_Brute from the already imported textures (the mesh / skeletal mesh keep referencing it by path)
        tools = unreal.AssetToolsHelpers.get_asset_tools()
        mat = build_material(os.path.dirname(fbx), tools, SKEL)
        mesh = unreal.load_asset(SKEL + '/SK_Brute')
        if mat and mesh:
            mats = mesh.get_editor_property('materials')
            for sm in mats: sm.set_editor_property('material_interface', mat)
            mesh.set_editor_property('materials', mats); EAL.save_asset(mesh.get_path_name())
        unreal.log('SM2_BUILD_OK: build_brute.py'); return
    for d in (DEST, OLD_SKEL, SKEL):
        if EAL.does_directory_exist(d): EAL.delete_directory(d)
    if os.environ.get('BRUTE_PHASE') == 'clean':
        # a re-import in the same process as the delete silently drops the animations (the old skeleton is still in memory):
        # the orchestrator runs the delete and the import as two commandlets
        unreal.log('SM2_BUILD_OK: build_brute.py'); return
    ui = unreal.FbxImportUI()
    for k, v in (('import_mesh', True), ('import_as_skeletal', True), ('import_materials', False), ('import_textures', False),
                 ('import_animations', True), ('create_physics_asset', False)):
        ui.set_editor_property(k, v)
    ui.set_editor_property('mesh_type_to_import', unreal.FBXImportType.FBXIT_SKELETAL_MESH)
    an = ui.get_editor_property('anim_sequence_import_data')
    an.set_editor_property('convert_scene', True)
    an.set_editor_property('import_bone_tracks', True)
    an.set_editor_property('animation_length', unreal.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
    try: an.set_editor_property('use_default_sample_rate', False); an.set_editor_property('custom_sample_rate', 30)
    except Exception as ex: unreal.log_warning('[brute] sample rate: %s' % ex)
    sk = ui.get_editor_property('skeletal_mesh_import_data')
    sk.set_editor_property('import_uniform_scale', 1.0)
    sk.set_editor_property('convert_scene', True)
    sk.set_editor_property('force_front_x_axis', False)
    sk.set_editor_property('normal_import_method', unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
    sk.set_editor_property('import_morph_targets', True)   # corrective shapes (tools/brute/mesh_corrective.py)
    t = unreal.AssetImportTask()
    for k, v in (('filename', fbx), ('destination_path', SKEL), ('destination_name', 'SK_Brute'), ('automated', True), ('replace_existing', True),
                 ('save', True), ('options', ui)):
        t.set_editor_property(k, v)
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    tools.import_asset_tasks([t])
    for a in EAL.list_assets(SKEL, recursive=True): unreal.log('[brute] asset ' + a)
    m = unreal.load_asset(SKEL + '/SK_Brute')
    if not isinstance(m, unreal.SkeletalMesh):
        cands = [a for a in EAL.list_assets(SKEL, recursive=True) if isinstance(unreal.load_asset(a), unreal.SkeletalMesh)]
        if cands:
            EAL.rename_asset(cands[0].split('.')[0], SKEL + '/SK_Brute'); m = unreal.load_asset(SKEL + '/SK_Brute')
    if not isinstance(m, unreal.SkeletalMesh):
        unreal.log_error('SM2_BUILD_FAILED: no skeletal mesh imported'); raise RuntimeError('SK_Brute missing')
    mat = build_material(os.path.dirname(fbx), tools, SKEL)   # M_Brute + textures live beside the mesh
    for kind in ('BaseColor', 'Normal', 'ORM'):   # the hero is always on screen: never stream his maps (no grey first second)
        tx = unreal.load_asset('%s/T_Brute_%s' % (SKEL, kind))
        if tx: tx.set_editor_property('never_stream', True); EAL.save_asset(tx.get_path_name())
    if mat:
        mats = m.get_editor_property('materials')
        for sm in mats: sm.set_editor_property('material_interface', mat)
        m.set_editor_property('materials', mats)
    skel = m.get_editor_property('skeleton')
    try: names = [str(n) for n in unreal.AnimPoseExtensions.get_bone_names(skel.get_reference_pose())]
    except Exception as ex: names = ['?(%s)' % ex]
    b = m.get_bounds()
    unreal.log('[brute] SK_Brute bounds origin (%.1f %.1f %.1f) extent (%.1f %.1f %.1f), bones %s' % (b.origin.x, b.origin.y, b.origin.z, b.box_extent.x, b.box_extent.y, b.box_extent.z, names))
    EAL.save_asset(m.get_path_name())
    if not any(isinstance(unreal.load_asset(x), unreal.AnimSequence) for x in EAL.list_assets(SKEL, recursive=True)):
        # Interchange sometimes imports the mesh but drops the takes (seen on re-imports): import them explicitly onto the skeleton
        ua = unreal.FbxImportUI()
        for k, v in (('import_mesh', False), ('import_as_skeletal', True), ('import_materials', False), ('import_textures', False), ('import_animations', True)):
            ua.set_editor_property(k, v)
        ua.set_editor_property('mesh_type_to_import', unreal.FBXImportType.FBXIT_ANIMATION)
        ua.set_editor_property('skeleton', m.get_editor_property('skeleton'))
        aa = ua.get_editor_property('anim_sequence_import_data')
        aa.set_editor_property('convert_scene', True); aa.set_editor_property('import_bone_tracks', True)
        aa.set_editor_property('animation_length', unreal.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
        ta = unreal.AssetImportTask()
        for k, v in (('filename', fbx), ('destination_path', SKEL), ('automated', True), ('replace_existing', True), ('save', True), ('options', ua)):
            ta.set_editor_property(k, v)
        tools.import_asset_tasks([ta])
        unreal.log('[brute] explicit animation import: %s' % [x for x in EAL.list_assets(SKEL, recursive=True) if isinstance(unreal.load_asset(x), unreal.AnimSequence)])
    rename_anims(EAL)
    EAL.save_directory(SKEL)
    build_fx(tools)
    unreal.log('SM2_BUILD_OK: build_brute.py')


def orchestrate():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--fbx', default=os.path.join(HOME, 'hulk-scratch/brute_v5/brute_anim.fbx'))
    ap.add_argument('--tex-dir', default=os.path.join(HOME, 'hulk-scratch/brute_v2/rig/textures'), help='Customuse auto-rig export textures (SM_Character_Brute_{D,N,ORM}.png)')
    ap.add_argument('--ao', default=os.path.join(HOME, 'hulk-scratch/brute_look/T_Brute_AO.png'), help='baked AO (tools/brute/bake_ao.py)')
    ap.add_argument('--normal', default=os.path.join(HOME, 'hulk-scratch/brute_tex/T_Brute_Normal.png'), help='normal map with baked veins / cloth folds (tools/brute/tex_bake.py)')
    ap.add_argument('--veins', default=os.path.join(HOME, 'hulk-scratch/brute_tex/T_Brute_Veins.png'), help='vein mask (tools/brute/tex_bake.py)')
    ap.add_argument('--material-only', action='store_true', help='look-dev: rebuild only M_Brute')
    ap.add_argument('--fx-fbx', default=os.path.join(HOME, 'hulk-scratch/brute_fx/brute_fx.fbx'))
    a = ap.parse_args()
    # stage the FBX + its maps under the names build_material expects (T_Brute_<Kind>.png beside the FBX)
    import shutil
    stage = os.path.join(HOME, 'hulk-scratch', 'brute_ue')
    os.makedirs(stage, exist_ok=True)
    shutil.copy2(a.fbx, os.path.join(stage, 'brute_anim.fbx'))
    for kind, suf in (('BaseColor', 'D'), ('Normal', 'N'), ('ORM', 'ORM')):
        src = os.path.join(a.tex_dir, 'SM_Character_Brute_%s.png' % suf)
        if os.path.isfile(src): shutil.copy2(src, os.path.join(stage, 'T_Brute_%s.png' % kind))
    for opt, kind in ((a.normal, 'Normal'), (a.veins, 'Veins')):   # detail-baked maps override the raw Customuse ones
        if opt and os.path.isfile(opt): shutil.copy2(opt, os.path.join(stage, 'T_Brute_%s.png' % kind))
        elif kind == 'Veins' and os.path.exists(os.path.join(stage, 'T_Brute_Veins.png')): os.remove(os.path.join(stage, 'T_Brute_Veins.png'))
    if a.ao and os.path.isfile(a.ao): shutil.copy2(a.ao, os.path.join(stage, 'T_Brute_AO.png'))
    elif os.path.exists(os.path.join(stage, 'T_Brute_AO.png')): os.remove(os.path.join(stage, 'T_Brute_AO.png'))
    a.fbx = os.path.join(stage, 'brute_anim.fbx')
    if subprocess.run(['pgrep', '-f', UPROJECT], capture_output=True).returncode == 0:
        raise SystemExit('an Unreal process of this project is running; stop it first (SIGTERM, wait up to 60 s)')
    root = os.path.join(HOME, '.cache', 'gpu-slot')
    if os.path.exists(os.path.join(root, 'PAUSED')):
        raise SystemExit('shared GPU PAUSED; never cleared by this build')
    logs = os.path.join(HOME, 'hulk-logs'); os.makedirs(logs, exist_ok=True)
    lg = os.path.join(logs, 'build_brute_ue.log')
    if os.path.exists(lg): os.remove(lg)
    cmd = [GPU_SLOT, 'capture', '--label', 'hulk-build-brute', '--timeout', '3600', '--', UE, UPROJECT, '-run=pythonscript',
           '-script=' + os.path.abspath(__file__), '-unattended', '-nullrhi', '-nosplash', '-RenderOffScreen', '-NoSound', '-NoCrashReports', '-abslog=' + lg]
    env = {**os.environ, 'BRUTE_FBX': os.path.abspath(a.fbx), 'BRUTE_FX_FBX': os.path.abspath(a.fx_fbx), 'GPU_SLOT_DIR': root, 'GPU_SLOT_CAPTURE_MAX_HOLD': '1800'}
    t0 = time.time()
    if a.material_only:
        rc = subprocess.run(cmd, env={**env, 'BRUTE_PHASE': 'material'}).returncode
    else:
        rc = subprocess.run(cmd, env={**env, 'BRUTE_PHASE': 'clean'}).returncode
        if os.path.exists(lg): os.rename(lg, lg + '.clean')
        rc = subprocess.run(cmd, env={**env, 'BRUTE_PHASE': 'import'}).returncode
    txt = open(lg, errors='replace').read() if os.path.exists(lg) else ''
    for l in txt.splitlines():
        if '[brute]' in l or 'SM2_BUILD' in l or 'Error' in l: print(l.split('LogPython: ')[-1])
    print('build_brute: rc %d in %.0f s' % (rc, time.time() - t0))
    # the commandlet exits 1 whenever the engine's own summary lists errors (e.g. the project's GameFeatureData warning), so the
    # success sentinel + no python error decide
    if 'SM2_BUILD_OK: build_brute.py' not in txt or 'LogPython: Error' in txt or 'Traceback' in txt:
        raise SystemExit('build_brute failed (log %s)' % lg)


if IN_UE:
    build_in_ue()
elif __name__ == '__main__':
    orchestrate()
