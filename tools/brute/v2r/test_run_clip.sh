#!/bin/bash
# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
# Offline test of run_clip.sh (see TESTS-runclip.md): no video, no spend, no reader. Steps 1-3 (check / run / review) run against a STUB of
# `python -m video2rig` that prints the formats copied from video2rig's source; steps 0 and 4-8 run for real on a synthetic fit.
# usage: tools/brute/v2r/test_run_clip.sh [work_dir]   (default ~/hulk/Local/video2rig/work-tools, gitignored; needs test_refine_export.sh's fake_fit)
# One Blender at a time (run_clip.sh waits for a free slot). The real projects are only READ (symlinks for the size gate).
set -u
V=$(cd "$(dirname "$0")" && pwd)
W=${1:-$HOME/hulk/Local/video2rig/work-tools}
ALIGNED=$HOME/hulk/Local/video2rig/brute-aligned
STUB=$W/stubfork; P=$W/proj_test; M=$P/motion-out
B=/Applications/Blender.app/Contents/MacOS/Blender
rc() { "$V/run_clip.sh" "$@"; }
R() { rc "$P" idle_test Idle --loop --fork-dir "$STUB" --motion-dir "$M" --no-size-gate "$@"; }
echo "== 0. parsers on sample strings"; rc --selftest || exit 1

echo "== 1. stub fork (prints the real formats) + test project"
mkdir -p "$STUB/.venv/bin" "$STUB/video2rig" "$STUB/blender" "$P/reader" "$P/rig" "$P/out" "$P/clips"
ln -sf "$(command -v python3)" "$STUB/.venv/bin/python"
ln -sf "$HOME/video2rig/blender/import_motion.py" "$STUB/blender/import_motion.py"
touch "$STUB/video2rig/__init__.py" "$P/reader/reader.pt"
cat > "$STUB/video2rig/__main__.py" <<'EOF'
"""STUB of video2rig for run_clip.sh tests: the exact formats of video2rig/__main__.py, check.py, reader/fit.py, report.py.
Env: STUB_CHECK=ok|warn|fail|none, STUB_FIT=<px>, STUB_WARNS=<n>, STUB_NPZ=<motion npz to copy to out/>, STUB_FILM=<mp4 to copy as review.mp4>."""
import json, os, shutil, sys, time
cmd, project, clip = sys.argv[1:4]
work = os.path.join(project, 'work', clip); os.makedirs(work, exist_ok=True)
mode = os.environ.get('STUB_CHECK', 'ok')
if cmd == 'check':
    print('read: 158 frames x 2 panels')
    if mode == 'none':
        print('clip not found: %s/clips/%s.mp4' % (project, clip)); sys.exit(1)
    body = {'ok': .0107, 'warn': .0121, 'fail': .0182}[mode]
    verdict = {'ok': 'OK', 'warn': 'WARN', 'fail': 'FAIL'}[mode]
    msgs = []
    if mode == 'warn':
        msgs.append('WARN: the panels disagree on the limbs by 2.6% of the height: fast legs drawn differently, or near and far legs mixed up; watch the limbs in the review film')
    if mode == 'fail':
        msgs.append('FAIL: the panels disagree on the body by 1.8% of its height (median; clean clips up to about 1.2%): Seedance drew the move differently in each panel, generate it again')
    print(f'{verdict} {clip}: body {body}, limbs 0.0153 (share of the height, median), frame 0 [0.93, 0.95]' + ''.join(f'\n  {m}' for m in msgs))
    sys.exit(1 if mode == 'fail' else 0)
t0 = time.time()
log = lambda s: print(f'[{time.time() - t0:6.1f}s] {s}', flush=True)
if cmd == 'run':
    fit = os.environ.get('STUB_FIT', '1.37'); nw = int(os.environ.get('STUB_WARNS', '0'))
    log(f'{clip}: 158 frames, 2 view(s), timing 1.0, frame 0 outline match after alignment [0.93, 0.95]')
    log(f'fit {clip}: 158 frames; median keypoint miss {float(fit):.2f} px; 12 one-frame spikes smoothed; low-pass 6 Hz at 30 fps')
    src = os.environ.get('STUB_NPZ')
    if src:
        os.makedirs(os.path.join(project, 'out'), exist_ok=True); shutil.copy(src, os.path.join(project, 'out', clip + '.npz'))
    log('motion -> %s/out/%s.npz' % (project, clip))
    rep = {'frames': 158, 'outline_match': {'v2r_front': 0.953, 'v2r_side': 0.947}, 'worst_frames': {'v2r_front': [1], 'v2r_side': [2]},
           'max_twist_deg': {}, 'biggest_jump_deg': {'deg': 9.1, 'bone': 'Spine', 'frame': 40}, 'frames_under_floor': 0,
           'frames_at_joint_limit': {}, 'warnings': ['stub warning %d' % i for i in range(nw)]}
    log('report ' + json.dumps(rep)); log('time {"total_s": 39.0}')
if cmd == 'review':
    shutil.copy(os.environ['STUB_FILM'], os.path.join(work, 'review.mp4'))
    log(f'review -> {os.path.join(work, "review.mp4")}')
EOF
cp "$W/model_aligned_copy.blend" "$P/model.blend"; cp "$ALIGNED/rig/rig.json" "$P/rig/rig.json"
# synthetic motion .npz from the synthetic Idle fit (test_refine_export.sh makes fake_fit/Idle_fit.blend)
"$B" -b --factory-startup -P "$V/make_test_npz.py" -- "$W/fake_fit/Idle_fit.blend" "$W/synthetic_fit_idle.npz" | grep TESTNPZ | sed "s#$HOME#~#g"
export STUB_NPZ=$W/synthetic_fit_idle.npz STUB_FILM=$ALIGNED/clips/idle_v1.mp4    # the "review film" is a shipped clip: only the sheet step uses it
rm -rf "$P/PIPELINE.log" "$P/work" "$M" "$P"/Idle_v2r_v*

echo "== 2. gate stops: check FAIL (exit 3), check unreadable (exit 4), no reader.pt (exit 4)"
STUB_CHECK=fail R; echo "exit $?"
STUB_CHECK=none R; echo "exit $?"
mv "$P/reader/reader.pt" "$P/reader/reader.pt.off"; R --from run; echo "exit $?"; mv "$P/reader/reader.pt.off" "$P/reader/reader.pt"

echo "== 3. full chain: check WARN, fit 5.2 px, 2 warnings (all continue), steps 4-8 live"
STUB_CHECK=warn STUB_FIT=5.2 STUB_WARNS=2 R; echo "exit $?"

echo "== 4. restarts: --from refine, --from log, --from import --to import (bumps), then --from refine --to refine on the new number"
R --from refine | tail -1
R --from log | tail -1
R --from import --to import | tail -1
R --from refine --to refine | tail -1

echo "== 5. EXPORT_GATE FAIL stops (gate forced to 0.0001 mm)"
R --from export --export-args "--gate-mm 0.0001"; echo "exit $?"

echo "== 6. size gate for real on shipped clips (project = symlinks to the real one, read-only): PASS, FAIL (jump_v2: top edge), air project"
mkdir -p "$W/proj_size"; for x in creature.json start rig clips; do ln -sfn "$ALIGNED/$x" "$W/proj_size/$x"; done
rc "$W/proj_size" idle_v1 Idle --loop --from size --to size; echo "exit $?"
rc "$W/proj_size" jump_v2 Jump --from size --to size; echo "exit $?"
mkdir -p "$W/proj_size_air"; for x in creature.json start rig clips; do ln -sfn "$HOME/hulk/Local/video2rig/brute-air/$x" "$W/proj_size_air/$x"; done
rc "$W/proj_size_air" fall_v1 Fall --loop --fork-dir "$HOME/video2rig-brute-air" --from size --to size; echo "exit $?"
echo "== 7. the real video2rig check without a reader (the real tool's error path)"
rc "$W/proj_size" idle_v1 Idle --loop --from check --to check; echo "exit $?"
echo "== PIPELINE.log of the test project"; cat "$P/PIPELINE.log"
