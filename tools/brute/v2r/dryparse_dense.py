# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
"""Round 4 dense reader plan check (docs/brute/video2rig/ROUND4.md). Dry-parse the dense-reader commands: run each module's real argparse on the exact argv, print the namespace, never execute.
Run: cd ~/video2rig-lockfix && PYTHONPATH=. ~/video2rig/.venv/bin/python ~/hulk/tools/brute/v2r/dryparse_dense.py  (CPU only, writes nothing)"""
import argparse, runpy, sys, types
P = '/Users/midir/hulk/Local/video2rig/brute-aligned'
R = P + '/reader/renders-dense'
class Parsed(BaseException): pass       # not caught by the tools' own "except Exception"
orig = argparse.ArgumentParser.parse_args
def fake(self, args=None, namespace=None):
    ns = orig(self, args, namespace)
    print('  OK', vars(ns)); raise Parsed()
argparse.ArgumentParser.parse_args = fake
cmds = [
 ('video2rig.reader.poses', [P, '--n', '6000', '--seed', '1', '--out', R + '/poses.npz']),
 ('video2rig.reader.visible', [P, '--poses', R + '/poses.npz', '--out', R + '/visible.npz']),
 ('video2rig.reader.dense', ['labels', P, '--renders', 'reader/renders-dense']),
 ('video2rig.reader.dense', ['train', P, '--renders', 'reader/renders-dense', '--init', P + '/reader/reader.pt', '--steps', '8000', '--out', 'reader/reader-dense.pt']),
]
for c in ['run_v2', 'land_v3', 'stoplunge_v2', 'land_v1']:
    cmds.append(('video2rig.reader.dense', ['read', P, c, '--reader', P + '/reader/reader-dense.pt', '--locator', 'masks']))
    extra = ['--set', 'steps=false'] if c == 'run_v2' else []
    cmds.append(('video2rig.reader.fit', [P, c, '--reading', f'{P}/work/{c}/dense/reading.npz', '--tag=-dense'] + extra))
    cmds.append(('video2rig', ['review', P, c, '--tag=-dense']))
for mod, argv in cmds:
    print(mod, ' '.join(argv))
    sys.argv = [mod] + argv
    try:
        runpy.run_module(mod, run_name='__main__', alter_sys=True)
        print('  NOT PARSED (ran through?)')
    except Parsed:
        pass
    except SystemExit as e:
        print('  ARGPARSE REJECTED', e)
# Blender script: stub bpy/mathutils, call its args()
for name in ('bpy', 'mathutils'):
    m = types.ModuleType(name); m.Matrix = m.Quaternion = m.Vector = object; sys.modules[name] = m
sys.argv = ['blender', '--', '--poses', R + '/poses.npz', '--cameras', P + '/start/cameras.json', '--out', R,
            '--copies', '12', '--samples', '8', '--fit', '896', '--height', '720', '--project', P]
print('blender/render_poses.py', ' '.join(sys.argv[2:]))
try:                                     # the script calls main() -> args() at import
    runpy.run_path('/Users/midir/video2rig-lockfix/blender/render_poses.py', run_name='not_main')
    print('  NOT PARSED (ran through?)')
except Parsed:
    pass
except SystemExit as e:
    print('  ARGPARSE REJECTED', e)
