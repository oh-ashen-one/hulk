# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
# Brute body content: imports the segmented Customuse model (tools/brute/segment_brute.py -> brute_parts.fbx) as 11 static meshes
# /Game/Brute/Parts/SM_Brute_<Part> (+ its material / textures), idempotent (the folder is deleted first). Content is git-ignored;
# this script + segment_brute.py + the source GLB (Customuse task, see docs/brute/ASSETS.md) are the source of truth.
#
#   plain python3 (orchestrator; YOUR editor/game of this project closed):
#       python3 unreal/WebHomage/Scripts/build_brute.py [--fbx ~/hulk-scratch/brute_parts/brute_parts.fbx]
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


def build_material(src_dir, tools):
    """M_Brute: base colour + normal + ORM (R occlusion, G roughness, B metallic) from the Customuse PBR maps."""
    MEL = unreal.MaterialEditingLibrary
    tex = {}
    for kind, comp, srgb in (('BaseColor', unreal.TextureCompressionSettings.TC_DEFAULT, True),
                             ('Normal', unreal.TextureCompressionSettings.TC_NORMALMAP, False),
                             ('ORM', unreal.TextureCompressionSettings.TC_MASKS, False)):
        f = os.path.join(src_dir, 'T_Brute_%s.png' % kind)
        if not os.path.isfile(f):
            unreal.log_warning('[brute] texture missing ' + f); continue
        t = unreal.AssetImportTask()
        t.set_editor_property('filename', f); t.set_editor_property('destination_path', DEST)
        t.set_editor_property('automated', True); t.set_editor_property('replace_existing', True); t.set_editor_property('save', True)
        tools.import_asset_tasks([t])
        a = unreal.load_asset('%s/T_Brute_%s' % (DEST, kind))
        if not a: continue
        a.set_editor_property('compression_settings', comp); a.set_editor_property('srgb', srgb)
        if kind == 'Normal': a.set_editor_property('flip_green_channel', False)   # Blender exports OpenGL normals (NormalGL)
        unreal.EditorAssetLibrary.save_asset(a.get_path_name())
        tex[kind] = a
    if 'BaseColor' not in tex: return None
    m = tools.create_asset('M_Brute', DEST, unreal.Material, unreal.MaterialFactoryNew())
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


def build_in_ue():
    fbx = os.environ['BRUTE_FBX']
    EAL = unreal.EditorAssetLibrary
    if EAL.does_directory_exist(DEST):
        EAL.delete_directory(DEST)
    ui = unreal.FbxImportUI()
    ui.set_editor_property('import_mesh', True)
    ui.set_editor_property('import_as_skeletal', False)
    ui.set_editor_property('import_materials', False)
    ui.set_editor_property('import_textures', False)
    ui.set_editor_property('import_animations', False)
    ui.set_editor_property('mesh_type_to_import', unreal.FBXImportType.FBXIT_STATIC_MESH)
    sm = ui.get_editor_property('static_mesh_import_data')
    sm.set_editor_property('combine_meshes', False)
    sm.set_editor_property('auto_generate_collision', False)
    sm.set_editor_property('generate_lightmap_u_vs', False)
    sm.set_editor_property('import_uniform_scale', 1.0)
    sm.set_editor_property('convert_scene', True)
    sm.set_editor_property('force_front_x_axis', False)
    sm.set_editor_property('normal_import_method', unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
    t = unreal.AssetImportTask()
    t.set_editor_property('filename', fbx)
    t.set_editor_property('destination_path', DEST)
    t.set_editor_property('automated', True)
    t.set_editor_property('replace_existing', True)
    t.set_editor_property('save', True)
    t.set_editor_property('options', ui)
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    tools.import_asset_tasks([t])
    mat = build_material(os.path.dirname(fbx), tools)
    rig = json.load(open(os.path.join(PROJ, 'Config', 'BruteRig.json')))
    found = 0
    for name in rig['parts']:
        path = '%s/%s' % (DEST, name)
        m = unreal.load_asset(path)
        if not m:
            # the FBX importer may prefix the file name
            cands = [a for a in EAL.list_assets(DEST, recursive=True) if a.split('.')[0].endswith(name)]
            m = unreal.load_asset(cands[0]) if cands else None
            if m and cands[0].split('.')[0] != path:
                EAL.rename_asset(cands[0].split('.')[0], path); m = unreal.load_asset(path)
        if not m:
            unreal.log_error('[brute] missing mesh ' + name); continue
        if mat:
            for i in range(max(1, len(m.static_materials))): m.set_material(i, mat)
        b = m.get_bounding_box()
        unreal.log('[brute] %s bounds min (%.1f %.1f %.1f) max (%.1f %.1f %.1f)' % (name, b.min.x, b.min.y, b.min.z, b.max.x, b.max.y, b.max.z))
        EAL.save_asset(path)
        found += 1
    for a in EAL.list_assets(DEST, recursive=True):
        unreal.log('[brute] asset ' + a)
    if found != len(rig['parts']):
        unreal.log_error('SM2_BUILD_FAILED: %d / %d brute parts' % (found, len(rig['parts'])))
        raise RuntimeError('brute parts missing')
    unreal.log('SM2_BUILD_OK: build_brute.py')


def orchestrate():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--fbx', default=os.path.join(HOME, 'hulk-scratch/brute_parts/brute_parts.fbx'))
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
    env = {**os.environ, 'BRUTE_FBX': os.path.abspath(a.fbx), 'GPU_SLOT_DIR': root, 'GPU_SLOT_CAPTURE_MAX_HOLD': '1800'}
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
