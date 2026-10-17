# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
# Bakes ambient occlusion of the Brute's bind-pose mesh into its own UV layout (Cycles), so muscle grooves, armpits, the chest / ab
# separations and the fingers get real depth in game (the Customuse ORM ships an all-white occlusion channel).
# usage: Blender -b --factory-startup -P tools/brute/bake_ao.py -- <rigged.glb|fbx> <out_ao.png> [size=2048] [samples=128]
import bpy, sys

argv = sys.argv[sys.argv.index('--') + 1:]
SRC, OUT = argv[0], argv[1]
SIZE = int(argv[2]) if len(argv) > 2 else 2048
SAMPLES = int(argv[3]) if len(argv) > 3 else 128
bpy.ops.wm.read_factory_settings(use_empty=True)
if SRC.lower().endswith('.fbx'): bpy.ops.import_scene.fbx(filepath=SRC)
else: bpy.ops.import_scene.gltf(filepath=SRC)
for o in bpy.data.objects:
    if o.type == 'ARMATURE' and o.animation_data: o.animation_data.action = None   # bind pose
mesh = max((o for o in bpy.data.objects if o.type == 'MESH'), key=lambda o: len(o.data.vertices))
sc = bpy.context.scene
sc.render.engine = 'CYCLES'
sc.cycles.samples = SAMPLES
try: sc.cycles.device = 'GPU'
except Exception: pass
img = bpy.data.images.new('BruteAO', SIZE, SIZE, alpha=False, float_buffer=False)
img.colorspace_settings.name = 'Non-Color'
for mat in mesh.data.materials:
    if not mat: continue
    mat.use_nodes = True
    n = mat.node_tree.nodes.new('ShaderNodeTexImage'); n.image = img
    mat.node_tree.nodes.active = n
for o in bpy.data.objects: o.select_set(False)
mesh.select_set(True); bpy.context.view_layer.objects.active = mesh
sc.render.bake.margin = 8
sc.world = sc.world or bpy.data.worlds.new('w')
bpy.ops.object.bake(type='AO')
img.filepath_raw = OUT; img.file_format = 'PNG'; img.save()
print('BAKED', OUT, SIZE, SAMPLES, 'verts', len(mesh.data.vertices))
