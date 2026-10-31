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
echo "== 7. burst pass: PunchL fit with a 120 deg LeftArm twist switch over 2 samples at sample 8 (Throw-like solver reset; 60 deg/step clears 8 x this busy arm's 6.9 deg median), --return-to-stance"
blender testfit_burst $V/make_test_fit.py -- $W/model_aligned_copy.blend $SHIPPED PunchL $W/fake_fit/PunchLBurst_fit.blend --twist LeftArm:8:120:2
blender refine_burst $V/refine_brute.py -- $W/fake_fit/PunchLBurst_fit.blend --return-to-stance --clip PunchLBurst --floor=-0.435
blender refine_burst_off $V/refine_brute.py -- $W/fake_fit/PunchLBurst_fit.blend --return-to-stance --clip PunchLBurst --floor=-0.435 --no-burst --out $W/fake_fit/PunchLBurst_fit_noburst.blend
python3 - "$W/fake_fit/PunchLBurst_fit_refined.json" "$W/fake_fit/PunchLBurst_fit_noburst.json" <<'PY'
import json, sys
r = json.load(open(sys.argv[1])); base = json.load(open(sys.argv[2]))
b = r['bursts']['found']
la = b.get('LeftArm', [])
ok = len(la) == 1 and abs(la[0]['net_deg'] - 120) < 6 and la[0]['peak_step_after_deg'] < 30 and set(b) == {'LeftArm'}
pk, pk0 = r['final']['peak_hand']['Left']['sample'], base['final']['peak_hand']['Left']['sample']
print('BURST_TEST bones %s LeftArm %s peakhand_L %d (same fit, --no-burst: %d) %s' % (sorted(b), la, pk, pk0, 'PASS' if ok and pk == pk0 else 'FAIL'))
PY
echo "== 8. hold compression: the PunchL fit with a 1 s still tail kept (--trim 0), --compress-holds --stance-snap 6: the tail hold is re-timed to 6 samples, the hit stays put, the end equals frame 0"
blender testfit_hold $V/make_test_fit.py -- $W/model_aligned_copy.blend $SHIPPED PunchL $W/fake_fit/PunchLHold_fit.blend --hold 1.0
blender refine_hold $V/refine_brute.py -- $W/fake_fit/PunchLHold_fit.blend --return-to-stance --clip PunchLHold --floor=-0.435 --trim 0 --compress-holds --stance-snap 6
blender refine_hold_off $V/refine_brute.py -- $W/fake_fit/PunchLHold_fit.blend --return-to-stance --clip PunchLHold --floor=-0.435 --trim 0 --out $W/fake_fit/PunchLHold_fit_off.blend
python3 - "$W/fake_fit/PunchLHold_fit_refined.json" "$W/fake_fit/PunchLHold_fit_off.json" <<'PY'
import json, sys
r = json.load(open(sys.argv[1])); base = json.load(open(sys.argv[2]))
rt = r['retime']; f = r['final']; fb = base['final']
tail = [c for c in rt['compressed'] if c['samples'][1] == rt['samples_before'] - 1]
cut = rt['samples_before'] - rt['samples_after']
hit = all(f['peak_hand'][s]['sample'] == fb['peak_hand'][s]['sample'] for s in ('Left', 'Right'))
end, end0 = r['last_frame_vs_frame0']['mesh_mm_max'], base['last_frame_vs_frame0']['mesh_mm_max']
# end gap: never worse than without the flags (this synthetic fit's left foot sits in a plant blend at frame 0 but swings at the end,
# which no lift match can fix; real fits start and end on both feet), toes not under the floor, drift not worse
ok = (len(tail) == 1 and tail[0]['keep'] == 6 and cut >= 20 and hit and end <= end0 + 0.5 and f['toe_min_mm'] >= -0.5
      and f['foot_drift_mm'] <= fb['foot_drift_mm'] + 1.0 and 'retime' not in base)
print('HOLD_TEST spans %s compressed %s samples %d -> %d hit L/R %d/%d (no flag: %d/%d) end_vs_frame0_mm %.3f (no flag: %.3f) toe %.1f drift %.1f (no flag: toe %.1f drift %.1f) %s' % (
    [s['samples'] for s in rt['spans']], [c['samples'] for c in rt['compressed']], rt['samples_before'], rt['samples_after'],
    f['peak_hand']['Left']['sample'], f['peak_hand']['Right']['sample'], fb['peak_hand']['Left']['sample'], fb['peak_hand']['Right']['sample'],
    end, end0, f['toe_min_mm'], f['foot_drift_mm'], fb['toe_min_mm'], fb['foot_drift_mm'], 'PASS' if ok else 'FAIL'))
PY
echo "== done"
