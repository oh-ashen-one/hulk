# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
# Brute body content: imports the SKINNED Customuse model (tools/brute/rig_brute.py -> brute_skel.fbx) as the skeletal mesh
# /Game/Brute/Skel/SK_Brute (+ M_Brute from its PBR maps) and the impact fx, idempotent (folders are deleted first). Content is git-ignored;
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
                             ('ORM', unreal.TextureCompressionSettings.TC_MASKS, False)):
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
        if kind == 'Normal': a.set_editor_property('flip_green_channel', False)   # Blender exports OpenGL normals (NormalGL)
        unreal.EditorAssetLibrary.save_asset(a.get_path_name())
        tex[kind] = a
    if 'BaseColor' not in tex: return None
    m = tools.create_asset('M_Brute', dest, unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property('used_with_skeletal_mesh', True)   # without the usage flag -game silently falls back to the default grey
    def sample(kind, x, y, stype):
        n = MEL.create_material_expression(m, unreal.MaterialExpressionTextureSample, x, y)
        n.set_editor_property('texture', tex[kind]); n.set_editor_property('sampler_type', stype)
        return n
    bc = sample('BaseColor', -500, -200, unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
    MEL.connect_material_property(bc, 'RGB', unreal.MaterialProperty.MP_BASE_COLOR)
    if 'Normal' in tex:
        nm = sample('Normal', -500, 150, unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
        MEL.connect_material_property(nm, 'RGB', unreal.MaterialProperty.MP_NORMAL)
    if 'ORM' in tex:
        orm = sample('ORM', -500, 450, unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
        MEL.connect_material_property(orm, 'R', unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
        MEL.connect_material_property(orm, 'G', unreal.MaterialProperty.MP_ROUGHNESS)
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
    for a in EAL.list_assets(FX_DEST, recursive=True):
        unreal.log('[brute] fx asset ' + a)


SKEL = '/Game/Brute/Skel'


def build_in_ue():
    """the skinned body (tools/brute/rig_brute.py): one SkeletalMesh /Game/Brute/Skel/SK_Brute + M_Brute; the old rigid parts are removed"""
    fbx = os.environ['BRUTE_FBX']
    EAL = unreal.EditorAssetLibrary
    for d in (DEST, SKEL):
        if EAL.does_directory_exist(d): EAL.delete_directory(d)
    ui = unreal.FbxImportUI()
    for k, v in (('import_mesh', True), ('import_as_skeletal', True), ('import_materials', False), ('import_textures', False),
                 ('import_animations', False), ('create_physics_asset', False)):
        ui.set_editor_property(k, v)
    ui.set_editor_property('mesh_type_to_import', unreal.FBXImportType.FBXIT_SKELETAL_MESH)
    sk = ui.get_editor_property('skeletal_mesh_import_data')
    sk.set_editor_property('import_uniform_scale', 1.0)
    sk.set_editor_property('convert_scene', True)
    sk.set_editor_property('force_front_x_axis', False)
    sk.set_editor_property('normal_import_method', unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
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
    build_fx(tools)
    unreal.log('SM2_BUILD_OK: build_brute.py')


def orchestrate():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--fbx', default=os.path.join(HOME, 'hulk-scratch/brute_skel/brute_skel.fbx'))
    ap.add_argument('--fx-fbx', default=os.path.join(HOME, 'hulk-scratch/brute_fx/brute_fx.fbx'))
    a = ap.parse_args()
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
    rc = subprocess.run(cmd, env=env).returncode
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
