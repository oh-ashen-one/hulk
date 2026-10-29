#!/bin/zsh
# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
# Offline test of refine_brute.py + export_clip.py (no video, no reader, no spend; see TESTS-refine-export.md):
#   synthetic fits from the shipped clips (make_test_fit.py) -> refine -> export -> round trip vs the shipped clip -> assemble ingest.
# usage: tools/brute/v2r/test_refine_export.sh [work_dir]   (default ~/hulk/Local/video2rig/work-tools, gitignored)
# One Blender at a time, headless, --factory-startup; waits while 4 Blender processes run (2 if an UnrealEditor runs).
# The aligned model.blend is only ever copied (the reader may be training on it).
set -u
B=/Applications/Blender.app/Contents/MacOS/Blender
V=$(cd "$(dirname "$0")" && pwd)
T=$(dirname "$V")
W=${1:-$HOME/hulk/Local/video2rig/work-tools}
ALIGNED=$HOME/hulk/Local/video2rig/brute-aligned/model.blend
SHIPPED=$HOME/hulk-scratch/brute_v5/brute.glb
RIG=$HOME/hulk-scratch/brute_corr/brute_rigged_corr.glb
OLD=$HOME/hulk-scratch/brute_v2/motion
mkdir -p $W/fake_fit $W/logs
blender() {   # blender <log> <script> args...
  local log=$1; shift
  while true; do
    local nb=$(ps -axo command | grep MacOS/Blender | grep -v grep | wc -l | tr -d ' ')
    local ue=$(ps -axo command | grep -c '[U]nrealEditor')
    local cap=4; [ "$ue" -gt 0 ] && cap=2
    [ "$nb" -lt "$cap" ] && break
    echo "waiting: $nb Blender running (cap $cap)"; sleep 20
  done
  echo "+ Blender -b --factory-startup -P $*" | sed "s#$HOME#~#g"
  $B -b --factory-startup -P "$@" > $W/logs/$log.log 2>&1
  local rc=$?
  grep -E "^(TESTFIT|EXPORT|REFINE|ROUNDTRIP|LOOP|CLIP|MOTION FILES|WROTE)|_GATE|SELFTEST|Traceback|Error:" $W/logs/$log.log | sed "s#$HOME#~#g"
  echo "  (exit $rc, log $W/logs/$log.log)" | sed "s#$HOME#~#g"
  return $rc
}
cp $ALIGNED $W/model_aligned_copy.blend
echo "== 0. file-name self-test"
blender selftest $V/export_clip.py -- --self-test
echo "== 1. synthetic Idle fit (shipped Idle -> aligned rig, keyed like import_motion: 24 fps scene, 30 fps sample times)"
blender testfit_idle $V/make_test_fit.py -- $W/model_aligned_copy.blend $SHIPPED Idle $W/fake_fit/Idle_fit.blend
echo "== 2. exact round trip: export the UNrefined fit, compare with the shipped Idle"
rm -rf $W/motion_raw
blender export_raw $V/export_clip.py -- $W/fake_fit/Idle_fit.blend Idle $W/motion_raw
blender roundtrip_raw $V/roundtrip_check.py -- $SHIPPED Idle $W/motion_raw/Brute_v2r_idle.glb
echo "== 3. refine (--loop) the fit, export, compare with the shipped Idle (refinement changes it on purpose)"
blender refine_idle $V/refine_brute.py -- $W/fake_fit/Idle_fit.blend --loop --clip Idle
rm -rf $W/motion_refined
blender export_refined $V/export_clip.py -- $W/fake_fit/Idle_fit_refined.blend Idle $W/motion_refined
blender roundtrip_refined $V/roundtrip_check.py -- $SHIPPED Idle $W/motion_refined/Brute_v2r_idle.glb
echo "== 4. assemble_motion ingest: old motion files (read-only symlinks) + the refined v2r Idle"
rm -rf $W/assemble_motion_dir $W/assemble_out; mkdir -p $W/assemble_motion_dir
for f in $OLD/*.glb; do ln -s "$f" $W/assemble_motion_dir/; done
ln -s $W/motion_refined/Brute_v2r_idle.glb $W/assemble_motion_dir/
blender assemble $T/assemble_motion.py -- $RIG $W/assemble_motion_dir $W/assemble_out
blender roundtrip_assembled $V/roundtrip_check.py -- $W/assemble_out/brute.glb Idle $W/motion_refined/Brute_v2r_idle.glb
echo "== 5. one-shot path: PunchL fit with two injected one-sample spikes and a 1 s still tail, --return-to-stance, export"
blender testfit_punchl $V/make_test_fit.py -- $W/model_aligned_copy.blend $SHIPPED PunchL $W/fake_fit/PunchL_fit.blend --spike LeftForeArm:20:25 --spike Spine1:30:-15 --hold 1.0
blender refine_punchl $V/refine_brute.py -- $W/fake_fit/PunchL_fit.blend --return-to-stance --clip PunchL --floor=-0.435
rm -rf $W/motion_punchl
blender export_punchl $V/export_clip.py -- $W/fake_fit/PunchL_fit_refined.blend PunchL $W/motion_punchl
echo "== 6. open loop: the shipped Idle minus its last 40 samples, --loop, export"
blender testfit_idleopen $V/make_test_fit.py -- $W/model_aligned_copy.blend $SHIPPED Idle $W/fake_fit/IdleOpen_fit.blend --cut 40
blender refine_idleopen $V/refine_brute.py -- $W/fake_fit/IdleOpen_fit.blend --loop --clip IdleOpen
rm -rf $W/motion_idleopen
blender export_idleopen $V/export_clip.py -- $W/fake_fit/IdleOpen_fit_refined.blend Idle $W/motion_idleopen
echo "== done"
