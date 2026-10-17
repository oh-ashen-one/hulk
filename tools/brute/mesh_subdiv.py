# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
# One level of Catmull-Clark on the skinned Brute (the Customuse body is only ~9.5k unique verts: close-ups look faceted). The
# subdivision is applied UNDER the armature, so vertex groups (skin weights) are interpolated onto the new vertices; UV borders are
# kept, skeleton / bind pose untouched -> still a drop-in first argument for assemble_motion.py.
# usage: Blender -b --factory-startup -P tools/brute/mesh_subdiv.py -- <rigged.glb> <out.glb> [levels=1]
import bpy, sys

argv = sys.argv[sys.argv.index('--') + 1:]
SRC, OUT = argv[0], argv[1]
LV = int(argv[2]) if len(argv) > 2 else 1
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
if arm.animation_data: arm.animation_data.action = None
for o in [o for o in bpy.data.objects if o.type == 'MESH']:
    bpy.context.view_layer.objects.active = o
    n0 = len(o.data.vertices)
    # weld the texture-seam splits first (the glTF importer splits vertices at every UV seam): the subdivision then smooths
    # across seams instead of opening cracks along them; UVs stay per-loop so the seams are still exact
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=1e-5); bpy.ops.object.mode_set(mode='OBJECT')
    m = o.modifiers.new('Subdiv', 'SUBSURF')
    m.levels = LV; m.render_levels = LV; m.subdivision_type = 'CATMULL_CLARK'
    m.uv_smooth = 'PRESERVE_BOUNDARIES'; m.boundary_smooth = 'ALL'; m.use_limit_surface = True
    while o.modifiers[0] != m: bpy.ops.object.modifier_move_up(modifier=m.name)
    bpy.ops.object.modifier_apply(modifier=m.name)
    for p in o.data.polygons: p.use_smooth = True
    print('SUBDIV', o.name, n0, '->', len(o.data.vertices), 'verts,', len(o.data.polygons), 'faces')
for o in bpy.data.objects: o.select_set(o.type in ('MESH', 'ARMATURE'))
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True, export_skins=True, export_animations=False)
print('WROTE', OUT)
